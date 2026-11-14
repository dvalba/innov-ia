"""Admin debate-days API tests (T-089, RF-24, RNF-11).

Covers the administrator-only surface on `/admin/debate-days`: the GET (the
default `{debateDays: 30, updatedBy: null, updatedAt: null}` when nothing is
saved, the stored record otherwise), the PUT (persist + audit
`updatedBy`/`updatedAt`), the 422 `DEBATE_DAYS_INVALID` for a malformed payload
(a non-integer, a boolean, a float, an out-of-range or a missing field), and
the 401/403 for a non-admin or an absent session.

The global debate-days store is injected by the autouse `debate_days_store`
fixture (conftest), so every request of a test reads/writes the same in-memory
record and no file is touched.
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
    """Issues bearer-authenticated clients against the in-memory debate-days store."""
    token_store = TokenStore(InMemoryStore(), ttl_minutes=480, now_factory=datetime.now)
    main_app.dependency_overrides[deps_module.get_user_directory] = lambda: directory
    main_app.dependency_overrides[deps_module.get_token_store] = lambda: token_store
    main_app.dependency_overrides[deps_module.get_assistant_check] = (
        lambda: (lambda: {"status": "OK", "refined": 0, "failed": 0, "pending": 0})
    )

    def _client(user_id: str = "u_admin", token: bool = True) -> TestClient:
        if not token:
            return TestClient(main_app)
        roles = tuple(directory.get(user_id)["roles"])
        session = token_store.issue(user_id, roles, now=datetime.now())
        return TestClient(main_app, headers={"Authorization": f"Bearer {session.token}"})

    return _client


# -- role guard (401 / 403) -----------------------------------------------------


def test_all_debate_days_endpoints_require_an_admin_session(auth) -> None:
    proponente = auth("u_ana")
    assert proponente.get("/admin/debate-days").status_code == 403
    assert proponente.put("/admin/debate-days", json={"debateDays": 40}).status_code == 403

    # Without a session at all, the surface is 401.
    anon = auth(token=False)
    assert anon.get("/admin/debate-days").status_code == 401
    assert anon.put("/admin/debate-days", json={"debateDays": 40}).status_code == 401


# -- read (RF-24, v2.4) ---------------------------------------------------------


def test_get_returns_the_default_30_when_nothing_is_saved(auth, debate_days_store) -> None:
    response = auth().get("/admin/debate-days")
    assert response.status_code == 200
    assert response.json() == {"debateDays": 30, "updatedBy": None, "updatedAt": None}
    assert debate_days_store.has() is False  # a read never persists


def test_get_returns_the_stored_record(auth, debate_days_store) -> None:
    auth().put("/admin/debate-days", json={"debateDays": 45})
    response = auth().get("/admin/debate-days")
    assert response.status_code == 200
    body = response.json()
    assert body["debateDays"] == 45
    assert body["updatedBy"] == "u_admin"
    assert body["updatedAt"]


# -- write (RF-24, RNF-11) -------------------------------------------------------


def test_put_persists_and_audits_the_record(auth, debate_days_store) -> None:
    response = auth().put("/admin/debate-days", json={"debateDays": 20})
    assert response.status_code == 200
    body = response.json()
    assert body["debateDays"] == 20
    assert body["updatedBy"] == "u_admin"
    assert body["updatedAt"]

    # The second GET reflects the persisted record.
    again = auth().get("/admin/debate-days")
    assert again.status_code == 200
    assert again.json() == body


def test_put_replaces_the_previous_record(auth) -> None:
    auth().put("/admin/debate-days", json={"debateDays": 30})
    response = auth().put("/admin/debate-days", json={"debateDays": 90})
    assert response.status_code == 200
    assert response.json()["debateDays"] == 90


@pytest.mark.parametrize("payload", [
    {"debateDays": 0},
    {"debateDays": 91},
    {"debateDays": -1},
    {"debateDays": 30.0},
    {"debateDays": "30"},
    {"debateDays": True},
    {"debateDays": None},
    {},
])
def test_put_rejects_a_malformed_payload_with_422(auth, payload, debate_days_store) -> None:
    response = auth().put("/admin/debate-days", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "DEBATE_DAYS_INVALID"
    assert response.json()["error"]["details"]["problems"]
    assert debate_days_store.has() is False  # nothing persisted on a rejection
