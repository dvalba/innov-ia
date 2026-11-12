"""E2E and integration verification of the v2.2 expansion (T-086).

Spec §9 plus the limit cases 26-31, driven end to end against the real
routers with in-memory stores: the specialist's decision (the 2-decimal
average, the closed band <4 / 4-6.99 / >=7, `DECISION_MISMATCH` with the
score and the band, the mandatory reason — cases 26-28), the re-evaluation
of an archived idea (owner-only, `ARCHIVADA`-only, the decision is cleared
while the closed debate and the immutable AI evaluation survive, re-entry
to the calibration queue — case 30), and the calibration thresholds
(defaults, persistence and audit, `THRESHOLDS_INVALID`, access control,
and no recomputation of prior decisions — case 31).
"""

import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app import deps as deps_module
from app.main import app as main_app
from features.auth.infrastructure.token_store import TokenStore
from features.ideas.infrastructure.idea_store import IdeaStore
from features.notifications.infrastructure.notification_store import NotificationStore
from features.org.infrastructure.org_store import OrgStore
from features.validation.infrastructure.threshold_store import ThresholdStore
from shared.contracts.evaluation import EVALUATION_CRITERIA
from shared.utils.password import hash_password
from tests.conftest import InMemoryDirectory, InMemoryStore, OllamaMock

PROPOSER = "u_ana"
OTHER = "u_beto"
SPECIALIST = "u_solo"
ADMIN = "u_admin"

PAST_DEADLINE = "2020-01-01T00:00:00"


def _fields(**overrides: object) -> dict:
    base: dict = {
        "title": "Portal de compras en línea",
        "proponent": {"name": "Ana Torres", "area": "Compras",
                       "contact": "ana.torres@innov-ia.local"},
        "description": "Migrar las compras a un portal en línea.",
        "problem": "Requisiciones en papel, sin trazabilidad.",
        "expectedBenefit": "40% menos de tiempo de ciclo de compra.",
        "strategicAlignment": "Digitalizar la cadena de suministro.",
    }
    base.update(overrides)
    return base


def evaluation_json(scores: list[int]) -> str:
    """A contract-shaped AI reply: the 5 fixed criteria, scores from `scores`."""
    return json.dumps(
        {key: {"score": score, "justification": f"Valoración IA de {key}."}
         for key, score in zip(EVALUATION_CRITERIA, scores, strict=True)},
        ensure_ascii=False,
    )


@pytest.fixture()
def directory() -> InMemoryDirectory:
    store = InMemoryDirectory()
    for user_id, name, roles in (
        (PROPOSER, "Ana Torres", ["proponente"]),
        (OTHER, "Beto Ruiz", ["proponente"]),
        (SPECIALIST, "Solo Esp.", ["especialista"]),
        (ADMIN, "Admin", ["admin"]),
    ):
        store.create({
            "id": user_id,
            "username": user_id.removeprefix("u_"),
            "name": name,
            "area": "Operaciones",
            "contact": f"{user_id.removeprefix('u_')}@innov-ia.local",
            "roles": roles,
            "active": True,
            "passwordHash": hash_password("clave123"),
            "shouldChangePassword": False,
        })
    return store


@pytest.fixture()
def mock() -> OllamaMock:
    return OllamaMock(available=True)


@pytest.fixture()
def idea_ledger() -> IdeaStore:
    return IdeaStore(InMemoryStore(), InMemoryStore())


@pytest.fixture()
def notify_store() -> NotificationStore:
    return NotificationStore(InMemoryStore())


@pytest.fixture()
def threshold_store() -> ThresholdStore:
    return ThresholdStore(InMemoryStore())


@pytest.fixture()
def org_store() -> OrgStore:
    return OrgStore(InMemoryStore())


