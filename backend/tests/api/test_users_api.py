"""Users router API tests (T-016, RF-17, RNF-7).

Covers the administrator-only surface: 201 with one-time temporary password,
403 for non-admin sessions and 409 when the operation would leave the system
without an active administrator (last-admin rule, T-015).
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app import deps as deps_module
from app.main import app as main_app
from features.auth.infrastructure.token_store import TokenStore
from shared.utils.password import hash_password
from tests.conftest import InMemoryDirectory, InMemoryStore


@pytest.fixture()
def directory() -> InMemoryDirectory:
    store = InMemoryDirectory()
    store.create({
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
    store.create({
        "id": "u_ana",
        "username": "ana",
        "name": "Ana",
        "area": "Produccion",
        "contact": "ana@corp.com",
        "roles": ["proponente"],
        "active": True,
        "passwordHash": hash_password("clave123"),
        "shouldChangePassword": False,
    })
    return store


@pytest.fixture()
def auth(directory):
    """Issues bearer-authenticated clients for a given (user, roles) pair."""
    token_store = TokenStore(InMemoryStore(), ttl_minutes=480, now_factory=datetime.now)
    main_app.dependency_overrides[deps_module.get_user_directory] = lambda: directory
    main_app.dependency_overrides[deps_module.get_token_store] = lambda: token_store

    def _client(user_id: str = "u_admin", roles: tuple[str, ...] = ("admin",),
                token: bool = True) -> TestClient:
        if not token:
            return TestClient(main_app)
        session = token_store.issue(user_id, roles, now=datetime.now())
        return TestClient(main_app, headers={"Authorization": f"Bearer {session.token}"})

    return _client


def test_list_users_requires_admin_401_and_403(auth) -> None:
    assert auth(token=False).get("/users").status_code == 401
    assert auth("u_ana", ("proponente",)).get("/users").status_code == 403
    response = auth().get("/users")
    assert response.status_code == 200
    usernames = {user["username"] for user in response.json()}
    assert usernames == {"admin", "ana"}
    assert "passwordHash" not in response.text


def test_create_user_201_returns_temporary_password_once(auth, directory) -> None:
    response = auth().post("/users", json={
        "username": "carlos",
        "name": "Carlos",
        "area": "Logistica",
        "contact": "carlos@corp.com",
        "roles": ["proponente"],
    })
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["username"] == "carlos"
    assert body["temporaryPassword"]
    assert "passwordHash" not in response.text

    # The temporary password is usable on the first access (forced change).
    login = TestClient(main_app).post(
        "/auth/login",
        json={"username": "carlos", "password": body["temporaryPassword"]})
    assert login.status_code == 200
    assert login.json()["mustChangePassword"] is True

    # A second creation with the same username conflicts (409).
    again = auth().post("/users", json={"username": "carlos"})
    assert again.status_code == 409


def test_create_user_unknown_role_400(auth) -> None:
    response = auth().post("/users", json={"username": "otro", "roles": ["supervisor"]})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UNKNOWN_ROLE"


def test_assign_roles_200_and_unknown_role_400(auth) -> None:
    response = auth().put("/users/u_ana/roles", json={"roles": ["proponente", "especialista"]})
    assert response.status_code == 200
    assert sorted(response.json()["roles"]) == ["especialista", "proponente"]

    bad = auth().put("/users/u_ana/roles", json={"roles": ["x"]})
    assert bad.status_code == 400


def test_revoke_last_admin_409(auth) -> None:
    response = auth().put("/users/u_admin/roles", json={"roles": ["proponente"]})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "LAST_ADMIN_REQUIRED"

    toggle = auth().patch("/users/u_admin/active")
    assert toggle.status_code == 409


def test_toggle_active_non_admin_ok(auth) -> None:
    deactivated = auth().patch("/users/u_ana/active")
    assert deactivated.status_code == 200
    assert deactivated.json()["active"] is False
    reactivated = auth().patch("/users/u_ana/active")
    assert reactivated.status_code == 200
    assert reactivated.json()["active"] is True


def test_toggle_unknown_user_404(auth) -> None:
    assert auth().patch("/users/u_nadie/active").status_code == 404
