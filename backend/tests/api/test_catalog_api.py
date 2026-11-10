"""Catalog router API tests (T-035, T-077, RF-20, RF-23, RNF-7, plan §3.1).

Covers the public catalog: `GET /catalog/public` is read-only for any active
session (401 without one) and returns only `VALIDADA_PUBLICA` ideas — with the
6 fields (proponent reduced to name/area, never contact), the origin and the
registration/publication dates. Ideas in any other state are absent. And the
public detail (`GET /catalog/{ideaId}`, RF-23): the same fields plus the final
`evaluation` and the immutable `aiEvaluation` snapshot, only for published
ideas — an unknown id or an unpublished idea is a 404.
"""

import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app import deps as deps_module
from app.main import app as main_app
from features.auth.infrastructure.token_store import TokenStore
from features.ideas.infrastructure.idea_store import IdeaStore
from shared.contracts.evaluation import EVALUATION_CRITERIA
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
        ("u_admin", "Admin", ["admin"]),
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
def mock() -> OllamaMock:
    return OllamaMock(available=False)


@pytest.fixture()
def auth(directory, idea_ledger, mock):
    token_store = TokenStore(InMemoryStore(), ttl_minutes=480, now_factory=datetime.now)
    main_app.dependency_overrides[deps_module.get_user_directory] = lambda: directory
    main_app.dependency_overrides[deps_module.get_token_store] = lambda: token_store
    main_app.dependency_overrides[deps_module.get_idea_ledger] = lambda: idea_ledger
    main_app.dependency_overrides[deps_module.get_assistant_client] = lambda: mock

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


# -- public detail (T-077, RF-23, plan line 708) -------------------------------------


def evaluation_json() -> str:
    """A contract-shaped AI reply: exactly the 5 criteria, score + justification."""
    return json.dumps(
        {key: {"score": 7, "justification": f"Valoración IA de {key}."}
         for key in EVALUATION_CRITERIA},
        ensure_ascii=False,
    )


def _publish(auth, mock, *, available: bool, respond=None, **field_overrides) -> dict:
    """Creates + requests + approves an idea; returns the created idea payload.

    `respond`, when given, is the assistant's reply (a `prompt -> str` callable,
    as in `test_evaluation_api.py`).
    """
    mock.available = available
    if respond is not None:
        mock.respond = respond
    idea = auth("u_ana").post("/ideas", json=_fields(**field_overrides)).json()
    auth("u_ana").post(f"/ideas/{idea['id']}/request-publication")
    auth("u_solo").post(f"/validation/{idea['id']}/approve")
    return idea


PAST_DEADLINE = "2020-01-01T00:00:00"


def _close(auth, idea_id: str) -> dict:
    """Closes the idea's debate through the real admin path: the deadline
    moves into the past and the next read runs the closure (the AI evaluation
    is generated at the debate's closure, RF-26)."""
    auth("u_admin").put(f"/admin/ideas/{idea_id}/debate/deadline",
                        json={"deadline": PAST_DEADLINE})
    return auth("u_solo").get(f"/catalog/{idea_id}/debate").json()


def test_detail_requires_an_active_session_401(auth) -> None:
    assert auth(token=False).get("/catalog/u_ana_1").status_code == 401


def test_detail_is_open_to_any_active_role(auth, mock) -> None:
    idea = _publish(auth, mock, available=False)
    # A specialist reads it ... (RF-23: any session).
    assert auth("u_solo").get(f"/catalog/{idea['id']}").status_code == 200
    # ... and so does a pure proponent (the public surface).
    assert auth("u_ana").get(f"/catalog/{idea['id']}").status_code == 200


def test_detail_of_an_unknown_id_is_a_404(auth, mock) -> None:
    assert auth("u_ana").get("/catalog/idea_inexistente").status_code == 404


def test_detail_of_an_unpublished_idea_is_a_404(auth, mock) -> None:
    # In development: exists, but the catalog never leaks it (RF-20 guard).
    idea = auth("u_beto").post("/ideas", json=_fields(title="Borrador")).json()
    assert auth("u_beto").get(f"/catalog/{idea['id']}").status_code == 404
    # Waiting for review: same, the publication is what makes it visible.
    solicitado = auth("u_beto").post("/ideas", json=_fields(title="Solicitando")).json()
    auth("u_beto").post(f"/ideas/{solicitado['id']}/request-publication")
    assert auth("u_solo").get(f"/catalog/{solicitado['id']}").status_code == 404


def test_detail_holds_the_fields_before_the_debate_closes(auth, mock) -> None:
    # No AI runs at publication: the evaluation is generated at the debate's
    # closure (RF-26), so before that there is none yet (no PENDING seed).
    idea = _publish(auth, mock, available=True)
    detail = auth("u_ana").get(f"/catalog/{idea['id']}").json()
    assert set(detail) == {
        "id", "fields", "origin", "createdAt", "publishedAt", "evaluation", "aiEvaluation",
    }
    assert detail["id"] == idea["id"]
    assert set(detail["fields"]) == set(IDEA_FIELDS)
    # The proponent is reduced to name/area; the contact is never exposed (RNF-7).
    assert detail["fields"]["proponent"] == {"name": "Ana Torres", "area": "Compras"}
    assert "contact" not in str(detail)
    assert detail["origin"] == "manual"
    assert detail["createdAt"] and detail["publishedAt"]
    # Nothing generated yet: the closure has not run.
    assert detail["evaluation"] is None
    assert detail["aiEvaluation"] is None


def test_detail_exposes_the_generated_evaluation_and_its_snapshot(auth, mock) -> None:
    idea = _publish(auth, mock, available=True, respond=lambda _p: evaluation_json())
    # The closure of the debate is what generates the AI evaluation (RF-26).
    debate = _close(auth, idea["id"])
    assert debate["closed"] is True
    detail = auth("u_ana").get(f"/catalog/{idea['id']}").json()
    evaluation = detail["evaluation"]
    assert evaluation["status"] == "GENERADA"
    assert [criterion["criterion"] for criterion in evaluation["criteria"]] == \
        list(EVALUATION_CRITERIA)
    assert evaluation["author"] == "Asistente (IA)"
    assert evaluation["createdAt"]
    assert evaluation["decidedBy"] is None and evaluation["decidedAt"] is None
    # The immutable snapshot mirrors the generated evaluation (RF-26).
    assert detail["aiEvaluation"] == evaluation


def test_detail_reflects_the_specialists_last_decision(auth, mock) -> None:
    idea = _publish(auth, mock, available=True, respond=lambda _p: evaluation_json())
    _close(auth, idea["id"])
    # The specialist accepts the AI evaluation (T-074); the detail is read-only
    # and simply reflects the final judgment (case 23).
    accepted = auth("u_solo").post(f"/validation/{idea['id']}/evaluation/accept").json()
    assert accepted["evaluation"]["status"] == "ACEPTADA"
    detail = auth("u_ana").get(f"/catalog/{idea['id']}").json()
    assert detail["evaluation"]["status"] == "ACEPTADA"
    assert detail["evaluation"]["decidedBy"] == "u_solo"
    assert detail["evaluation"]["decidedAt"]
    # The AI snapshot is kept untouched by the acceptance (RF-26, RNF-8).
    assert detail["aiEvaluation"]["status"] == "GENERADA"
    assert detail["aiEvaluation"]["decidedBy"] is None