@pytest.fixture()
def auth(directory, mock, idea_ledger, notify_store, threshold_store, org_store):
    token_store = TokenStore(InMemoryStore(), ttl_minutes=480, now_factory=datetime.now)

    main_app.dependency_overrides[deps_module.get_user_directory] = lambda: directory
    main_app.dependency_overrides[deps_module.get_token_store] = lambda: token_store
    main_app.dependency_overrides[deps_module.get_idea_ledger] = lambda: idea_ledger
    main_app.dependency_overrides[deps_module.get_assistant_client] = lambda: mock
    main_app.dependency_overrides[deps_module.get_notification_store] = lambda: notify_store
    main_app.dependency_overrides[deps_module.get_threshold_store] = lambda: threshold_store
    main_app.dependency_overrides[deps_module.get_org_store] = lambda: org_store

    def _client(user_id: str = SPECIALIST, token: bool = True) -> TestClient:
        if not token:
            return TestClient(main_app)
        roles = tuple(directory.get(user_id)["roles"])
        session = token_store.issue(user_id, roles, now=datetime.now())
        return TestClient(main_app, headers={"Authorization": f"Bearer {session.token}"})

    return _client


def _published_and_evaluated(auth, mock, scores: list[int]) -> str:
    """Creates, publishes, closes (with the AI evaluation generated) and
    returns the idea id, ready for the final decision."""
    mock.respond = lambda _prompt: evaluation_json(scores)
    idea = auth(PROPOSER).post("/ideas", json=_fields()).json()
    auth(PROPOSER).post(f"/ideas/{idea['id']}/request-publication")
    assert auth(SPECIALIST).post(f"/validation/{idea['id']}/approve").status_code == 200
    auth(ADMIN).put(f"/admin/ideas/{idea['id']}/debate/deadline",
                    json={"deadline": PAST_DEADLINE})
    assert auth(SPECIALIST).get(f"/catalog/{idea['id']}/debate").status_code == 200
    return idea["id"]


# -- the final decision (spec §9, RF-27/RF-28, cases 26-28) -------------------------


def test_the_decision_is_decided_with_the_average_rounded_to_two_decimals(
        auth, mock, notify_store) -> None:
    # 8 + 9 + 7 + 6 + 5 = 35 / 5 = 7.0 → the acceptance band.
    idea_id = _published_and_evaluated(auth, mock, [8, 9, 7, 6, 5])

    response = auth(SPECIALIST).post(f"/validation/{idea_id}/decision",
                                     json={"outcome": "ACEPTADA",
                                           "reason": "Alineada con la estrategia."})
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "ACEPTADA"
    assert body["decision"]["outcome"] == "ACEPTADA"
    assert body["decision"]["score"] == 7.0
    assert body["decision"]["reason"] == "Alineada con la estrategia."
    assert body["decision"]["decidedBy"] == SPECIALIST
    assert body["decision"]["decidedByName"] == "Solo Esp."
    assert body["decision"]["decidedAt"]
    # The creator was notified of the outcome (RF-18).
    proponent = notify_store.list_for_user(PROPOSER)
    assert proponent and proponent[0]["type"] == "IDEA_ACCEPTED"


def test_the_band_must_match_the_average_case_26(auth, mock) -> None:
    # Average 4.0 is in the archive band, not the acceptance one.
    idea_id = _published_and_evaluated(auth, mock, [4, 4, 4, 4, 4])

    response = auth(SPECIALIST).post(f"/validation/{idea_id}/decision",
                                     json={"outcome": "ACEPTADA", "reason": "No."})
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "DECISION_MISMATCH"
    assert error["details"]["score"] == 4.0
    assert error["details"]["band"] == "ARCHIVADA"

    # And the idea stays calibratable: the queue still lists it.
    queue = auth(SPECIALIST).get("/validation/queue",
                                 params={"stage": "calibracion"}).json()
    assert [entry["id"] for entry in queue] == [idea_id]


