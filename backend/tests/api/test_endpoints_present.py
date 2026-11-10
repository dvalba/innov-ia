"""Transversal API smoke test (T-036, plan §3.1).

Closes the backend gate: every endpoint of the plan §3.1 table is asserted
to exist (OpenAPI surface) and to answer according to its contract, with a
single coherent journey per surface built from in-memory stores. This file
adds no production code; it exercises the real application instance end to
end and, in one test, boots a real `uvicorn app.main:app` process and reads
`GET /health` over the network (the 200 the gate requires).

The fixtures mirror the rest of the API suite: `InMemory*` leaves are
injected through `dependency_overrides` and the REAL `get_assistant_check`
is used (popped from the shared app), so the on-demand refinement triggers
and `POST /assistant/check` run the genuine pass against the mock.
"""

import http.client
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import deps as deps_module
from app.main import app as main_app
from features.auth.infrastructure.token_store import TokenStore
from features.capture.domain.conversation import Conversation
from features.capture.infrastructure.conversation_store import ConversationStore
from features.ideas.infrastructure.idea_store import IdeaStore
from features.ideas.use_cases.create_idea import create_idea
from features.ideas.use_cases.improve_idea import CASE_10_NOTICE
from features.notifications.infrastructure.notification_store import NotificationStore
from features.org.infrastructure.org_store import OrgStore
from shared.utils.password import hash_password
from tests.conftest import InMemoryDirectory, InMemoryStore, OllamaMock, turn_options_json

BACKEND_ROOT = Path(__file__).resolve().parents[2]

PROPOSER = "u_ana"
OTHER = "u_beto"
SPECIALIST = "u_solo"
ADMIN = "u_admin"


def _fields(**overrides: object) -> dict:
    base: dict = {
        "title": "Optimización de los tiempos de compra",
        "proponent": {"name": "Ana Torres", "area": "Compras",
                      "contact": "ana.torres@innov-ia.local"},
        "description": "Reducir los tiempos de compra con un flujo digital.",
        "problem": "Revisión manual duplicada del proveedor.",
        "expectedBenefit": "Ahorro de 120 horas mensuales.",
        "strategicAlignment": "Agilizar la cadena de suministro.",
    }
    base.update(overrides)
    return base


def _smart_respond(prompt: str) -> str:
    """A deterministic, always-valid assistant reply (titles, extraction and
    full 7-field refinements all parse, so incidental background checks are
    harmless and the queue drains predictably)."""
    if 'JSON esperado: {"options' in prompt:
        return turn_options_json(prompt)
    if "JSON esperado: {\"title" in prompt:
        return json.dumps({"title": "Título propuesto por la IA"}, ensure_ascii=False)
    if "Campos pendientes" in prompt:
        return json.dumps({"description": "Descripción extraída del relato."},
                          ensure_ascii=False)
    return json.dumps(_fields(), ensure_ascii=False)


@pytest.fixture()
def env():
    directory = InMemoryDirectory()
    for user_id, username, name, roles in (
        (PROPOSER, "ana", "Ana Torres", ["proponente"]),
        (OTHER, "beto", "Beto Ruiz", ["proponente"]),
        (SPECIALIST, "solo", "Solo Esp.", ["especialista"]),
        (ADMIN, "admin", "Admin", ["admin"]),
    ):
        directory.create({
            "id": user_id,
            "username": username,
            "name": name,
            "area": "Operaciones",
            "contact": f"{username}@innov-ia.local",
            "roles": roles,
            "active": True,
            "passwordHash": hash_password("clave123"),
            "shouldChangePassword": False,
        })
    ledger = IdeaStore(InMemoryStore(), InMemoryStore())
    conversations = ConversationStore(InMemoryStore())
    notifications = NotificationStore(InMemoryStore())
    org_store = OrgStore(InMemoryStore())
    mock = OllamaMock()
    mock.respond = _smart_respond
    token_store = TokenStore(InMemoryStore(), ttl_minutes=480, now_factory=datetime.now)

    main_app.dependency_overrides[deps_module.get_user_directory] = lambda: directory
    main_app.dependency_overrides[deps_module.get_token_store] = lambda: token_store
    main_app.dependency_overrides[deps_module.get_idea_ledger] = lambda: ledger
    main_app.dependency_overrides[deps_module.get_assistant_client] = lambda: mock
    main_app.dependency_overrides[deps_module.get_notification_store] = lambda: notifications
    main_app.dependency_overrides[deps_module.get_conversation_store] = lambda: conversations
    main_app.dependency_overrides[deps_module.get_org_store] = lambda: org_store
    main_app.dependency_overrides.pop(deps_module.get_assistant_check, None)

    def _client(user_id: str = PROPOSER, token: bool = True) -> TestClient:
        if not token:
            return TestClient(main_app)
        roles = tuple(directory.get(user_id)["roles"])
        session = token_store.issue(user_id, roles, now=datetime.now())
        return TestClient(main_app,
                          headers={"Authorization": f"Bearer {session.token}"})

    return SimpleNamespace(directory=directory, ledger=ledger,
                           conversations=conversations, notifications=notifications,
                           mock=mock, token_store=token_store, client=_client)


