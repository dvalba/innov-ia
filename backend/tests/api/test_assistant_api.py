"""Assistant check endpoint and on-demand triggers (T-062, RF-11/RF-12).

Covers `POST /assistant/check` (proponente guard, direct run with the real
queue: down, full pass oldest-first with `IDEA_REFINED`, partial failure
case 6, conversion of the stored `improvementRequest` case 10, idempotency)
and the internal triggers bound to login, `/capture/start` and the
improvement request (RF-11 decision #4, plan §4.5): they run the check
without blocking the main response. The triggers use the REAL
`get_assistant_check` provider (the no-op shield applied by the other API
files persists on the shared app, so this fixture pops it).
"""

import json
from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import deps as deps_module
from app.main import app as main_app
from features.auth.infrastructure.token_store import TokenStore
from features.capture.infrastructure.conversation_store import ConversationStore
from features.ideas.infrastructure.idea_store import IdeaStore
from features.ideas.use_cases.create_idea import create_idea
from features.ideas.use_cases.improve_idea import improve_idea
from features.notifications.infrastructure.notification_store import NotificationStore
from shared.utils.password import hash_password
from tests.conftest import InMemoryDirectory, InMemoryStore, OllamaMock

PROPOSER = "u_ana"


def _fields(**overrides: object) -> dict:
    base: dict = {
        "title": "Optimización del proceso de aprobación de proveedores",
        "proponent": {"name": "Ana Torres", "area": "Compras", "contact": "ana.torres@innov-ia.local"},
        "description": "Digitalizar la validación de proveedores eliminando la revisión manual duplicada.",
        "problem": "Tres revisiones manuales independientes que duplican esfuerzo.",
        "expectedBenefit": "Ahorro de 120 horas mensuales de personal.",
        "strategicAlignment": "Agilizar la cadena de suministro de la empresa.",
    }
    base.update(overrides)
    return base


def _refined_reply(prompt: str, marker: str) -> str:
    return json.dumps(_fields(title=f"Refinada: {marker}"), ensure_ascii=False)


@pytest.fixture()
def env():
    directory = InMemoryDirectory()
    directory.create({
        "id": PROPOSER,
        "username": "ana",
        "name": "Ana Torres",
        "area": "Compras",
        "contact": "ana.torres@innov-ia.local",
        "roles": ["proponente"],
        "active": True,
        "passwordHash": hash_password("clave123"),
        "shouldChangePassword": False,
    })
    directory.create({
        "id": "u_admin",
        "username": "admin",
        "name": "Admin",
        "area": "",
        "contact": "",
        "roles": ["admin"],
        "active": True,
        "passwordHash": hash_password("admin123"),
        "shouldChangePassword": False,
    })
    ledger = IdeaStore(InMemoryStore(), InMemoryStore())
    notifications = NotificationStore(InMemoryStore())
    mock = OllamaMock()
    token_store = TokenStore(InMemoryStore(), ttl_minutes=480, now_factory=datetime.now)
    main_app.dependency_overrides[deps_module.get_user_directory] = lambda: directory
    main_app.dependency_overrides[deps_module.get_token_store] = lambda: token_store
    main_app.dependency_overrides[deps_module.get_idea_ledger] = lambda: ledger
    main_app.dependency_overrides[deps_module.get_assistant_client] = lambda: mock
    main_app.dependency_overrides[deps_module.get_notification_store] = lambda: notifications
    main_app.dependency_overrides[deps_module.get_conversation_store] = (
        lambda: ConversationStore(InMemoryStore())
    )
    # The on-demand triggers must use the REAL check composed from the
    # in-memory leaves above; the no-op shield applied by the other API test
    # files persists on the shared app, so it is popped here.
    main_app.dependency_overrides.pop(deps_module.get_assistant_check, None)
    return SimpleNamespace(
        directory=directory, ledger=ledger, notifications=notifications,
        mock=mock, token_store=token_store,
    )


@pytest.fixture()
def api_client(env) -> TestClient:
    return TestClient(main_app)


def _headers(env, user_id: str) -> dict:
    session = env.token_store.issue(
        user_id, tuple(env.directory.get(user_id)["roles"]), now=datetime.now()
    )
    return {"Authorization": f"Bearer {session.token}"}


# -- access guards (plan §3.1) -------------------------------------------------------


def test_check_without_session_is_401(env, api_client: TestClient) -> None:
    assert api_client.post("/assistant/check").status_code == 401


def test_check_with_a_non_proponent_role_is_403(env, api_client: TestClient) -> None:
    response = api_client.post("/assistant/check", headers=_headers(env, "u_admin"))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ROLE_NOT_ALLOWED"


# -- direct check: the real pass ------------------------------------------------------