def test_a_mandatory_reason_is_required_to_archive_or_reject_case_27(
        auth, mock) -> None:
    idea_id = _published_and_evaluated(auth, mock, [4, 4, 4, 4, 4])

    missing = auth(SPECIALIST).post(f"/validation/{idea_id}/decision",
                                    json={"outcome": "ARCHIVADA"})
    assert missing.status_code == 400
    assert missing.json()["error"]["code"] == "DECISION_REASON_REQUIRED"

    rejected = auth(SPECIALIST).post(f"/validation/{idea_id}/decision",
                                     json={"outcome": "ARCHIVADA",
                                           "reason": "No priorizada este año."})
    assert rejected.status_code == 200
    assert rejected.json()["state"] == "ARCHIVADA"
    assert rejected.json()["decision"]["outcome"] == "ARCHIVADA"
    assert rejected.json()["decision"]["reason"] == "No priorizada este año."


def test_an_accepted_or_rejected_decision_is_terminal_case_28(auth, mock) -> None:
    accepted = _published_and_evaluated(auth, mock, [7, 7, 7, 7, 7])
    assert auth(SPECIALIST).post(f"/validation/{accepted}/decision",
                                 json={"outcome": "ACEPTADA",
                                       "reason": "Alta alineación."}).status_code == 200

    # A second decision is no longer admissible (terminal outcome, §5.12).
    again = auth(SPECIALIST).post(f"/validation/{accepted}/decision",
                                  json={"outcome": "ARCHIVADA",
                                        "reason": "Cambio de criterio."})
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "DECISION_STATE_INVALID"

    # The catalog reflects the final zone (D21).
    zones = auth(SPECIALIST).get("/catalog/public").json()["zones"]
    assert [entry["id"] for entry in zones["aceptadas"]] == [accepted]
    assert zones["en-proceso"] == []


# -- the re-evaluation of an archived idea (RF-29, case 30) --------------------------


def test_only_the_owner_can_request_a_reevaluation_case_30(auth, mock) -> None:
    idea_id = _published_and_evaluated(auth, mock, [4, 4, 4, 4, 4])
    assert auth(SPECIALIST).post(f"/validation/{idea_id}/decision",
                                 json={"outcome": "ARCHIVADA",
                                       "reason": "No priorizada."}).status_code == 200

    denied = auth(OTHER).post(f"/ideas/{idea_id}/request-reevaluation")
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "NOT_IDEA_OWNER"


def test_only_archived_ideas_admit_a_reevaluation_case_30(auth, mock) -> None:
    accepted = _published_and_evaluated(auth, mock, [7, 7, 7, 7, 7])
    assert auth(SPECIALIST).post(f"/validation/{accepted}/decision",
                                 json={"outcome": "ACEPTADA",
                                       "reason": "Alta alineación."}).status_code == 200

    denied = auth(PROPOSER).post(f"/ideas/{accepted}/request-reevaluation")
    assert denied.status_code == 409
    assert denied.json()["error"]["code"] == "INVALID_TRANSITION"


def test_the_reevaluation_clears_the_decision_and_reenters_the_calibration(
        auth, mock, notify_store) -> None:
    idea_id = _published_and_evaluated(auth, mock, [4, 4, 4, 4, 4])
    assert auth(SPECIALIST).post(f"/validation/{idea_id}/decision",
                                 json={"outcome": "ARCHIVADA",
                                       "reason": "No priorizada."}).status_code == 200
    # An archived idea is out of the calibration queue.
    assert auth(SPECIALIST).get("/validation/queue",
                                params={"stage": "calibracion"}).json() == []

    retried = auth(PROPOSER).post(f"/ideas/{idea_id}/request-reevaluation")
    assert retried.status_code == 200

    stored = auth(PROPOSER).get(f"/ideas/{idea_id}").json()["idea"]
    assert stored["state"] == "VALIDADA_PUBLICA"
    assert stored["decision"] is None
    # The closed debate and the immutable AI evaluation survive (D12): the
    # idea re-enters calibration without re-opening the debate.
    debate = auth(SPECIALIST).get(f"/catalog/{idea_id}/debate").json()
    assert debate["closed"] is True
    assert stored["aiEvaluation"]["status"] == "GENERADA"
    assert stored["evaluation"]["status"] == "GENERADA"

    # Back in the calibration queue; the creator was notified.
    queue = auth(SPECIALIST).get("/validation/queue",
                                 params={"stage": "calibracion"}).json()
    assert [entry["id"] for entry in queue] == [idea_id]
    proponent = notify_store.list_for_user(PROPOSER)
    assert proponent[0]["type"] == "IDEA_REEVALUATED"


