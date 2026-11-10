"""Validation router API tests (T-034, RF-14/RF-15/RF-16, plan §3.1).

Covers the specialist review surface: `GET /validation/queue` (only
SOLICITANDO_PUBLICACION, proponent without contact), `POST /validation/{id}/approve`
(VALIDADA_PUBLICA) and `POST /validation/{id}/reject` (EN_DESARROLLO, mandatory
comment = case 13). Approval/rejection reuse the G06 `approve_idea`/`reject_idea`
use cases, so the audit trail (RNF-8) and the notification emission points are
preserved; here the tests assert the state, the trail and the 403 role guard,
while the emitted notifications are covered in `test_notifications_api.py`.
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
from shared.contracts.idea_ledger import IDEA_FIELDS
from shared.utils.password import hash_password
from tests.conftest import InMemoryDirectory, InMemoryStore, OllamaMock

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
        "title": "Optimización de la aprobación de proveedores",
        "proponent": {"name": "Ana Torres", "area": "Compras",
                      "contact": "ana.torres@innov-ia.local"},
        "description": "Digitalizar la validación de proveedores.",
        "problem": "Revisión manual duplicada.",
        "expectedBenefit": "120 horas ahorradas al mes.",
        "strategicAlignment": "Agilizar la cadena de suministro.",
    }
    base.update(overrides)
    return base


@pytest.fixture()
def directory() -> InMemoryDirectory:
    store = InMemoryDirectory()
    for user_id, name in (("u_ana", "Ana"), ("u_beto", "Beto")):
        store.create({
            "id": user_id,
            "username": user_id.removeprefix("u_"),
            "name": name,
            "area": "Produccion",
            "contact": f"{user_id.removeprefix('u_')}@corp.com",
            "roles": ["proponente"],
            "active": True,
            "passwordHash": hash_password("clave123"),
            "shouldChangePassword": False,
        })
    store.create({
        "id": "u_solo",
        "username": "solo",
        "name": "Solo Esp.",
        "area": "Calidad",
        "contact": "solo@corp.com",
        "roles": ["especialista"],
        "active": True,
        "passwordHash": hash_password("clave123"),
        "shouldChangePassword": False,
    })
    # Proponent + specialist: the self-validation case 9 (decision #3) is legal.
    store.create({
        "id": "u_proplus",
        "username": "proplus",
        "name": "Pro plus",
        "area": "Calidad",
        "contact": "proplus@corp.com",
        "roles": ["proponente", "especialista"],
        "active": True,
        "passwordHash": hash_password("clave123"),
        "shouldChangePassword": False,
    })
    store.create({
        "id": ADMIN,
        "username": "admin",
        "name": "Admin",
        "area": "Dirección",
        "contact": "admin@corp.com",
        "roles": ["admin"],
        "active": True,
        "passwordHash": hash_password("clave123"),
        "shouldChangePassword": False,
    })
    return store


@pytest.fixture()
def idea_ledger() -> IdeaStore:
    return IdeaStore(InMemoryStore(), InMemoryStore())


@pytest.fixture()
def mock() -> OllamaMock:
    return OllamaMock(available=False)


@pytest.fixture()
def auth(directory, mock, idea_ledger):
    token_store = TokenStore(InMemoryStore(), ttl_minutes=480, now_factory=datetime.now)
    notify_store = NotificationStore(InMemoryStore())
    threshold_store = ThresholdStore(InMemoryStore())
    org_store = OrgStore(InMemoryStore())
    main_app.dependency_overrides[deps_module.get_user_directory] = lambda: directory
    main_app.dependency_overrides[deps_module.get_token_store] = lambda: token_store
    main_app.dependency_overrides[deps_module.get_idea_ledger] = lambda: idea_ledger
    main_app.dependency_overrides[deps_module.get_assistant_client] = lambda: mock
    main_app.dependency_overrides[deps_module.get_notification_store] = lambda: notify_store
    main_app.dependency_overrides[deps_module.get_threshold_store] = lambda: threshold_store
    main_app.dependency_overrides[deps_module.get_org_store] = lambda: org_store

    def _client(user_id: str = "u_solo", token: bool = True) -> TestClient:
        if not token:
            return TestClient(main_app)
        roles = tuple(directory.get(user_id)["roles"])
        session = token_store.issue(user_id, roles, now=datetime.now())
        return TestClient(main_app, headers={"Authorization": f"Bearer {session.token}"})

    return _client


# -- access guards ------------------------------------------------------------------


def test_endpoints_require_session_401_and_specialist_role_403(auth) -> None:
    assert auth(token=False).get("/validation/queue").status_code == 401
    assert auth(token=False).post("/validation/idea_any/approve").status_code == 401
    # A pure proponent is out of the review surface (RF-15/RF-16).
    assert auth("u_ana").get("/validation/queue").status_code == 403
    assert auth("u_ana").post("/validation/idea_any/approve").status_code == 403
    assert auth("u_ana").post("/validation/idea_any/reject", json={"comment": "x"}).status_code == 403


def test_self_validation_is_allowed_to_a_proponent_specialist(auth) -> None:
    idea = auth("u_proplus").post("/ideas", json=_fields()).json()
    auth("u_proplus").post(f"/ideas/{idea['id']}/request-publication")
    response = auth("u_proplus").post(f"/validation/{idea['id']}/approve")
    assert response.status_code == 200
    assert response.json()["state"] == "VALIDADA_PUBLICA"


# -- GET /validation/queue (RF-14) ----------------------------------------------------


def test_queue_lists_only_solicitando_without_contact_or_owner(auth, idea_ledger) -> None:
    en_dev = auth("u_beto").post("/ideas", json=_fields(title="Aún en desarrollo")).json()
    idea = auth("u_ana").post("/ideas", json=_fields()).json()
    auth("u_ana").post(f"/ideas/{idea['id']}/request-publication")
    # A second idea already approved leaves the queue.
    other = auth("u_beto").post("/ideas", json=_fields(title="Otra")).json()
    auth("u_beto").post(f"/ideas/{other['id']}/request-publication")
    auth("u_solo").post(f"/validation/{other['id']}/approve")

    queue = auth("u_solo").get("/validation/queue").json()
    assert [entry["id"] for entry in queue] == [idea["id"]]
    entry = queue[0]
    assert set(entry) == {"id", "origin", "requestDate", "fields"}
    assert entry["origin"] == "manual"
    assert entry["requestDate"]
    # The 7 fields are present, but the proponent is reduced to name/area.
    assert set(entry["fields"]) == set(IDEA_FIELDS)
    assert entry["fields"]["proponent"] == {"name": "Ana Torres", "area": "Compras"}
    assert "contact" not in entry["fields"]["proponent"]
    # No ownerId nor state leaks through the queue projection.
    assert "ownerId" not in entry
    assert "state" not in entry
    # The EN_DESARROLLO and the VALIDADA_PUBLICA ideas are not in the queue.
    assert en_dev["id"] not in [entry["id"] for entry in queue]
    assert other["id"] not in [entry["id"] for entry in queue]


def test_queue_oldest_first(auth) -> None:
    first = auth("u_ana").post("/ideas", json=_fields(title="Primera")).json()
    auth("u_ana").post(f"/ideas/{first['id']}/request-publication")
    second = auth("u_beto").post("/ideas", json=_fields(title="Segunda")).json()
    auth("u_beto").post(f"/ideas/{second['id']}/request-publication")

    queue = auth("u_solo").get("/validation/queue").json()
    assert [entry["id"] for entry in queue] == [first["id"], second["id"]]


# -- POST /validation/{id}/approve (RF-15) --------------------------------------------


def test_approve_200_reaches_validada_publica_with_the_trail(auth, idea_ledger) -> None:
    idea = auth("u_ana").post("/ideas", json=_fields()).json()
    auth("u_ana").post(f"/ideas/{idea['id']}/request-publication")
    response = auth("u_solo").post(f"/validation/{idea['id']}/approve")
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "VALIDADA_PUBLICA"
    assert body["publishedBy"] == "u_solo"
    assert body["publishedAt"]
    # The approval is terminal in the MVP (RNF-9): the second attempt loses 409.
    again = auth("u_solo").post(f"/validation/{idea['id']}/approve")
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "INVALID_TRANSITION"
    # The idea left the queue.
    assert auth("u_solo").get("/validation/queue").json() == []


def test_approve_404_for_an_unknown_idea(auth) -> None:
    assert auth("u_solo").post("/validation/idea_nadie/approve").status_code == 404


# -- POST /validation/{id}/reject (RF-16, case 13) ------------------------------------


def test_reject_with_comment_goes_back_to_en_desarrollo_and_keeps_the_note(auth) -> None:
    idea = auth("u_ana").post("/ideas", json=_fields()).json()
    auth("u_ana").post(f"/ideas/{idea['id']}/request-publication")
    response = auth("u_solo").post(f"/validation/{idea['id']}/reject",
                                   json={"comment": "Falta cuantificación"})
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "EN_DESARROLLO"
    note = body["rejectionNote"]
    assert note["by"] == "u_solo"
    assert note["byName"] == "Solo Esp."
    assert note["comment"] == "Falta cuantificación"
    assert note["at"]
    # Back to EN_DESARROLLO: the proponent can request publication again (RF-10).
    again = auth("u_ana").post(f"/ideas/{idea['id']}/request-publication")
    assert again.status_code == 200


def test_reject_without_comment_is_a_400_case_13(auth) -> None:
    idea = auth("u_ana").post("/ideas", json=_fields()).json()
    auth("u_ana").post(f"/ideas/{idea['id']}/request-publication")
    response = auth("u_solo").post(f"/validation/{idea['id']}/reject", json={"comment": "   "})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "REJECTION_COMMENT_REQUIRED"
    # An empty body is rejected by the framework (422) before the rule applies.
    missing = auth("u_solo").post(f"/validation/{idea['id']}/reject")
    assert missing.status_code == 422
    # The idea stays in SOLICITANDO_PUBLICACION: nothing changed.
    stored = auth("u_ana").get(f"/ideas/{idea['id']}").json()["idea"]
    assert stored["state"] == "SOLICITANDO_PUBLICACION"
    assert stored["rejectionNote"] is None


def test_reject_404_for_an_unknown_idea_and_409_outside_solicitando(auth) -> None:
    assert auth("u_solo").post("/validation/idea_nadie/reject",
                                json={"comment": "x"}).status_code == 404
    en_dev = auth("u_ana").post("/ideas", json=_fields()).json()
    assert auth("u_solo").post(f"/validation/{en_dev['id']}/reject",
                                json={"comment": "x"}).status_code == 409


# -- GET /validation/queue?stage=… (RF-14, v2.2 two stages) ---------------------------


def _close_debate(auth, idea_id: str) -> None:
    """Closes the idea's debate through the real admin path (RF-24)."""
    auth(ADMIN).put(f"/admin/ideas/{idea_id}/debate/deadline",
                    json={"deadline": PAST_DEADLINE})
    assert auth("u_solo").get(f"/catalog/{idea_id}/debate").status_code == 200


