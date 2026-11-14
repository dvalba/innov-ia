"""Notifications router API tests (T-033, RF-18, plan §3.1; T-083).

Covers the active-session surface of `/notifications`: `GET /notifications`
(listing + unread counter) and `POST /notifications/{id}/read` (only the
recipient: 404 unknown, 403 otherwise). It also pins the emission contracts —
the eight RF-18 events and only them — through the real flows: `IDEA_REQUESTED`
fanned out to every active specialist on `request-publication`, `IDEA_PUBLISHED`
on `approve`, `IDEA_REJECTED` on `reject`, and `IDEA_CALIBRATION_PENDING`
fanned out to every active specialist the first time the AI evaluation is
generated at the debate's closure (T-083).

The fixtures inject an in-memory `NotificationStore` (and a live directory)
through `app.dependency_overrides`, so the emitters bound in the composition
root write to the in-memory store that the assertions read from. `features.ideas`
/emitters keep the "no idea/assistant imports notifications" rule: here the
store is only observed, never produced by a test directly.
"""

import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app import deps as deps_module
from app.main import app as main_app
from features.auth.infrastructure.token_store import TokenStore
from features.ideas.infrastructure.idea_store import IdeaStore
from features.notifications.domain.notification import EVENT_TYPES
from features.notifications.infrastructure.notification_store import NotificationStore
from features.org.infrastructure.org_store import OrgStore
from shared.contracts.evaluation import EVALUATION_CRITERIA
from shared.utils.password import hash_password
from tests.conftest import InMemoryDirectory, InMemoryStore, OllamaMock

PAST_DEADLINE = "2020-01-01T00:00:00"