def _seed_resumen_conversation(env, captured: dict, conv_id: str,
                               user_id: str = PROPOSER) -> None:
    conversation = Conversation(id=conv_id, userId=user_id, state="RESUMEN",
                                capturedFields=captured)
    env.conversations.create(conversation)


# -- presence of every plan §3.1 endpoint --------------------------------------------


def test_every_endpoint_of_plan_3_1_is_present() -> None:
    spec = [
        ("post", "/auth/login"), ("post", "/auth/logout"), ("get", "/auth/me"),
        ("post", "/auth/change-password"),
        ("post", "/capture/start"), ("get", "/capture/assistant-status"),
        ("post", "/capture/messages"), ("post", "/capture/finish"),
        ("post", "/capture/activate-manual"),
        ("post", "/ideas"), ("get", "/ideas/me"), ("get", "/ideas/{id}"),
        ("put", "/ideas/{id}"), ("post", "/ideas/{id}/improve"),
        ("post", "/ideas/{id}/versions/{vid}/decide"),
        ("post", "/ideas/{id}/request-publication"),
        ("get", "/validation/queue"), ("post", "/validation/{id}/approve"),
        ("post", "/validation/{id}/reject"),
        ("get", "/catalog/public"),
        ("get", "/notifications"), ("post", "/notifications/{id}/read"),
        ("get", "/users"), ("post", "/users"),
        ("put", "/users/{id}/roles"), ("patch", "/users/{id}/active"),
        ("post", "/assistant/check"),
        ("get", "/admin/contexto/plantilla"), ("get", "/admin/contexto"),
        ("put", "/admin/contexto"), ("post", "/admin/contexto/subida"),
        ("get", "/health"),
    ]

    def _shape(path: str) -> str:
        return json.dumps([path]) if False else __import__("re").sub(
            r"\{[^}]+\}", "{P}", path)

    present = {
        (method.upper(), _shape(path))
        for path, methods in main_app.openapi()["paths"].items()
        for method in methods
    }
    expected = {
        (method.upper(), _shape(path))
        for method, path in spec
    }
    missing = sorted(expected - present)
    assert not missing, f"Endpoints del plan §3.1 ausentes: {missing}"


# -- health over a real `uvicorn app.main:app` process ---------------------------------


def test_health_over_a_real_uvicorn_process() -> None:
    data_dir = Path(tempfile.mkdtemp(prefix="innov-ia-smoke-"))
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    child_env = dict(os.environ)
    child_env.update({"PYTHONPATH": str(BACKEND_ROOT), "INNOV_DATA_DIR": str(data_dir)})

    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(BACKEND_ROOT), env=child_env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    status, body = None, ""
    deadline = time.time() + 30
    try:
        while time.time() < deadline:
            if process.poll() is not None:
                break
            try:
                connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
                try:
                    connection.request("GET", "/health")
                    response = connection.getresponse()
                    status, body = response.status, response.read().decode()
                    if status == 200:
                        break
                finally:
                    connection.close()
            except OSError:
                time.sleep(0.2)
        assert status == 200, (
            f"GET /health no respondió 200 sobre el proceso uvicorn real "
f"(status={status}, body={body!r})")
        assert json.loads(body) == {"status": "ok"}
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


# -- auth ---------------------------------------------------------------------------


def test_login_me_and_logout(env) -> None:
    login = env.client().post("/auth/login",
                              json={"username": "ana", "password": "clave123"})
    assert login.status_code == 200
    body = login.json()
    assert body["token"]
    assert body["user"]["username"] == "ana"
    assert body["user"]["roles"] == ["proponente"]
    assert body["mustChangePassword"] is False

    me = env.client().get("/auth/me").json()
    assert me["username"] == "ana"
    assert me["roles"] == ["proponente"]

    session = env.client()
    logout = session.post("/auth/logout")
    assert logout.status_code == 200
    assert logout.json() == {"ok": True}

    # The token was revoked by the logout: the same session now 401s.
    assert session.get("/auth/me").status_code == 401