def _publish(auth, mock, **overrides: object) -> str:
    """Creates + requests + approves an idea; returns its id (VALIDADA_PUBLICA)."""
    idea = auth("u_ana").post("/ideas", json=_fields(**overrides)).json()
    auth("u_ana").post(f"/ideas/{idea['id']}/request-publication")
    assert auth("u_solo").post(f"/validation/{idea['id']}/approve").status_code == 200
    return idea["id"]


def test_stage_publicacion_lists_only_solicitando(auth, mock) -> None:
    solicitando = auth("u_ana").post("/ideas", json=_fields()).json()
    auth("u_ana").post(f"/ideas/{solicitando['id']}/request-publication")
    # A published idea (VALIDADA_PUBLICA) is not in the publication stage.
    _publish(auth, mock)

    queue = auth("u_solo").get("/validation/queue",
                               params={"stage": "publicacion"}).json()
    assert [entry["id"] for entry in queue] == [solicitando["id"]]


def test_stage_calibracion_lists_only_calibrated_ideas(auth, mock) -> None:
    # A published idea whose debate is still open: not yet calibratable.
    open_debate = _publish(auth, mock)
    # A published, closed, evaluated idea with no decision: calibratable.
    mock.available = True
    mock.respond = lambda _prompt: evaluation_json([8] * 5)
    calibratable = _publish(auth, mock, title="Calibrable")
    _close_debate(auth, calibratable)

    queue = auth("u_solo").get("/validation/queue",
                               params={"stage": "calibracion"}).json()
    assert [entry["id"] for entry in queue] == [calibratable]
    assert open_debate not in [entry["id"] for entry in queue]