def test_check_without_the_assistant_reports_unavailable(env, api_client: TestClient) -> None:
    idea = create_idea(env.ledger, owner_id=PROPOSER, origin="manual",
                       fields=_fields(title="Idea manual pendiente"))
    env.mock.available = False

    response = api_client.post("/assistant/check", headers=_headers(env, PROPOSER))

    assert response.status_code == 200
    assert response.json() == {"status": "UNAVAILABLE", "refined": 0, "failed": 0, "pending": 1}
    # Case 5: nothing is touched while the assistant is down.
    assert env.ledger.versions_of(idea["id"]) == []
    assert env.ledger.get(idea["id"])["state"] == "EN_DESARROLLO"
    assert env.mock.prompts == []


def test_check_refines_the_manual_queue_oldest_first_and_notifies(
    env, api_client: TestClient
) -> None:
    idea_a = create_idea(env.ledger, owner_id=PROPOSER, origin="manual",
                         fields=_fields(title="Idea antigua a refinar"))
    idea_b = create_idea(env.ledger, owner_id=PROPOSER, origin="manual",
                         fields=_fields(title="Idea reciente a refinar"))
    env.ledger.update(idea_a["id"], {"createdAt": "2026-01-01T00:00:00"})
    env.ledger.update(idea_b["id"], {"createdAt": "2026-01-02T00:00:00"})

    def _reply(prompt: str) -> str:
        for idea in (idea_a, idea_b):
            if idea["title"] in prompt:
                return _refined_reply(prompt, idea["title"])
        return json.dumps(_fields(), ensure_ascii=False)

    env.mock.respond = _reply
    response = api_client.post("/assistant/check", headers=_headers(env, PROPOSER))

    assert response.status_code == 200
    assert response.json() == {"status": "OK", "refined": 2, "failed": 0, "pending": 0}
    # RF-11: the oldest idea is processed first.
    assert idea_a["title"] in env.mock.prompts[0]
    assert idea_b["title"] in env.mock.prompts[1]
    for idea in (idea_a, idea_b):
        versions = env.ledger.versions_of(idea["id"])
        assert [version["requestedBy"] for version in versions] == ["refinement"]
        assert versions[0]["status"] == "PENDIENTE"
        payload = env.ledger.get(idea["id"])
        assert payload["reviewedByAI"] is True
        assert payload["state"] == "EN_DESARROLLO", "the idea keeps operating (RF-11)"
        assert payload["title"] == idea["title"], "the current fields are never overwritten"
    # RF-12: one IDEA_REFINED per idea, with the canonical message, newest first.
    notices = env.notifications.list_for_user(PROPOSER)
    assert [notice["ideaId"] for notice in notices] == [idea_b["id"], idea_a["id"]]
    for notice in notices:
        assert notice["type"] == "IDEA_REFINED"
        assert notice["message"] == f"La IA refinó tu idea ({notice['ideaId']})."
        assert notice["read"] is False

    again = api_client.post("/assistant/check", headers=_headers(env, PROPOSER)).json()
    assert again == {"status": "OK", "refined": 0, "failed": 0, "pending": 0}, "the pass is idempotent"


def test_check_partial_failure_keeps_the_processed_and_counts_the_rest(
    env, api_client: TestClient
) -> None:
    idea_a = create_idea(env.ledger, owner_id=PROPOSER, origin="manual",
                         fields=_fields(title="Idea uno a refinar"))
    idea_b = create_idea(env.ledger, owner_id=PROPOSER, origin="manual",
                         fields=_fields(title="Idea dos a refinar"))
    env.ledger.update(idea_a["id"], {"createdAt": "2026-01-01T00:00:00"})

    def _reply(prompt: str) -> str:
        if idea_a["title"] in prompt:
            return _refined_reply(prompt, idea_a["title"])
        return "respuesta sin JSON interpretable"

    env.mock.respond = _reply
    response = api_client.post("/assistant/check", headers=_headers(env, PROPOSER))

    assert response.json() == {"status": "OK", "refined": 1, "failed": 1, "pending": 1}
    assert env.ledger.versions_of(idea_a["id"]) != [], "case 6: the processed is kept"
    assert env.ledger.versions_of(idea_b["id"]) == [], "case 6: the failed stays pending"
    assert env.ledger.get(idea_b["id"])["state"] == "EN_DESARROLLO"

    env.mock.respond = lambda prompt: _refined_reply(prompt, idea_b["title"])
    again = api_client.post("/assistant/check", headers=_headers(env, PROPOSER))

    assert again.json() == {"status": "OK", "refined": 1, "failed": 0, "pending": 0}
    assert len(env.ledger.versions_of(idea_b["id"])) == 1
    assert len(env.notifications.list_for_user(PROPOSER)) == 2


