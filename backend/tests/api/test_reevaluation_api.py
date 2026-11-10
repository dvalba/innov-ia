"""Re-evaluation router API tests (T-082, RF-29, plan §4.9, case 30).

Covers the proponent's re-evaluation surface end to end with in-memory stores:
an `ARCHIVADA` idea goes back to the calibration queue (`VALIDADA_PUBLICA`) on
the owner's request (RF-29, case 30), its previous final decision is cleared
while the closed debate and the AI evaluation are kept (the idea re-enters the
calibration stage without re-opening the debate nor regenerating the evaluation),
and the owner is notified with `IDEA_REEVALUATED` (RF-18). Only the owner may
request it (403) and only an `ARCHIVADA` idea admits it (409, case 29: the other
final states are terminal).
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

OWNER = "u_ana"
OTHER_PROPOSER = "u_beto"
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
    for user_id, name in ((OWNER, "Ana Torres"), (OTHER_PROPOSER, "Beto Ruiz")):
        store.create({
            "id": user_id, "username": user_id.removeprefix("u_"),
            "name": name, "area": "Compras",
            "contact": f"{user_id.removeprefix('u_')}@innov-ia.local",
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
def org_store() -> OrgStore:
    return OrgStore(InMemoryStore())


@pytest.fixture()
def auth(directory, mock, idea_ledger, notify_store, org_store):
    token_store = TokenStore(InMemoryStore(), ttl_minutes=480, now_factory=datetime.now)
    threshold_store = ThresholdStore(InMemoryStore())

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


def _to_archivada(auth, mock) -> str:
    """Drives an idea (owned by `OWNER`) to `ARCHIVADA`: publish, close the
    debate so the AI evaluation is generated, then take the final decision.
    Returns the idea id."""
    mock.available = True
    mock.respond = lambda _prompt: evaluation_json([5] * 5)  # average 5.0 -> ARCHIVADA
    idea = auth(OWNER).post("/ideas", json=_fields()).json()
    auth(OWNER).post(f"/ideas/{idea['id']}/request-publication")
    assert auth(SPECIALIST).post(f"/validation/{idea['id']}/approve").status_code == 200
    auth(ADMIN).put(f"/admin/ideas/{idea['id']}/debate/deadline",
                    json={"deadline": PAST_DEADLINE})
    assert auth(SPECIALIST).get(f"/catalog/{idea['id']}/debate").status_code == 200
    decision = auth(SPECIALIST).post(f"/validation/{idea['id']}/decision",
                                     json={"outcome": "ARCHIVADA",
                                           "reason": "Pendiente de justificación"})
    assert decision.status_code == 200
    assert decision.json()["state"] == "ARCHIVADA"
    return idea["id"]


def _stored(auth, idea_id: str) -> dict:
    return auth(OWNER).get(f"/ideas/{idea_id}").json()["idea"]


def test_an_archivada_idea_goes_back_to_the_calibration_queue(auth, mock) -> None:
    idea_id = _to_archivada(auth, mock)

    response = auth(OWNER).post(f"/ideas/{idea_id}/request-reevaluation")
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "VALIDADA_PUBLICA"
    assert body["decision"] is None
    assert "calibración" in body["note"]
    # Persisted on the ledger, with the previous final decision cleared.
    stored = _stored(auth, idea_id)
    assert stored["state"] == "VALIDADA_PUBLICA"
    assert stored["decision"] is None


def test_the_debate_and_the_ai_evaluation_are_kept(auth, mock) -> None:
    idea_id = _to_archivada(auth, mock)
    before = _stored(auth, idea_id)
    assert before["aiEvaluation"] is not None
    assert before["evaluation"]["status"] == "GENERADA"

    assert auth(OWNER).post(f"/ideas/{idea_id}/request-reevaluation").status_code == 200

    stored = _stored(auth, idea_id)
    # The closed debate and the AI evaluation are preserved (case 30): the idea
    # re-enters the calibration stage without re-opening the debate.
    assert stored["aiEvaluation"] == before["aiEvaluation"]
    assert stored["evaluation"] == before["evaluation"]
    debate = auth(SPECIALIST).get(f"/catalog/{idea_id}/debate").json()
    assert debate["closed"] is True


def test_a_reentered_idea_may_be_decided_again(auth, mock) -> None:
    idea_id = _to_archivada(auth, mock)
    assert auth(OWNER).post(f"/ideas/{idea_id}/request-reevaluation").status_code == 200
    # Back in the calibration queue: a new final decision is legal (RF-27).
    response = auth(SPECIALIST).post(f"/validation/{idea_id}/decision",
                                     json={"outcome": "ARCHIVADA",
                                           "reason": "Revisada y archivada de nuevo"})
    assert response.status_code == 200
    assert response.json()["state"] == "ARCHIVADA"
    assert _stored(auth, idea_id)["decision"]["outcome"] == "ARCHIVADA"


def test_the_owner_is_notified_with_idea_reevaluated(auth, mock, notify_store) -> None:
    idea_id = _to_archivada(auth, mock)
    assert auth(OWNER).post(f"/ideas/{idea_id}/request-reevaluation").status_code == 200

    listed = notify_store.list_for_user(OWNER)
    event = next(record for record in listed if record["type"] == "IDEA_REEVALUATED")
    assert event["ideaId"] == idea_id
    assert idea_id in event["message"]
    assert event["read"] is False


# -- guards (RNF-7/RNF-9) --------------------------------------------------------------


def test_reevaluation_404_for_an_unknown_idea(auth) -> None:
    response = auth(OWNER).post("/ideas/idea_nadie/request-reevaluation")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "IDEA_NOT_FOUND"


def test_only_the_owner_may_request_a_reevaluation(auth, mock) -> None:
    idea_id = _to_archivada(auth, mock)
    response = auth(OTHER_PROPOSER).post(f"/ideas/{idea_id}/request-reevaluation")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "NOT_IDEA_OWNER"
    # The idea is untouched.
    assert _stored(auth, idea_id)["state"] == "ARCHIVADA"


def test_reevaluation_requires_the_proponente_role(auth, mock) -> None:
    idea_id = _to_archivada(auth, mock)
    # A pure specialist holds no `proponente` role: the endpoint is out of reach.
    response = auth(SPECIALIST).post(f"/ideas/{idea_id}/request-reevaluation")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ROLE_NOT_ALLOWED"


def test_only_an_archivada_idea_admits_a_reevaluation(auth, mock) -> None:
    # Published and calibrated (VALIDADA_PUBLICA): the re-evaluation is not legal.
    mock.available = True
    mock.respond = lambda _prompt: evaluation_json([5] * 5)
    idea = auth(OWNER).post("/ideas", json=_fields()).json()
    auth(OWNER).post(f"/ideas/{idea['id']}/request-publication")
    assert auth(SPECIALIST).post(f"/validation/{idea['id']}/approve").status_code == 200
    response = auth(OWNER).post(f"/ideas/{idea['id']}/request-reevaluation")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_TRANSITION"
    # An idea still in development is out of the table too.
    en_dev = auth(OWNER).post("/ideas", json=_fields(title="Otra idea")).json()
    assert auth(OWNER).post(f"/ideas/{en_dev['id']}/request-reevaluation").status_code == 409
