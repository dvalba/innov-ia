"""Users/roles end-to-end tests (T-067, RF-17, case 16).

Closes the full user-management cycle over a single live API surface, wiring
together the routers of `users` (admin panel, T-016) and `auth` (login /
forced change, T-013) against the shared in-memory contracts:

  1. the admin creates a user (201) and receives the one-time temporary
     password, which forces a change on the first access;
  2. the admin deactivates or strips the user: the access to the platform
     functions is lost while the account, its ideas and history are preserved
     (case 16);
  3. deactivating or stripping the last administrator is blocked with 409,
     and a second active administrator frees the block.

The queue of ideas of a deactivated user stays valid for the other
specialists (spec §7 case 16): the `validation` endpoints are not wired yet
(T-034, G10), so the state contract is asserted at the shared `IdeaLedger`
seam (T-008) — the exact object the validation feature will consume.
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app import deps as deps_module
from app.main import app as main_app
from features.auth.infrastructure.token_store import TokenStore
from shared.contracts.idea_ledger import (
    STATE_EN_DESARROLLO,
    STATE_SOLICITANDO_PUBLICACION,
)
from shared.exceptions.handlers import DomainError
from shared.utils.password import hash_password
from tests.conftest import InMemoryDirectory, InMemoryStore


class InMemoryIdeaLedger:
    """In-memory variant of the `IdeaLedger` contract for the e2e seam."""

    def __init__(self) -> None:
        self._ideas: dict[str, dict] = {}

    def put(self, idea: dict) -> None:
        self._ideas[idea["id"]] = dict(idea)

    def get(self, idea_id: str) -> dict | None:
        idea = self._ideas.get(idea_id)
        return dict(idea) if idea is not None else None

    def list_by_state(self, state: str, owner_id: str | None = None):
        return [dict(idea) for idea_id, idea in self._ideas.items()
                if idea["state"] == state and (owner_id is None or idea["ownerId"] == owner_id)]

    def list_by_owner(self, owner_id: str) -> list[dict]:
        return [dict(idea) for idea in self._ideas.values() if idea["ownerId"] == owner_id]

    def list_by_origin(self, origin: str, state: str, owner_id: str | None = None):
        return [dict(idea) for idea in self._ideas.values()
                if idea["origin"] == origin and idea["state"] == state
                and (owner_id is None or idea["ownerId"] == owner_id)]

    def save_current_fields(self, idea_id: str, fields: dict) -> dict:
        raise DomainError("IDEA_LEDGER_READ_ONLY", "No disponible en el e2e.", status_code=501)

    def get_version(self, idea_id: str, version_id: str) -> dict | None:
        return None


def _idea(idea_id: str, owner_id: str, state: str) -> dict:
    return {
        "id": idea_id,
        "title": "Idea de prueba",
        "proponent": {"name": "Prueba", "area": "Area", "contact": "p@x.com"},
        "description": "Descripcion de prueba de la iniciativa.",
        "problem": "Problema de prueba.",
        "expectedBenefit": "Beneficio de prueba.",
        "strategicAlignment": "Alineacion de prueba.",
        "ownerId": owner_id,
        "origin": "manual",
        "state": state,
        "createdAt": datetime.now().isoformat(),
    }


@pytest.fixture()
def env():
    directory = InMemoryDirectory()
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
    store = InMemoryStore()
    token_store = TokenStore(store, ttl_minutes=480, now_factory=datetime.now)
    ideas = InMemoryIdeaLedger()
    main_app.dependency_overrides[deps_module.get_user_directory] = lambda: directory
    main_app.dependency_overrides[deps_module.get_token_store] = lambda: token_store
    # T-062: the login trigger must not reach the real Ollama/JSON stores.
    main_app.dependency_overrides[deps_module.get_assistant_check] = (
        lambda: (lambda: {"status": "OK", "refined": 0, "failed": 0, "pending": 0})
    )
    return directory, token_store, ideas


@pytest.fixture()
def admin_client(env) -> TestClient:
    _, token_store, _ = env
    session = token_store.issue("u_admin", ("admin",))
    return TestClient(main_app, headers={"Authorization": f"Bearer {session.token}"})


def _plain() -> TestClient:
    return TestClient(main_app)


def _login(client: TestClient, username: str, password: str) -> dict | None:
    response = client.post("/auth/login", json={"username": username, "password": password})
    return response.json() if response.status_code == 200 else None


def _with(token: str) -> TestClient:
    return TestClient(main_app, headers={"Authorization": f"Bearer {token}"})


def test_e2e_create_temporal_forced_change(admin_client, env) -> None:
    """Step 1: create -> one-time temporary password -> forced change on the
    first access; the temporary password stops working afterwards."""
    directory, _, _ = env
    response = admin_client.post("/users", json={
        "username": "carlos", "name": "Carlos", "area": "Logistica",
        "contact": "carlos@corp.com", "roles": ["proponente"],
    })
    assert response.status_code == 201
    body = response.json()
    temporary = body["temporaryPassword"]
    user_id = body["user"]["id"]
    assert body["user"]["active"] is True
    assert "passwordHash" not in response.text
    # The temporary password is returned exactly once (RF-17).
    listing = {user["id"]: user for user in admin_client.get("/users").json()}
    assert listing[user_id]["shouldChangePassword"] is True
    assert "passwordHash" not in str(listing)

    client = _plain()
    login = _login(client, "carlos", temporary)
    assert login is not None
    assert login["mustChangePassword"] is True
    assert login["user"]["roles"] == ["proponente"]

    forced = _with(login["token"]).post(
        "/auth/change-password",
        json={"currentPassword": temporary, "newPassword": "carlos2026"})
    assert forced.status_code == 200
    assert forced.json()["shouldChangePassword"] is False

    assert _login(client, "carlos", temporary) is None, "the temporary password is single-use"
    again = _login(client, "carlos", "carlos2026")
    assert again is not None
    assert again["mustChangePassword"] is False
    assert directory.get(user_id) is not None, "the account record is preserved"


def test_e2e_deactivate_revokes_access_and_preserves_history(admin_client, env) -> None:
    """Step 2: deactivation loses the access (current session + new logins)
    while the account, the password change and the history are preserved
    (case 16); re-activation restores the access."""
    directory, token_store, ideas = env
    created = admin_client.post(
        "/users", json={"username": "ana", "name": "Ana", "roles": ["proponente"]}).json()
    user_id = created["user"]["id"]

    login = _login(_plain(), "ana", created["temporaryPassword"])
    assert login is not None
    new_password = "ana2026"
    changed = _with(login["token"]).post(
        "/auth/change-password",
        json={"currentPassword": created["temporaryPassword"], "newPassword": new_password})
    assert changed.status_code == 200

    ana = _with(login["token"])
    assert ana.get("/auth/me").status_code == 200
    assert ana.get("/auth/me").json()["roles"] == ["proponente"]

    ideas.put(_idea("idea_ana_1", user_id, STATE_EN_DESARROLLO))
    ideas.put(_idea("idea_ana_2", user_id, STATE_SOLICITANDO_PUBLICACION))

    # The admin deactivates a user that currently has an active session.
    toggle = admin_client.patch(f"/users/{user_id}/active")
    assert toggle.status_code == 200
    assert toggle.json()["active"] is False

    # ... the live session loses the access at once and the token is revoked.
    assert ana.get("/auth/me").status_code == 401
    assert token_store.resolve(login["token"]) is None
    assert _login(_plain(), "ana", new_password) is None, "no new logins while deactivated"

    # The account, the already-changed password and the history are preserved.
    stored = directory.get(user_id)
    assert stored is not None
    assert stored["active"] is False
    assert stored["shouldChangePassword"] is False
    assert [idea["id"] for idea in ideas.list_by_owner(user_id)] == ["idea_ana_1", "idea_ana_2"]

    # Re-activation restores the access with the new password.
    assert admin_client.patch(f"/users/{user_id}/active").json()["active"] is True
    back = _login(_plain(), "ana", new_password)
    assert back is not None
    assert back["mustChangePassword"] is False


def test_e2e_deactivated_requesting_ideas_stay_validatable(env) -> None:
    """A SOLICITANDO_PUBLICACION idea of a deactivated user remains in the
    queue that the other specialists will consume (case 16), while the
    deactivated account itself can no longer sign in."""
    directory, _, ideas = env
    owner = directory.create({
        "id": "u_out", "username": "out", "name": "Out", "area": "", "contact": "",
        "roles": ["proponente"], "active": False,
        "passwordHash": hash_password("clave123"), "shouldChangePassword": False,
    })
    ideas.put(_idea("idea_out_1", owner["id"], STATE_SOLICITANDO_PUBLICACION))
    ideas.put(_idea("idea_out_2", owner["id"], STATE_EN_DESARROLLO))

    assert _login(_plain(), "out", "clave123") is None
    assert [idea["id"] for idea in ideas.list_by_state(STATE_SOLICITANDO_PUBLICACION)] == ["idea_out_1"]
    assert [idea["id"] for idea in ideas.list_by_state(STATE_EN_DESARROLLO)] == ["idea_out_2"]


def test_e2e_role_revocation_keeps_account_and_blocks_functions(admin_client, env) -> None:
    """Revoking every role keeps the account (no deletion) but leaves the user
    without any platform function (RF-17: sin roles = sin acceso); the session
    is downgraded live and the account recovers the access when a role is
    assigned again."""
    directory, token_store, ideas = env
    created = admin_client.post(
        "/users", json={"username": "lucia", "name": "Lucia", "roles": ["proponente"]}).json()
    user_id = created["user"]["id"]
    ideas.put(_idea("idea_lucia_1", user_id, STATE_EN_DESARROLLO))

    session = token_store.issue(user_id, ("proponente",))
    lucia = _with(session.token)
    assert lucia.get("/auth/me").status_code == 200
    assert lucia.get("/auth/me").json()["roles"] == ["proponente"]
    assert lucia.get("/users").status_code == 403

    # The admin strips the roles: the session keeps existing, without roles.
    revoked = admin_client.put(f"/users/{user_id}/roles", json={"roles": []})
    assert revoked.status_code == 200
    assert revoked.json()["roles"] == []

    me = lucia.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["roles"] == [], "no roles: no access to the platform functions"
    assert lucia.get("/users").status_code == 403

    # The account and the history survive untouched.
    stored = directory.get(user_id)
    assert stored is not None
    assert stored["active"] is True
    assert stored["roles"] == []
    assert [idea["id"] for idea in ideas.list_by_owner(user_id)] == ["idea_lucia_1"]

    # Assigning the role back restores the functions for the same account.
    assert admin_client.put(f"/users/{user_id}/roles",
                            json={"roles": ["proponente"]}).json()["roles"] == ["proponente"]
    assert lucia.get("/auth/me").json()["roles"] == ["proponente"]


def test_e2e_last_admin_blocked_409(admin_client, env) -> None:
    """Step 3: deactivating or stripping the last administrator is blocked
    (409) in both directions; a second active administrator frees the block."""
    directory, _, _ = env
    revoke = admin_client.put("/users/u_admin/roles", json={"roles": ["proponente"]})
    assert revoke.status_code == 409
    assert revoke.json()["error"]["code"] == "LAST_ADMIN_REQUIRED"
    # The state is unchanged: the admin keeps the role and the panel access.
    roles = {user["id"]: user["roles"] for user in admin_client.get("/users").json()}
    assert roles["u_admin"] == ["admin"]

    deactivate = admin_client.patch("/users/u_admin/active")
    assert deactivate.status_code == 409
    assert deactivate.json()["error"]["code"] == "LAST_ADMIN_REQUIRED"
    assert directory.get("u_admin")["active"] is True

    # A second active administrator frees the block for the first one.
    _, token_store, _ = env
    second = admin_client.post(
        "/users", json={"username": "admin2", "name": "Admin 2", "roles": ["admin"]}).json()
    second_id = second["user"]["id"]
    assert admin_client.patch("/users/u_admin/active").json()["active"] is False
    # The first admin's own session has been revoked by its deactivation.
    assert admin_client.get("/auth/me").status_code == 401
    # The new administrator is in turn the only active one: it is protected.
    second_token = token_store.issue(second_id, ("admin",))
    second_client = _with(second_token.token)
    blocked = second_client.patch(f"/users/{second_id}/active")
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "LAST_ADMIN_REQUIRED"
    assert directory.get(second_id)["active"] is True