# -- the calibration thresholds (RF-28, RNF-8, case 31) ------------------------------


def test_the_thresholds_default_to_4_and_7(auth, threshold_store) -> None:
    body = auth(ADMIN).get("/admin/calibration-thresholds").json()
    assert body == {"rejectionThreshold": 4, "acceptanceThreshold": 7}
    assert threshold_store.has() is False  # a read never persists


def test_the_thresholds_can_be_persisted_and_are_audited_case_31(auth, threshold_store) -> None:
    response = auth(ADMIN).put("/admin/calibration-thresholds",
                               json={"rejectionThreshold": 5, "acceptanceThreshold": 8})
    assert response.status_code == 200
    body = response.json()
    assert body["rejectionThreshold"] == 5
    assert body["acceptanceThreshold"] == 8
    assert body["updatedBy"] == ADMIN
    assert body["updatedAt"]
    assert auth(ADMIN).get("/admin/calibration-thresholds").json() == body


def test_a_malformed_threshold_payload_is_rejected_with_422_case_31(
        auth, threshold_store) -> None:
    response = auth(ADMIN).put("/admin/calibration-thresholds",
                               json={"rejectionThreshold": 5, "acceptanceThreshold": 5})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "THRESHOLDS_INVALID"
    assert threshold_store.has() is False  # nothing persisted on a rejection


def test_the_thresholds_are_admin_only(auth) -> None:
    assert auth(SPECIALIST, token=False).get("/admin/calibration-thresholds").status_code == 401
    assert auth(SPECIALIST).get("/admin/calibration-thresholds").status_code == 403
    assert auth(PROPOSER).put("/admin/calibration-thresholds",
                              json={"rejectionThreshold": 3,
                                    "acceptanceThreshold": 7}).status_code == 403


def test_changing_the_thresholds_does_not_recompute_prior_decisions_case_31(
        auth, mock) -> None:
    # Accepted with the default 7 threshold (average 7.0).
    idea_id = _published_and_evaluated(auth, mock, [7, 7, 7, 7, 7])
    assert auth(SPECIALIST).post(f"/validation/{idea_id}/decision",
                                 json={"outcome": "ACEPTADA",
                                       "reason": "Alta alineación."}).status_code == 200

    # New, stricter thresholds (>=8) are persisted…
    assert auth(ADMIN).put("/admin/calibration-thresholds",
                           json={"rejectionThreshold": 5,
                                 "acceptanceThreshold": 8}).status_code == 200

    # …but the already-accepted decision stands untouched (RNF-8/case 31):
    # state, outcome, score and reason are preserved and the decision stays
    # terminal.
    stored = auth(PROPOSER).get(f"/ideas/{idea_id}").json()["idea"]
    assert stored["state"] == "ACEPTADA"
    assert stored["decision"]["outcome"] == "ACEPTADA"
    assert stored["decision"]["score"] == 7.0
    assert stored["decision"]["reason"] == "Alta alineación."
    again = auth(SPECIALIST).post(f"/validation/{idea_id}/decision",
                                  json={"outcome": "ARCHIVADA",
                                        "reason": "Nuevo umbral."})
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "DECISION_STATE_INVALID"
    # And the catalog keeps it in the acceptance zone.
    zones = auth(SPECIALIST).get("/catalog/public").json()["zones"]
    assert [entry["id"] for entry in zones["aceptadas"]] == [idea_id]