def test_change_password_forced_flow(env) -> None:
    created = env.client(ADMIN).post(
        "/users", json={"username": "nuevo", "name": "Nuevo Usuario",
                        "roles": ["proponente"]})
    assert created.status_code == 201
    created = created.json()
    nuevo_id = created["user"]["id"]
    assert created["user"]["shouldChangePassword"] is True
    temporary = created["temporaryPassword"]

    assert env.client(nuevo_id).post(
        "/auth/change-password",
        json={"currentPassword": "incorrecta", "newPassword": "nueva123"}
    ).status_code == 401
    assert env.client(nuevo_id).post(
        "/auth/change-password",
        json={"currentPassword": temporary, "newPassword": "x"}
    ).status_code == 400

    changed = env.client(nuevo_id).post(
        "/auth/change-password",
        json={"currentPassword": temporary, "newPassword": "nueva123"})
    assert changed.status_code == 200
    assert changed.json()["shouldChangePassword"] is False

    assert env.client(nuevo_id).post(
        "/auth/change-password",
        json={"currentPassword": "nueva123", "newPassword": "otra123"}
    ).status_code == 409

    rel = env.client().post("/auth/login",
                            json={"username": "nuevo", "password": "nueva123"})
    assert rel.status_code == 200
    assert rel.json()["mustChangePassword"] is False
    # The proponent login triggers the on-demand refinement check in the
    # background; with an empty ledger it is a no-op OK pass.


# -- capture ------------------------------------------------------------------------


def test_capture_start_assistant_and_manual(env) -> None:
    started = env.client().post("/capture/start").json()
    assert started["mode"] == "assistant"
    assert started["resumed"] is False
    assert started["conversation"]["id"]
    assert started["assistant"]["currentField"] == "description"
    assert isinstance(started["assistant"]["quickOptions"], list)

    # A second start RESUMES the active conversation (RF-2, case 8): never a
    # duplicate, even after the assistant goes down.
    env.mock.available = False
    resumed = env.client().post("/capture/start").json()
    assert resumed["mode"] == "assistant"
    assert resumed["resumed"] is True
    assert resumed["conversation"]["id"] == started["conversation"]["id"]

    # A user without any conversation (beto) gets the manual-form signal
    # (RF-7 case 1) when the assistant is down: nothing is persisted.
    down = env.client(OTHER).post("/capture/start").json()
    assert down["mode"] == "manual"
    assert down["conversation"] is None
    assert "asistente no está disponible" in down["manual"]["notice"]
    assert down["manual"]["capturedFields"]


def test_capture_assistant_status_reports_ok_and_unavailable(env) -> None:
    assert env.client().get("/capture/assistant-status").json() == {"status": "OK"}
    env.mock.available = False
    assert env.client().get("/capture/assistant-status").json() == {"status": "UNAVAILABLE"}


def test_capture_messages_processes_a_turn(env) -> None:
    started = env.client().post("/capture/start").json()
    conv_id = started["conversation"]["id"]
    reply = env.client().post(
        "/capture/messages",
        json={"conversationId": conv_id, "message": "Quiero reducir los tiempos de compra."})
    assert reply.status_code == 200
    body = reply.json()
    assert body["conversationId"] == conv_id
    assert body["assistant"]["currentField"] == "title"
    assert env.conversations.get(conv_id)["state"] == "ACTIVA"


def test_capture_finish_registers_the_idea_from_the_resumen(env) -> None:
    seed = {
        "title": "Flujo digital de compras",
        "description": "Reducir tiempos de compra.",
        "problem": "Revisión manual duplicada.",
        "expectedBenefit": "120 horas al mes.",
        "strategicAlignment": "Agilizar la cadena de suministro.",
        "proponent": json.dumps({"name": "Ana Torres", "area": "Compras",
                                 "contact": "ana.torres@innov-ia.local"}),
    }
    _seed_resumen_conversation(env, seed, "c_seed_finish")
    result = env.client().post("/capture/finish", json={"conversationId": "c_seed_finish"})
    assert result.status_code == 201
    body = result.json()
    assert body["state"] == "EN_DESARROLLO"
    assert body["origin"] == "asistida"
    assert body["ideaId"].startswith("idea_")
    assert len(env.ledger.list()) == 1
    assert env.conversations.get("c_seed_finish")["state"] == "TERMINADA"


def test_capture_activate_manual_marks_contingency(env) -> None:
    seed = {
        "title": "Idea parcial",
        "description": "Una descripción capturada.",
        "proponent": json.dumps({"name": "Ana Torres", "area": "Compras",
                                 "contact": "ana.torres@innov-ia.local"}),
    }
    _seed_resumen_conversation(env, seed, "c_seed_manual")
    result = env.client().post("/capture/activate-manual",
                               json={"conversationId": "c_seed_manual"})
    assert result.status_code == 200
    body = result.json()
    assert body["state"] == "CONTINGENCIA"
    assert body["capturedFields"]["description"] == "Una descripción capturada."


