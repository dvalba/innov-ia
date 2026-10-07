"""Catalog router API tests (T-035, RF-20, RNF-7, plan §3.1).

Covers the public catalog: `GET /catalog/public` is read-only for any active
session (401 without one) and returns only `VALIDADA_PUBLICA` ideas — with the 7
fields (proponent reduced to name/area, never contact), the origin and the
registration/publication dates. Ideas in any other state are absent.
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app import deps as deps_module
from app.main import app as main_app
from features.auth.infrastructure.token_store import TokenStore
from features.ideas.infrastructure.idea_store import IdeaStore
from shared.contracts.idea_ledger import IDEA_FIELDS
from shared.utils.password import hash_password
from tests.conftest import InMemoryDirectory, InMemoryStore, OllamaMock


def _fields(**overrides: object) -> dict:
    base: dict = {
        "title": "Optimización de la aprobación de proveedores",
        "proponent": {"name": "Ana Torres", "area": "Compras",
                      "contact": "ana.torres@innov-ia.local"},
        "description": "Digitalizar la validación de proveedores.",
        "problem": "Revisión manual duplicada.",
        "expectedBenefit": "120 horas ahorradas al mes.",
        "strategicAlignment": "Agilizar la cadena de suministro.",
        "estimatedResources": {"time": "6 semanas", "people": "2 personas",
                               "budget": "50000 PLN"},
    }
    base.update(overrides)
    return base


@pytest.fixture()
def directory() -> InMemoryDirectory:
    store = InMemoryDirectory()
    for user_id, name, roles in (
        ("u_ana", "Ana", ["proponente"]),
        ("u_beto", "Beto", ["proponente"]),
        ("u_solo", "Solo Esp.", ["especialista"]),
    ):
        store.create({
            "id": user_id,
            "username": user_id.removeprefix("u_"),
            "name": name,
            "area": "Calidad",
            "contact": f"{user_id.removeprefix('u_')}@corp.com",
            "roles": roles,
            "active": True,
            "passwordHash": hash_password("clave123"),
            "shouldChangePassword": False,
        })
    return store


@pytest.fixture()
def idea_ledger() -> IdeaStore:
    return IdeaStore(InMemoryStore(), InMemoryStore())


@pytest.fixture()
def auth(directory, idea_ledger):
    token_store = TokenStore(InMemoryStore(), ttl_minutes=480, now_factory=datetime.now)
    main_app.dependency_overrides[deps_module.get_user_directory] = lambda: directory
    main_app.dependency_overrides[deps_module.get_token_store] = lambda: token_store
    main_app.dependency_overrides[deps_module.get_idea_ledger] = lambda: idea_ledger
    main_app.dependency_overrides[deps_module.get_assistant_client] = (
        lambda: OllamaMock(available=False)
    )

    def _client(user_id: str = "u_solo", token: bool = True) -> TestClient:
        if not token:
            return TestClient(main_app)
        roles = tuple(directory.get(user_id)["roles"])
        session = token_store.issue(user_id, roles, now=datetime.now())
        return TestClient(main_app, headers={"Authorization": f"Bearer {session.token}"})

    return _client


# -- access guards ------------------------------------------------------------------


def test_public_catalog_requires_an_active_session_401(auth) -> None:
    assert auth(token=False).get("/catalog/public").status_code == 401


def test_public_catalog_is_open_to_any_active_role(auth) -> None:
    # The catalog is role-agnostic (RF-20): a specialist can read it.
    assert auth("u_solo").get("/catalog/public").status_code == 200
    # ... and even a pure proponent (the public surface).
    assert auth("u_ana").get("/catalog/public").status_code == 200


# -- content contract (RF-20, decision #2, RNF-7) -------------------------------------


def test_public_catalog_lists_only_validada_publica(auth) -> None:
    # Approved -> in the catalog.
    approved = auth("u_ana").post("/ideas", json=_fields()).json()
    auth("u_ana").post(f"/ideas/{approved['id']}/request-publication")
    auth("u_solo").post(f"/validation/{approved['id']}/approve")
    # In development -> out of the catalog.
    auth("u_beto").post("/ideas", json=_fields(title="Otra, en desarrollo")).json()
    # Waiting for review -> out of the catalog (decision #2: only published).
    solicitado = auth("u_beto").post("/ideas", json=_fields(title="Solicitando")).json()
    auth("u_beto").post(f"/ideas/{solicitado['id']}/request-publication")

    catalog = auth("u_solo").get("/catalog/public").json()
    assert [entry["id"] for entry in catalog] == [approved["id"]]


def test_catalog_entry_holds_the_fields_without_contact_and_with_dates(auth) -> None:
    approved = auth("u_ana").post("/ideas", json=_fields()).json()
    auth("u_ana").post(f"/ideas/{approved['id']}/request-publication")
    auth("u_solo").post(f"/validation/{approved['id']}/approve")

    entry = auth("u_solo").get("/catalog/public").json()[0]
    assert set(entry) == {"id", "fields", "origin", "createdAt", "publishedAt"}
    assert set(entry["fields"]) == set(IDEA_FIELDS)
    # The proponent is reduced to name/area; the contact is never exposed (RNF-7).
    assert entry["fields"]["proponent"] == {"name": "Ana Torres", "area": "Compras"}
    assert "contact" not in entry["fields"]["proponent"]
    assert entry["origin"] == "manual"
    assert entry["createdAt"]
    assert entry["publishedAt"]
    # The full idea payload (contact included) is not leaked through the catalog.
    assert "contact" not in str(entry)


def test_public_catalog_never_leaks_another_users_contact(auth) -> None:
    idea = auth("u_beto").post("/ideas", json=_fields(
        proponent={"name": "Beto", "area": "Logistica", "contact": "beto@corp.com"}
    )).json()
    auth("u_beto").post(f"/ideas/{idea['id']}/request-publication")
    auth("u_solo").post(f"/validation/{idea['id']}/approve")
    entry = auth("u_ana").get("/catalog/public").json()[0]
    assert entry["fields"]["proponent"]["name"] == "Beto"
    assert "beto@corp.com" not in str(entry)