def test_check_converts_the_stored_improvement_request_when_the_ia_is_back(
    env, api_client: TestClient
) -> None:
    idea = create_idea(env.ledger, owner_id=PROPOSER, origin="manual",
                       fields=_fields(title="Idea con mejora pendiente"))
    env.mock.available = False
    improve_idea(env.ledger, env.mock, idea_id=idea["id"], owner_id=PROPOSER,
                 instruction="Cuantifica el beneficio")
    # Case 10: without the IA the request is stored on the idea (no version).
    assert env.ledger.get(idea["id"])["improvementRequest"] is not None
    assert env.ledger.versions_of(idea["id"]) == []

    env.mock.available = True
    env.mock.respond = lambda prompt: json.dumps(
        _fields(expectedBenefit="Beneficio cuantificado por la mejora."), ensure_ascii=False
    )
    response = api_client.post("/assistant/check", headers=_headers(env, PROPOSER))

    assert response.status_code == 200
    # The conversion succeeds (refined=1) but the idea has no valid
    # refinement version yet, so it stays in the queue for the next pass.
    assert response.json() == {"status": "OK", "refined": 1, "failed": 0, "pending": 1}
    version = env.ledger.versions_of(idea["id"])[0]
    assert version["requestedBy"] == "improvement", "case 10 keeps the improvement semantics"
    assert version["status"] == "PENDIENTE"
    assert "Cuantifica el beneficio" in env.mock.prompts[0]
    payload = env.ledger.get(idea["id"])
    assert payload["improvementRequest"] is None, "the stored request is consumed"
    assert payload["reviewedByAI"] is True
    assert any(
        notice["type"] == "IDEA_REFINED" and notice["ideaId"] == idea["id"]
        for notice in env.notifications.list_for_user(PROPOSER)
    )


# -- on-demand triggers (RF-11 decision #4) -------------------------------------------


def test_login_of_a_proponent_triggers_the_check_in_background(
    env, api_client: TestClient
) -> None:
    create_idea(env.ledger, owner_id=PROPOSER, origin="manual",
                fields=_fields(title="Idea manual pendiente de refinamiento"))
    env.mock.respond = lambda prompt: _refined_reply(prompt, "pendiente")

    login = api_client.post("/auth/login", json={"username": "ana", "password": "clave123"})

    # The main response is unchanged; the pass ran afterwards (no blocking).
    assert login.status_code == 200
    assert login.json()["user"]["roles"] == ["proponente"]
    versions = env.ledger.versions_of(
        env.ledger.list_by_state("EN_DESARROLLO")[0]["id"]
    )
    assert [version["requestedBy"] for version in versions] == ["refinement"]
    assert len(env.notifications.list_for_user(PROPOSER)) == 1


def test_login_of_a_non_proponent_does_not_trigger(env, api_client: TestClient) -> None:
    login = api_client.post("/auth/login", json={"username": "admin", "password": "admin123"})

    assert login.status_code == 200
    assert env.mock.ping_calls == 0, "no verification without the proponent role"
    assert env.mock.prompts == []


def test_capture_start_triggers_the_check_in_background(
    env, api_client: TestClient
) -> None:
    idea = create_idea(env.ledger, owner_id=PROPOSER, origin="manual",
                       fields=_fields(title="Otra idea manual en cola"))
    env.mock.respond = lambda prompt: _refined_reply(prompt, "en cola")

    response = api_client.post("/capture/start", headers=_headers(env, PROPOSER))

    assert response.status_code == 200
    assert [version["requestedBy"] for version in env.ledger.versions_of(idea["id"])] == ["refinement"]
    assert len(env.notifications.list_for_user(PROPOSER)) == 1


def test_improve_request_triggers_the_check_in_background(
    env, api_client: TestClient
) -> None:
    idea_x = create_idea(env.ledger, owner_id=PROPOSER, origin="asistida",
                         fields=_fields(title="Idea a mejorar"))
    idea_y = create_idea(env.ledger, owner_id=PROPOSER, origin="manual",
                         fields=_fields(title="Idea manual que aprovecha el disparo"))
    env.ledger.update(idea_y["id"], {"createdAt": "2026-01-01T00:00:00"})

    def _reply(prompt: str) -> str:
        if "Cuantifica el beneficio" in prompt:
            return json.dumps(
                _fields(expectedBenefit="Beneficio mejorado por la IA."), ensure_ascii=False
            )
        return _refined_reply(prompt, "aprovecha")

    env.mock.respond = _reply
    response = api_client.post(
        f"/ideas/{idea_x['id']}/improve",
        json={"instruction": "Cuantifica el beneficio"},
        headers=_headers(env, PROPOSER),
    )

    assert response.status_code == 200
    # The synchronous improvement registered its version...
    assert env.ledger.versions_of(idea_x["id"])[0]["requestedBy"] == "improvement"
    # ...and the background check processed the rest of the queue.
    assert [version["requestedBy"] for version in env.ledger.versions_of(idea_y["id"])] == ["refinement"]
    assert len(env.notifications.list_for_user(PROPOSER)) == 1
