"""Final-decision router API tests (T-082, RF-27/RF-28, plan §4.9, cases 26-28).

Covers the calibration-stage decision surface end to end with in-memory stores:
the specialist closes a published idea (`VALIDADA_PUBLICA`) with a final
`outcome` (`ACEPTADA`/`ARCHIVADA`/`RECHAZADA`, RF-27) that must match the band
of the average of the five criteria given the administrator thresholds (RF-28);
the band is closed upward (case 26: an average exactly on a threshold falls
into the upper band), `ARCHIVADA`/`RECHAZADA` require a reason (case 28) and a
mismatch 409s `DECISION_MISMATCH` carrying the `score` and the `band` (case 27,
the outcome is never forced). The decision is audited (RNF-8) and the creator
is notified (RF-18).
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
SPECIALIST = "u_solo"
ADMIN = "u_admin"

PAST_DEADLINE = "2020-01-01T00:00:00"


def evaluation_json(scores: list[int]) -> str:
    """A contract-shaped reply: the 5 fixed criteria, each with one of `scores`."""
    return json.dumps(
        {key: {"score": score, "justification": f"Valoración IA de {key}."}
         for key, score in zip(EVALUATION_CRITERIA, scores, strict=True)},
        ensure_ascii=False,
    )


def _fields(**overrides: object) -> dict:
    base: dict = {
        "title": "Panel de indicadores de compra",
        "proponent": {"name": "Ana Torres", "area": "Compras",
                        "contact": "ana.torres@innov-ia.local"},
        "description": "Consolidar los indicadores de compra en un panel.",
        "problem": "Indicadores dispersos en hojas de cálculo.",
        "expectedBenefit": "Tres horas semanales menos de consolidación.",
        "strategicAlignment": "Decisiones basadas en datos.",
    }
    base.update(overrides)
    return base


@pytest.fixture()
def directory() -> InMemoryDirectory:
    store = InMemoryDirectory()
    store.create({
        "id": PROPOSER, "username": "ana", "name": "Ana Torres",
        "area": "Compras", "contact": "ana@innov-ia.local",
        "roles": ["proponente"], "active": True,
        "passwordHash": hash_password("clave123"), "shouldChangePassword": False,
    })
    store.create({
        "id": SPECIALIST, "username": "solo", "name": "Solo Esp.",
        "area": "Calidad", "contact": "solo@innov-ia.local",
        "roles": ["especialista"], "active": True,
        "passwordHash": hash_password("clave123"), "shouldChangePassword": False,
    })
    store.create({
        "id": ADMIN, "username": "admin", "name": "Admin",
        "area": "Dirección", "contact": "admin@innov-ia.local",
        "roles": ["admin"], "active": True,
        "passwordHash": hash_password("clave123"), "shouldChangePassword": False,
    })
    return store


@pytest.fixture()
def mock() -> OllamaMock:
    return OllamaMock(available=False)


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


def _idea(auth, mock, *, scores: list[int], close: bool = True,
          title: str = "") -> str:
    """Creates + publishes an idea; with `close` closes the debate so the AI
    evaluation is generated (RF-26). Returns the idea id."""
    mock.available = True
    mock.respond = lambda _prompt: evaluation_json(scores)
    fields = _fields()
    if title:
        fields["title"] = title
    idea = auth(PROPOSER).post("/ideas", json=fields).json()
    auth(PROPOSER).post(f"/ideas/{idea['id']}/request-publication")
    approved = auth(SPECIALIST).post(f"/validation/{idea['id']}/approve")
    assert approved.status_code == 200
    if close:
        auth(ADMIN).put(f"/admin/ideas/{idea['id']}/debate/deadline",
                        json={"deadline": PAST_DEADLINE})
        auth(SPECIALIST).get(f"/catalog/{idea['id']}/debate")
    return idea["id"]


def _stored(auth, idea_id: str) -> dict:
    return auth(PROPOSER).get(f"/ideas/{idea_id}").json()["idea"]


def _decide(auth, idea_id: str, outcome: str, reason: str | None = None) -> TestClient:
    client = auth(SPECIALIST)
    return client.post(f"/validation/{idea_id}/decision",
                       json={"outcome": outcome, "reason": reason})


# -- happy path: one outcome per band (RF-27) ----------------------------------------


@pytest.mark.parametrize(
    "scores, outcome, reason, state",
    [
        ([8, 8, 8, 8, 8], "ACEPTADA", None, "ACEPTADA"),
        ([5, 5, 5, 5, 5], "ARCHIVADA", "Pendiente de justificación", "ARCHIVADA"),
        ([2, 2, 2, 2, 2], "RECHAZADA", "Impacto no demostrable", "RECHAZADA"),
    ],
    ids=["alta", "media", "baja"],
)
def test_each_outcome_reaches_its_final_state(auth, mock, scores, outcome,
                                              reason, state) -> None:
    idea_id = _idea(auth, mock, scores=scores)

    response = _decide(auth, idea_id, outcome, reason)
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == state
    assert body["decision"]["outcome"] == outcome
    assert body["decision"]["score"] == pytest.approx(sum(scores) / len(scores))
    assert body["decision"]["reason"] == reason
    assert body["decision"]["decidedBy"] == SPECIALIST
    assert body["decision"]["decidedByName"] == "Solo Esp."
    assert body["decision"]["decidedAt"]
    # Persisted on the ledger (RNF-8) with the idea in its final state.
    stored = _stored(auth, idea_id)
    assert stored["state"] == state
    assert stored["decision"]["outcome"] == outcome


@pytest.mark.parametrize(
    "scores, outcome",
    [
        ([4, 4, 4, 4, 4], "ARCHIVADA"),  # average == rejectionThreshold (case 26)
        ([7, 7, 7, 7, 7], "ACEPTADA"),   # average == acceptanceThreshold (case 26)
    ],
    ids=["promedio-en-umbral-rechazo", "promedio-en-umbral-aceptacion"],
)
def test_an_average_exactly_on_a_threshold_falls_in_the_upper_band(auth, mock,
                                                                    scores, outcome) -> None:
    idea_id = _idea(auth, mock, scores=scores)
    reason = "Límite de banda"
    response = _decide(auth, idea_id, outcome, reason)
    assert response.status_code == 200
    assert response.json()["state"] == outcome


# -- guards (RF-27, RNF-7/RNF-9), in order -------------------------------------------


def test_an_unknown_outcome_is_a_422(auth, mock) -> None:
    idea_id = _idea(auth, mock, scores=[8] * 5)
    response = _decide(auth, idea_id, "PROMOCIONADA", "x")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "DECISION_INVALID"


def test_decision_404_for_an_unknown_idea(auth) -> None:
    response = _decide(auth, "idea_nadie", "ACEPTADA")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "IDEA_NOT_FOUND"


def test_decision_requires_the_specialist_role(auth, mock) -> None:
    idea_id = _idea(auth, mock, scores=[8] * 5)
    response = auth(PROPOSER).post(f"/validation/{idea_id}/decision",
                                   json={"outcome": "ACEPTADA"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ROLE_NOT_ALLOWED"


def test_decision_requires_a_validada_publica_state(auth) -> None:
    idea = auth(PROPOSER).post("/ideas", json=_fields()).json()
    response = _decide(auth, idea["id"], "ACEPTADA")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DECISION_STATE_INVALID"


def test_decision_409_when_there_is_no_evaluation_yet(auth, mock) -> None:
    # Approved but the debate is still open: no evaluation has been generated.
    idea_id = _idea(auth, mock, scores=[8] * 5, close=False)
    response = _decide(auth, idea_id, "ACEPTADA")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EVALUATION_MISSING"


def test_decision_409_when_the_evaluation_is_pending(auth, mock) -> None:
    mock.available = True  # the mock is toggled by the caller
    idea = auth(PROPOSER).post("/ideas", json=_fields()).json()
    auth(PROPOSER).post(f"/ideas/{idea['id']}/request-publication")
    assert auth(SPECIALIST).post(f"/validation/{idea['id']}/approve").status_code == 200
    # Close the debate with the assistant down: the evaluation stays PENDING.
    mock.available = False
    auth(ADMIN).put(f"/admin/ideas/{idea['id']}/debate/deadline",
                    json={"deadline": PAST_DEADLINE})
    auth(SPECIALIST).get(f"/catalog/{idea['id']}/debate")

    response = _decide(auth, idea["id"], "ACEPTADA")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EVALUATION_PENDING"


@pytest.mark.parametrize("outcome, scores", [("ARCHIVADA", [5] * 5),
                                             ("RECHAZADA", [2] * 5)])
def test_archivada_and_rechazada_require_a_reason_case_28(auth, mock, outcome,
                                                          scores) -> None:
    idea_id = _idea(auth, mock, scores=scores)
    assert _decide(auth, idea_id, outcome, None).status_code == 400
    assert _decide(auth, idea_id, outcome, "   ").status_code == 400
    response = _decide(auth, idea_id, outcome, "   ")
    assert response.json()["error"]["code"] == "DECISION_REASON_REQUIRED"
    # The idea is untouched: still in the calibration stage.
    assert _stored(auth, idea_id)["state"] == "VALIDADA_PUBLICA"


def test_a_mismatching_outcome_is_a_409_with_score_and_band_case_27(auth, mock) -> None:
    idea_id = _idea(auth, mock, scores=[4] * 5)  # average 4.0 -> band ARCHIVADA
    response = _decide(auth, idea_id, "ACEPTADA")
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "DECISION_MISMATCH"
    assert error["details"]["score"] == pytest.approx(4.0)
    assert error["details"]["band"] == "ARCHIVADA"
    # The outcome is never forced: the idea stays in the calibration stage.
    assert _stored(auth, idea_id)["state"] == "VALIDADA_PUBLICA"


def test_the_band_follows_the_administrator_thresholds_case_31(auth, mock, threshold_store) -> None:
    # With the defaults (4/7) an average of 5.0 would be ARCHIVADA; a raised
    # acceptance threshold (5) moves it into the acceptance band. The band is
    # recomputed from the thresholds in force AT decision time (case 31).
    idea_id = _idea(auth, mock, scores=[5] * 5)
    threshold_store.put({"rejectionThreshold": 3, "acceptanceThreshold": 5})

    response = _decide(auth, idea_id, "ACEPTADA")
    assert response.status_code == 200
    assert response.json()["state"] == "ACEPTADA"


def test_saving_thresholds_later_does_not_reopen_a_decided_idea(auth, mock, threshold_store) -> None:
    idea_id = _idea(auth, mock, scores=[5] * 5)
    assert _decide(auth, idea_id, "ARCHIVADA", "Banda media").status_code == 200
    # A later threshold change never recalculates a decided idea (case 31).
    threshold_store.put({"rejectionThreshold": 3, "acceptanceThreshold": 5})
    stored = _stored(auth, idea_id)
    assert stored["state"] == "ARCHIVADA"
    assert stored["decision"]["outcome"] == "ARCHIVADA"


# -- notification (RF-18) --------------------------------------------------------------


def test_the_decision_notifies_the_creator(auth, mock, notify_store) -> None:
    idea_id = _idea(auth, mock, scores=[8] * 5)
    assert _decide(auth, idea_id, "ACEPTADA").status_code == 200

    # The owner also holds the IDEA_PUBLISHED of the publication, so the
    # decision event is looked up by type (newest first: it leads the list).
    listed = notify_store.list_for_user(PROPOSER)
    decision = next(record for record in listed if record["type"] == "IDEA_ACCEPTED")
    assert decision["ideaId"] == idea_id
    assert idea_id in decision["message"]
    assert decision["read"] is False
    assert "Nota:" not in decision["message"]  # no reason was given


def test_a_mismatching_decision_emits_no_notification(auth, mock, notify_store) -> None:
    idea_id = _idea(auth, mock, scores=[4] * 5)
    assert _decide(auth, idea_id, "ACEPTADA").status_code == 409
    # The owner keeps the IDEA_PUBLISHED of the publication but gets no
    # final-decision event (the outcome was never applied).
    types = [record["type"] for record in notify_store.list_for_user(PROPOSER)]
    assert types == ["IDEA_PUBLISHED"]