def test_stage_calibracion_excludes_a_pending_evaluation(auth, mock) -> None:
    # The assistant is down at the closure: the evaluation stays PENDING (case 22).
    mock.available = False
    idea_id = _publish(auth, mock, title="Pendiente")
    _close_debate(auth, idea_id)
    stored = auth("u_ana").get(f"/ideas/{idea_id}").json()["idea"]
    assert stored["evaluation"]["status"] == "PENDING"

    queue = auth("u_solo").get("/validation/queue",
                               params={"stage": "calibracion"}).json()
    assert idea_id not in [entry["id"] for entry in queue]


def test_stage_calibracion_excludes_an_already_decided_idea(auth, mock) -> None:
    mock.available = True
    mock.respond = lambda _prompt: evaluation_json([8] * 5)
    idea_id = _publish(auth, mock, title="Decidida")
    _close_debate(auth, idea_id)
    assert auth("u_solo").post(f"/validation/{idea_id}/decision",
                                json={"outcome": "ACEPTADA"}).status_code == 200

    queue = auth("u_solo").get("/validation/queue",
                               params={"stage": "calibracion"}).json()
    assert idea_id not in [entry["id"] for entry in queue]


def test_no_stage_lists_both_publication_first(auth, mock) -> None:
    # The debate of the first idea (the publication one) is not involved:
    # publication entries always come first, then the calibration ones.
    solicitando = auth("u_ana").post("/ideas", json=_fields()).json()
    auth("u_ana").post(f"/ideas/{solicitando['id']}/request-publication")
    mock.available = True
    mock.respond = lambda _prompt: evaluation_json([8] * 5)
    calibratable = _publish(auth, mock, title="Calibrable")
    _close_debate(auth, calibratable)

    queue = auth("u_solo").get("/validation/queue").json()
    assert [entry["id"] for entry in queue] == [solicitando["id"], calibratable]


def test_an_invalid_stage_is_a_422(auth) -> None:
    response = auth("u_solo").get("/validation/queue", params={"stage": "otra"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "QUEUE_STAGE_INVALID"