# -- ideas --------------------------------------------------------------------------


def test_create_idea_201_and_422(env) -> None:
    created = env.client().post("/ideas", json=_fields())
    assert created.status_code == 201
    idea = created.json()
    assert idea["id"].startswith("idea_")
    assert idea["state"] == "EN_DESARROLLO"
    assert idea["origin"] == "manual"
    assert idea["ownerId"] == PROPOSER

    invalid = env.client().post("/ideas", json={})
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "IDEA_FIELDS_INVALID"


def test_my_ideas_lists_only_the_proponents_ideas(env) -> None:
    alpha = env.client().post("/ideas", json=_fields(title="Alpha")).json()
    env.client(OTHER).post("/ideas", json=_fields(title="Beta"))

    listing = env.client().get("/ideas/me")
    assert listing.status_code == 200
    entries = listing.json()
    assert {entry["id"] for entry in entries} == {alpha["id"]}
    assert set(entries[0]) == {"id", "title", "createdAt", "origin", "state"}


def test_idea_detail_for_the_owner_and_403_for_others(env) -> None:
    idea = env.client().post("/ideas", json=_fields()).json()

    detail = env.client().get(f"/ideas/{idea['id']}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["idea"]["id"] == idea["id"]
    assert isinstance(body["versions"], list)

    assert env.client(OTHER).get(f"/ideas/{idea['id']}").status_code == 403


def test_edit_idea_updates_the_seven_fields(env) -> None:
    idea = env.client().post("/ideas", json=_fields()).json()
    updated = env.client().put(
        f"/ideas/{idea['id']}",
        json=_fields(title="Título corregido manualmente"))
    assert updated.status_code == 200
    assert updated.json()["title"] == "Título corregido manualmente"


def test_improve_without_the_assistant_saves_the_request(env) -> None:
    env.mock.available = False
    idea = env.client().post("/ideas", json=_fields()).json()
    response = env.client().post(f"/ideas/{idea['id']}/improve",
                                 json={"instruction": "Cuantifica el beneficio"})
    assert response.status_code == 200
    body = response.json()
    assert body["notice"] == CASE_10_NOTICE
    assert body["improvementRequest"]["instruction"] == "Cuantifica el beneficio"


def test_improve_with_the_assistant_then_accept_the_version(env) -> None:
    idea = env.client().post("/ideas", json=_fields()).json()
    improved = env.client().post(f"/ideas/{idea['id']}/improve",
                                 json={"instruction": "Refuerza el problema"}).json()
    version_id = improved["version"]["id"]
    assert improved["version"]["status"] == "PENDIENTE"

    decided = env.client().post(
        f"/ideas/{idea['id']}/versions/{version_id}/decide",
        json={"decision": "accept"})
    assert decided.status_code == 200
    assert decided.json()["currentVersionId"] == version_id

    detail = env.client().get(f"/ideas/{idea['id']}").json()
    accepted = next(v for v in detail["versions"] if v["id"] == version_id)
    assert accepted["status"] == "VIGENTE"
    assert detail["idea"]["state"] == "EN_DESARROLLO"


def test_request_publication_reaches_solicitando_and_fans_out(env) -> None:
    idea = env.client().post("/ideas", json=_fields()).json()
    requested = env.client().post(f"/ideas/{idea['id']}/request-publication")
    assert requested.status_code == 200
    assert requested.json()["state"] == "SOLICITANDO_PUBLICACION"

    # Every active specialist sees it (RF-18).
    notifications = env.client(SPECIALIST).get("/notifications").json()
    assert notifications["unread"] >= 1


def test_approve_publishes_and_the_catalog_shows_it_without_contact(env) -> None:
    idea = env.client().post("/ideas", json=_fields()).json()
    env.client().post(f"/ideas/{idea['id']}/request-publication")

    approved = env.client(SPECIALIST).post(f"/validation/{idea['id']}/approve")
    assert approved.status_code == 200
    assert approved.json()["state"] == "VALIDADA_PUBLICA"
    assert approved.json()["publishedAt"]

    catalog = env.client(OTHER).get("/catalog/public").json()
    entries = {entry["id"]: entry for entry in catalog["zones"]["en-proceso"]}
    assert idea["id"] in entries
    entry = entries[idea["id"]]
    assert set(entry) == {"id", "title", "publishedAt", "description"}
    assert entry["title"] == "Optimización de los tiempos de compra"
    assert entry["publishedAt"]
    assert "contact" not in str(entry)


def test_reject_without_a_comment_is_a_400(env) -> None:
    idea = env.client().post("/ideas", json=_fields()).json()
    env.client().post(f"/ideas/{idea['id']}/request-publication")
    response = env.client(SPECIALIST).post(
        f"/validation/{idea['id']}/reject", json={"comment": "   "})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "REJECTION_COMMENT_REQUIRED"
    assert env.ledger.get(idea["id"])["state"] == "SOLICITANDO_PUBLICACION"


# -- assistant check + notifications ------------------------------------------------


def test_assistant_check_refines_then_the_owner_reads_the_notification(env) -> None:
    create_idea(env.ledger, owner_id=PROPOSER, origin="manual",
                fields=_fields(title="Idea manual por refinar"))

    check = env.client().post("/assistant/check")
    assert check.status_code == 200
    assert check.json() == {"status": "OK", "refined": 1, "failed": 0, "pending": 0}

    listing = env.client().get("/notifications").json()
    assert listing["unread"] == 1
    notice_id = listing["notifications"][0]["id"]

    read = env.client().post(f"/notifications/{notice_id}/read")
    assert read.status_code == 200
    assert read.json()["read"] is True
    assert env.client().get("/notifications").json()["unread"] == 0

    assert env.client(SPECIALIST).post(f"/notifications/{notice_id}/read").status_code == 403
    assert env.client().post("/notifications/nope/read").status_code == 404


def test_assistant_check_unavailable_reports_the_pending_queue(env) -> None:
    create_idea(env.ledger, owner_id=PROPOSER, origin="manual",
                fields=_fields(title="Idea manual sin IA"))
    env.mock.available = False

    check = env.client().post("/assistant/check")
    assert check.status_code == 200
    assert check.json() == {"status": "UNAVAILABLE", "refined": 0, "failed": 0,
                            "pending": 1}


# -- users (admin surface) ----------------------------------------------------------


def test_users_admin_surface_create_roles_and_deactivate(env) -> None:
    listing = env.client(ADMIN).get("/users")
    assert listing.status_code == 200
    assert {user["username"] for user in listing.json()} >= {"ana", "beto", "solo", "admin"}

    created = env.client(ADMIN).post(
        "/users", json={"username": "carlos", "name": "Carlos", "roles": ["proponente"]})
    assert created.status_code == 201
    assert created.json()["user"]["shouldChangePassword"] is True

    roles = env.client(ADMIN).put(f"/users/{OTHER}/roles",
                                  json={"roles": ["proponente", "especialista"]})
    assert roles.status_code == 200
    assert set(roles.json()["roles"]) == {"proponente", "especialista"}

    toggled = env.client(ADMIN).patch(f"/users/{OTHER}/active")
    assert toggled.status_code == 200
    assert toggled.json()["active"] is False

    # A deactivated account loses access immediately (RF-17, case 16).
    assert env.client(OTHER).get("/ideas/me").status_code == 401


# -- access guards (session + role matrix) -------------------------------------------


def test_session_and_role_guards(env) -> None:
    anonymous = env.client(token=False)
    for path in ("/auth/me", "/auth/logout", "/ideas/me", "/capture/start",
                 "/capture/messages", "/assistant/check", "/validation/queue",
                 "/catalog/public", "/notifications", "/users"):
        method = anonymous.post if path in (
            "/auth/logout", "/capture/start", "/capture/messages",
            "/assistant/check") else anonymous.get
        assert method(path).status_code == 401

    # A pure specialist is out of the proponent surface (each on its real method).
    proponent_routes = {"/ideas/me": lambda c: c.get("/ideas/me"),
                        "/capture/start": lambda c: c.post("/capture/start"),
                        "/assistant/check": lambda c: c.post("/assistant/check")}
    for call in proponent_routes.values():
        assert call(env.client(SPECIALIST)).status_code == 403

    # A pure proponent is out of the specialist and admin surfaces.
    assert env.client().get("/users").status_code == 403
    assert env.client().post("/users",
                             json={"username": "x"}).status_code == 403
    assert env.client().get("/validation/queue").status_code == 403
    assert env.client().post("/validation/x/approve").status_code == 403
    assert env.client().post("/validation/x/reject",
                             json={"comment": "x"}).status_code == 403

    # An administrator is out of the specialist queue and the proponent surface.
    assert env.client(ADMIN).get("/validation/queue").status_code == 403
    assert env.client(ADMIN).get("/ideas/me").status_code == 403
