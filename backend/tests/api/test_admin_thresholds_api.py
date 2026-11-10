"""Admin calibration-thresholds API tests (T-081, RF-28, case 31).

Covers the administrator-only surface on `/admin/calibration-thresholds`:
the GET (default 4/7 when nothing is saved, the stored record otherwise),
the PUT (persist + audit `updatedBy`/`updatedAt`), the 422 `THRESHOLDS_INVALID`
for a malformed payload, and the 401/403 for a non-admin or absent session.
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app import deps as deps_module
from app.main import app as main_app
from features.auth.infrastructure.token_store import TokenStore
from features.validation.infrastructure.threshold_store import ThresholdStore
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
def threshold_store() -> ThresholdStore:
    return ThresholdStore(InMemoryStore())


@pytest.fixture()
def auth(directory, threshold_store):
    """Issues bearer-authenticated clients against an in-memory thresholds store."""
    token_store = TokenStore(InMemoryStore(), ttl_minutes=480, now_factory=datetime.now)
    main_app.dependency_overrides[deps_module.get_user_directory] = lambda: directory
    main_app.dependency_overrides[deps_module.get_token_store] = lambda: token_store
    main_app.dependency_overrides[deps_module.get_threshold_store] = lambda: threshold_store
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


def test_all_threshold_endpoints_require_an_admin_session(auth) -> None:
    proponente = auth("u_ana")
    assert proponente.get("/admin/calibration-thresholds").status_code == 403
    assert proponente.put(
        "/admin/calibration-thresholds",
        json={"rejectionThreshold": 3, "acceptanceThreshold": 8},
    ).status_code == 403

    # Without a session at all, the surface is 401.
    anon = auth(token=False)
    assert anon.get("/admin/calibration-thresholds").status_code == 401
    assert anon.put(
        "/admin/calibration-thresholds",
        json={"rejectionThreshold": 3, "acceptanceThreshold": 8},
    ).status_code == 401


# -- read (RF-28, case 31) ------------------------------------------------------


def test_get_returns_the_default_4_7_when_nothing_is_saved(auth, threshold_store) -> None:
    response = auth().get("/admin/calibration-thresholds")
    assert response.status_code == 200
    assert response.json() == {"rejectionThreshold": 4, "acceptanceThreshold": 7}
    assert threshold_store.has() is False  # a read never persists


def test_get_returns_the_stored_record(auth, threshold_store) -> None:
    auth().put("/admin/calibration-thresholds",
               json={"rejectionThreshold": 3, "acceptanceThreshold": 8})
    response = auth().get("/admin/calibration-thresholds")
    assert response.status_code == 200
    body = response.json()
    assert body["rejectionThreshold"] == 3
    assert body["acceptanceThreshold"] == 8
    assert body["updatedBy"] == "u_admin"
    assert body["updatedAt"]


# -- write (RF-28, RNF-8) -------------------------------------------------------


def test_put_persists_and_audits_the_record(auth, threshold_store) -> None:
    response = auth().put("/admin/calibration-thresholds",
                          json={"rejectionThreshold": 2, "acceptanceThreshold": 9})
    assert response.status_code == 200
    body = response.json()
    assert body["rejectionThreshold"] == 2
    assert body["acceptanceThreshold"] == 9
    assert body["updatedBy"] == "u_admin"
    assert body["updatedAt"]

    # The second GET reflects the persisted record.
    again = auth().get("/admin/calibration-thresholds")
    assert again.status_code == 200
    assert again.json() == body


def test_put_replaces_the_previous_record(auth, threshold_store) -> None:
    auth().put("/admin/calibration-thresholds",
               json={"rejectionThreshold": 4, "acceptanceThreshold": 7})
    response = auth().put("/admin/calibration-thresholds",
                          json={"rejectionThreshold": 1, "acceptanceThreshold": 10})
    assert response.status_code == 200
    assert response.json()["rejectionThreshold"] == 1
    assert response.json()["acceptanceThreshold"] == 10


@pytest.mark.parametrize("payload", [
    {"rejectionThreshold": 0, "acceptanceThreshold": 7},
    {"rejectionThreshold": 11, "acceptanceThreshold": 7},
    {"rejectionThreshold": 4, "acceptanceThreshold": 0},
    {"rejectionThreshold": 4, "acceptanceThreshold": 11},
    {"rejectionThreshold": 5, "acceptanceThreshold": 5},
    {"rejectionThreshold": 7, "acceptanceThreshold": 4},
    {"rejectionThreshold": 4.5, "acceptanceThreshold": 7},
    {"rejectionThreshold": "5", "acceptanceThreshold": 7},
    {"rejectionThreshold": True, "acceptanceThreshold": 7},
    {"acceptanceThreshold": 7},
    {"rejectionThreshold": 4},
    {},
])
def test_put_rejects_a_malformed_payload_with_422(auth, payload, threshold_store) -> None:
    response = auth().put("/admin/calibration-thresholds", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "THRESHOLDS_INVALID"
    assert response.json()["error"]["details"]["problems"]
    assert threshold_store.has() is False  # nothing persisted on a rejection