def evaluation_json() -> str:
    """A contract-shaped AI evaluation reply: the 5 criteria, score + reason."""
    return json.dumps(
        {key: {"score": 7, "justification": f"Valoración IA de {key}."}
         for key in EVALUATION_CRITERIA},
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
    # Two active specialists: the fanout must reach both.
    for user_id, name in (("u_solo", "Solo Esp."), ("u_dos", "Dos Esp.")):
        store.create({
            "id": user_id,
            "username": user_id.removeprefix("u_"),
            "name": name,
            "area": "Calidad",
            "contact": f"{user_id.removeprefix('u_')}@corp.com",
            "roles": ["especialista"],
            "active": True,
            "passwordHash": hash_password("clave123"),
            "shouldChangePassword": False,
        })
    # A deactivated specialist: never receives a fanout, but keeps its history.
    store.create({
        "id": "u_baja",
        "username": "baja",
        "name": "Baja Esp.",
        "area": "Calidad",
        "contact": "baja@corp.com",
        "roles": ["especialista"],
        "active": False,
        "passwordHash": hash_password("clave123"),
        "shouldChangePassword": False,
    })
    # An administrator: closes the debate at its deadline (the calibration
    # fanout fires at the closure, T-083).
    store.create({
        "id": "u_admin",
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
def notify_store() -> NotificationStore:
    return NotificationStore(InMemoryStore())


@pytest.fixture()
def auth(directory, idea_ledger, notify_store):
    """Bearer clients for a given user id, with the in-memory store injected."""
    token_store = TokenStore(InMemoryStore(), ttl_minutes=480, now_factory=datetime.now)
    main_app.dependency_overrides[deps_module.get_user_directory] = lambda: directory
    main_app.dependency_overrides[deps_module.get_token_store] = lambda: token_store
    main_app.dependency_overrides[deps_module.get_idea_ledger] = lambda: idea_ledger
    main_app.dependency_overrides[deps_module.get_notification_store] = lambda: notify_store
    main_app.dependency_overrides[deps_module.get_assistant_client] = (
        lambda: OllamaMock(available=False)
    )

    def _client(user_id: str = "u_ana", token: bool = True) -> TestClient:
        if not token:
            return TestClient(main_app)
        roles = tuple(directory.get(user_id)["roles"])
        session = token_store.issue(user_id, roles, now=datetime.now())
        return TestClient(main_app, headers={"Authorization": f"Bearer {session.token}"})

    return _client


def _all_records(notify_store: NotificationStore) -> list[dict]:
    """Every notification persisted in the in-memory store (for the invariant check)."""
    return [record for user in ("u_ana", "u_beto", "u_solo", "u_dos", "u_baja")
            for record in notify_store.list_for_user(user)]


# -- access guards (RF-1, plan §3.1) -----------------------------------------------


def test_endpoints_require_an_active_session_401(auth) -> None:
    assert auth(token=False).get("/notifications").status_code == 401
    assert auth(token=False).post("/notifications/notif_any/read").status_code == 401


# -- the eight and only the eight RF-18 events --------------------------------------


def test_every_stored_notification_uses_one_of_the_eight_types(auth, notify_store) -> None:
    """Invariant: no notification of any other type is ever persisted (RF-18)."""
    idea = auth().post("/ideas", json=_fields()).json()
    auth().post(f"/ideas/{idea['id']}/request-publication")  # IDEA_REQUESTED fanout
    auth("u_solo").post(f"/validation/{idea['id']}/approve")  # IDEA_PUBLISHED
    idea2 = auth("u_beto").post("/ideas", json=_fields(title="Idea de Beto")).json()
    auth("u_beto").post(f"/ideas/{idea2['id']}/request-publication")
    auth("u_solo").post(f"/validation/{idea2['id']}/reject", json={"comment": "No hay caso de uso"})

    records = _all_records(notify_store)
    assert records, "the flows must have persisted notifications"
    types = {record["type"] for record in records}
    assert types <= set(EVENT_TYPES), f"unexpected notification types: {types - set(EVENT_TYPES)}"
    # And each of the reachable events did appear through the real flows.
    assert {"IDEA_REQUESTED", "IDEA_PUBLISHED", "IDEA_REJECTED"} <= types


def test_request_publication_fans_idea_requested_out_only_to_active_specialists(
        auth, notify_store) -> None:
    idea = auth().post("/ideas", json=_fields()).json()
    response = auth().post(f"/ideas/{idea['id']}/request-publication")
    assert response.status_code == 200

    # Both active specialists got exactly one IDEA_REQUESTED for the idea.
    for specialist in ("u_solo", "u_dos"):
        listed = notify_store.list_for_user(specialist)
        assert [record["type"] for record in listed] == ["IDEA_REQUESTED"]
        assert listed[0]["ideaId"] == idea["id"]
        assert listed[0]["read"] is False
        assert idea["id"] in listed[0]["message"]
        assert "proponente" in listed[0]["message"].lower()
    # The proponent and the deactivated specialist never receive a fanout.
    assert notify_store.list_for_user("u_ana") == []
    assert notify_store.list_for_user("u_baja") == []
    assert notify_store.unread_count("u_solo") == 1


# -- GET /notifications (listing + unread counter) -----------------------------------


def test_list_returns_only_the_recipient_with_the_unread_counter(auth, notify_store) -> None:
    idea = auth().post("/ideas", json=_fields()).json()
    auth().post(f"/ideas/{idea['id']}/request-publication")

    body = auth("u_solo").get("/notifications").json()
    assert body["unread"] == 1
    assert [entry["type"] for entry in body["notifications"]] == ["IDEA_REQUESTED"]
    entry = body["notifications"][0]
    assert entry["userId"] == "u_solo"
    assert entry["ideaId"] == idea["id"]
    assert set(entry) == {"id", "userId", "type", "ideaId", "message", "read", "createdAt"}

    # Another user reads only their own (empty) stream.
    other = auth("u_ana").get("/notifications").json()
    assert other["notifications"] == []
    assert other["unread"] == 0


# -- POST /notifications/{id}/read (only the recipient) ------------------------------


def test_mark_read_by_the_recipient_updates_the_payload_and_counter(auth, notify_store) -> None:
    idea = auth().post("/ideas", json=_fields()).json()
    auth().post(f"/ideas/{idea['id']}/request-publication")
    target = notify_store.list_for_user("u_solo")[0]

    response = auth("u_solo").post(f"/notifications/{target['id']}/read")
    assert response.status_code == 200
    assert response.json()["read"] is True
    assert notify_store.unread_count("u_solo") == 0


def test_mark_read_twice_is_idempotent(auth, notify_store) -> None:
    idea = auth().post("/ideas", json=_fields()).json()
    auth().post(f"/ideas/{idea['id']}/request-publication")
    target = notify_store.list_for_user("u_dos")[0]

    assert auth("u_dos").post(f"/notifications/{target['id']}/read").status_code == 200
    again = auth("u_dos").post(f"/notifications/{target['id']}/read")
    assert again.status_code == 200
    assert again.json()["read"] is True
    assert notify_store.unread_count("u_dos") == 0


def test_mark_read_403_for_a_non_recipient_and_404_for_an_unknown(auth, notify_store) -> None:
    idea = auth().post("/ideas", json=_fields()).json()
    auth().post(f"/ideas/{idea['id']}/request-publication")
    target = notify_store.list_for_user("u_solo")[0]

    forbidden = auth("u_dos").post(f"/notifications/{target['id']}/read")
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "NOT_NOTIFICATION_OWNER"
    # Left unread by a foreign attempt.
    assert notify_store.get(target["id"])["read"] is False

    missing = auth("u_solo").post("/notifications/notif_nope_99/read")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "NOTIFICATION_NOT_FOUND"


# -- emission points reached through the real flows ----------------------------------


def test_approve_emits_idea_published_to_the_proponent(auth, notify_store) -> None:
    idea = auth().post("/ideas", json=_fields()).json()
    auth().post(f"/ideas/{idea['id']}/request-publication")
    assert auth("u_solo").post(f"/validation/{idea['id']}/approve").status_code == 200

    proponent = notify_store.list_for_user("u_ana")
    assert [record["type"] for record in proponent] == ["IDEA_PUBLISHED"]
    assert proponent[0]["ideaId"] == idea["id"]
    # The approving specialist got only the fanout (IDEA_REQUESTED), not the publish.
    assert [record["type"] for record in notify_store.list_for_user("u_solo")] == ["IDEA_REQUESTED"]


def test_reject_emits_idea_rejected_to_the_proponent(auth, notify_store) -> None:
    idea = auth().post("/ideas", json=_fields()).json()
    auth().post(f"/ideas/{idea['id']}/request-publication")
    assert auth("u_solo").post(f"/validation/{idea['id']}/reject",
                               json={"comment": "Falta cuantificación"}).status_code == 200

    proponent = notify_store.list_for_user("u_ana")
    assert [record["type"] for record in proponent] == ["IDEA_REJECTED"]
    assert proponent[0]["ideaId"] == idea["id"]


# -- the calibration fanout (T-083, RF-18/RF-20) -----------------------------------


def test_calibration_fans_pending_out_to_active_specialists_at_closure(
        auth, notify_store) -> None:
    """When the AI evaluation is first generated at the debate's closure, every
    active specialist is invited to calibrate it (`IDEA_CALIBRATION_PENDING`).
    The fanout fires once, only to active specialists, and never to the proponent
    or the deactivated one."""
    mock = OllamaMock(available=True)
    mock.respond = lambda _prompt: evaluation_json()
    main_app.dependency_overrides[deps_module.get_assistant_client] = lambda: mock
    main_app.dependency_overrides[deps_module.get_org_store] = lambda: OrgStore(InMemoryStore())

    idea = auth().post("/ideas", json=_fields()).json()
    auth().post(f"/ideas/{idea['id']}/request-publication")  # IDEA_REQUESTED fanout
    assert auth("u_solo").post(f"/validation/{idea['id']}/approve").status_code == 200

    # The debate is still open (30-day deadline): no evaluation, no calibration.
    assert [record["type"] for record in notify_store.list_for_user("u_solo")] == ["IDEA_REQUESTED"]
    assert [record["type"] for record in notify_store.list_for_user("u_dos")] == ["IDEA_REQUESTED"]

    # The deadline moves into the past and the next read closes the debate: the
    # AI evaluation is generated and the calibration fanout fires (T-083).
    # The deadline is fixed at opening (T-089): the test forces the past
    # deadline directly on the shared in-memory store.
    debate_store = main_app.dependency_overrides[deps_module.get_debate_store]()
    debate = debate_store.get_debate(idea["id"])
    debate.deadline = PAST_DEADLINE
    debate_store.set(debate)
    assert auth("u_solo").get(f"/catalog/{idea['id']}/debate").status_code == 200

    # Both active specialists got one calibration-pending notification (newest
    # first: the fanout fired after the request-publication fanout).
    for specialist in ("u_solo", "u_dos"):
        records = notify_store.list_for_user(specialist)
        assert [record["type"] for record in records] == [
            "IDEA_CALIBRATION_PENDING", "IDEA_REQUESTED"]
        pending = records[0]
        assert pending["ideaId"] == idea["id"]
        assert pending["read"] is False
        assert idea["id"] in pending["message"]
    # The proponent never receives a calibration; the deactivated one, either.
    assert [record["type"] for record in notify_store.list_for_user("u_ana")] == ["IDEA_PUBLISHED"]
    assert notify_store.list_for_user("u_baja") == []
