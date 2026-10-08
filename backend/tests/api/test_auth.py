"""Auth router API tests (T-013): login/logout/me/change-password.

Covers RF-1, RF-17 forced change (409 when not forced), 401/403 codes and
case 15 (expired session -> 401).
"""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from features.auth.infrastructure.token_store import TokenStore
from shared.utils.password import hash_password
from tests.conftest import InMemoryDirectory, InMemoryStore

NOW = datetime(2026, 9, 16, 12, 0, 0)


@pytest.fixture()
def env():
    directory = InMemoryDirectory()
    directory.create({
        "id": "u_1",
        "username": "ana",
        "name": "Ana",
        "area": "Produccion",
        "contact": "ana@corp.com",
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
    store = InMemoryStore()
    token_store = TokenStore(store, ttl_minutes=480, now_factory=lambda: NOW)
    return directory, token_store


@pytest.fixture()
def auth_client(app, env) -> TestClient:
    directory, token_store = env
    from app import deps as deps_module

    app.dependency_overrides[deps_module.get_user_directory] = lambda: directory
    app.dependency_overrides[deps_module.get_token_store] = lambda: token_store
    # T-062: the login trigger must not reach the real Ollama/JSON stores.
    app.dependency_overrides[deps_module.get_assistant_check] = (
        lambda: (lambda: {"status": "OK", "refined": 0, "failed": 0, "pending": 0})
    )
    return TestClient(app)


def test_login_success_200_token_and_user(auth_client: TestClient) -> None:
    response = auth_client.post("/auth/login", json={"username": "ana", "password": "clave123"})
    assert response.status_code == 200
    body = response.json()
    assert body["token"]
    assert body["user"]["username"] == "ana"
    assert body["user"]["roles"] == ["proponente"]
    assert body["mustChangePassword"] is False


def test_login_invalid_credentials_401(auth_client: TestClient) -> None:
    response = auth_client.post("/auth/login", json={"username": "ana", "password": "mala"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert "passwordHash" not in response.text


def test_me_requires_session_401(auth_client: TestClient) -> None:
    assert auth_client.get("/auth/me").status_code == 401


def test_me_with_session_200(auth_client: TestClient) -> None:
    login = auth_client.post("/auth/login", json={"username": "ana", "password": "clave123"}).json()
    headers = {"Authorization": f"Bearer {login['token']}"}
    response = auth_client.get("/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["username"] == "ana"
    assert response.json()["roles"] == ["proponente"]


def test_session_expired_returns_401(auth_client: TestClient, env) -> None:
    """Case 15: an expired session is rejected (401)."""
    _, token_store = env
    expired = token_store.issue("u_1", ("proponente",), now=NOW - timedelta(days=2))
    headers = {"Authorization": f"Bearer {expired.token}"}
    assert auth_client.get("/auth/me", headers=headers).status_code == 401


def test_logout_revokes_session(auth_client: TestClient) -> None:
    login = auth_client.post("/auth/login", json={"username": "ana", "password": "clave123"}).json()
    headers = {"Authorization": f"Bearer {login['token']}"}
    assert auth_client.post("/auth/logout", headers=headers).status_code == 200
    assert auth_client.get("/auth/me", headers=headers).status_code == 401


def test_logout_without_session_401(auth_client: TestClient) -> None:
    assert auth_client.post("/auth/logout").status_code == 401


def test_require_role_rejects_session_without_role(env, app) -> None:
    """require_role rejects a session without the role (403, RNF-7) and
    accepts one that has it (200)."""
    from fastapi import APIRouter, FastAPI

    from app import deps as deps_module
    from app.deps import role_dependency
    from shared.exceptions.handlers import register_exception_handlers

    directory, token_store = env
    guarded_app = FastAPI()
    register_exception_handlers(guarded_app)
    guarded_app.dependency_overrides[deps_module.get_user_directory] = lambda: directory
    guarded_app.dependency_overrides[deps_module.get_token_store] = lambda: token_store
    guarded = APIRouter()

    admin_dep = role_dependency("admin")

    @guarded.get("/admin-only")
    def admin_only(session: admin_dep):
        return {"user": session.user_id}

    guarded_app.include_router(guarded)
    client = TestClient(guarded_app)

    # Build sessions via the same token store (bypassing /auth/login, which
    # lives on the main app). The guard resolves with the real clock, so the
    # tokens are issued now (otherwise they would read as expired).
    session = token_store.issue("u_1", ("proponente",), now=datetime.now())
    assert client.get("/admin-only", headers={"Authorization": f"Bearer {session.token}"}).status_code == 403

    admin_session = token_store.issue("u_admin", ("admin",), now=datetime.now())
    assert client.get("/admin-only", headers={"Authorization": f"Bearer {admin_session.token}"}).status_code == 200

    assert client.get("/admin-only").status_code == 401


def test_change_password_not_forced_409(auth_client: TestClient) -> None:
    login = auth_client.post("/auth/login", json={"username": "ana", "password": "clave123"}).json()
    headers = {"Authorization": f"Bearer {login['token']}"}
    response = auth_client.post("/auth/change-password",
                                json={"currentPassword": "clave123", "newPassword": "nueva123"},
                                headers=headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PASSWORD_CHANGE_NOT_REQUIRED"


def test_change_password_forced_flow(auth_client: TestClient, env) -> None:
    directory, _ = env
    directory.update("u_1", {"shouldChangePassword": True})
    login = auth_client.post("/auth/login", json={"username": "ana", "password": "clave123"}).json()
    assert login["mustChangePassword"] is True
    headers = {"Authorization": f"Bearer {login['token']}"}
    response = auth_client.post("/auth/change-password",
                                json={"currentPassword": "clave123", "newPassword": "nueva123"},
                                headers=headers)
    assert response.status_code == 200
    # The new credentials work and the flag is cleared.
    again = auth_client.post("/auth/login", json={"username": "ana", "password": "nueva123"}).json()
    assert again["mustChangePassword"] is False
    assert auth_client.post("/auth/login", json={"username": "ana", "password": "clave123"}).status_code == 401


def test_change_password_wrong_current_401(auth_client: TestClient, env) -> None:
    directory, _ = env
    directory.update("u_1", {"shouldChangePassword": True})
    login = auth_client.post("/auth/login", json={"username": "ana", "password": "clave123"}).json()
    headers = {"Authorization": f"Bearer {login['token']}"}
    response = auth_client.post("/auth/change-password",
                                json={"currentPassword": "mala", "newPassword": "nueva123"},
                                headers=headers)
    assert response.status_code == 401
