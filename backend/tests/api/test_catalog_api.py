"""Catalog router API tests (T-035, T-077, T-083, RF-20/RF-23/RF-27, RNF-7, plan §3.1).

Covers the public catalog by zones (RF-20/D16/D21): `GET /catalog/public` is
read-only for any active session (401 without one) and returns the four zones
(`en-proceso`, `aceptadas`, `rechazadas`, `archivadas`), each a projection of
one idea state, each with the compact item (`id`, `title`, `publishedAt`,
`description` — never the 6 fields, the origin or the proponent's contact).
`?zone=<zone>` returns a single zone and an unknown zone is a 422
(`CATALOG_ZONE_INVALID`). And the public detail (`GET /catalog/{ideaId}`,
RF-23/D21): the 6 fields (proponent reduced to name/area, never contact), the
origin and the registration/publication dates, the `state` and the `decision`
(`None` while the idea is still in calibration) plus the final `evaluation` and
the immutable `aiEvaluation` snapshot — only for the four catalog states, an
unknown id or an out-of-catalog state is a 404.
"""

import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app import deps as deps_module
from app.main import app as main_app
from features.auth.infrastructure.token_store import TokenStore
from features.ideas.infrastructure.idea_store import IdeaStore
from features.notifications.infrastructure.notification_store import NotificationStore
from features.org.infrastructure.org_store import OrgStore
from features.validation.infrastructure.threshold_store import ThresholdStore
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
def notify_store() -> NotificationStore:
    return NotificationStore(InMemoryStore())


@pytest.fixture()
def threshold_store() -> ThresholdStore:
    return ThresholdStore(InMemoryStore())


@pytest.fixture()
def org_store() -> OrgStore:
    return OrgStore(InMemoryStore())


@pytest.fixture()
def auth(directory, idea_ledger, mock, notify_store, threshold_store, org_store):
    token_store = TokenStore(InMemoryStore(), ttl_minutes=480, now_factory=datetime.now)
    main_app.dependency_overrides[deps_module.get_user_directory] = lambda: directory
    main_app.dependency_overrides[deps_module.get_token_store] = lambda: token_store
    main_app.dependency_overrides[deps_module.get_idea_ledger] = lambda: idea_ledger
    main_app.dependency_overrides[deps_module.get_assistant_client] = lambda: mock
    main_app.dependency_overrides[deps_module.get_notification_store] = lambda: notify_store
    main_app.dependency_overrides[deps_module.get_threshold_store] = lambda: threshold_store
    main_app.dependency_overrides[deps_module.get_org_store] = lambda: org_store

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


# -- content contract (RF-20, D16/D21, RNF-7) ------------------------------------------


def test_public_catalog_returns_the_four_zones_with_only_their_states(auth) -> None:
    # Approved -> in the en-proceso zone.
    approved = auth("u_ana").post("/ideas", json=_fields()).json()
    auth("u_ana").post(f"/ideas/{approved['id']}/request-publication")
    auth("u_solo").post(f"/validation/{approved['id']}/approve")
    # In development -> out of the catalog.
    auth("u_beto").post("/ideas", json=_fields(title="Otra, en desarrollo")).json()
    # Waiting for review -> out of the catalog (only the catalog states).
    solicitado = auth("u_beto").post("/ideas", json=_fields(title="Solicitando")).json()
    auth("u_beto").post(f"/ideas/{solicitado['id']}/request-publication")

    body = auth("u_solo").get("/catalog/public").json()
    assert set(body) == {"zones"}
    assert set(body["zones"]) == {"en-proceso", "aceptadas", "rechazadas", "archivadas"}
    assert [entry["id"] for entry in body["zones"]["en-proceso"]] == [approved["id"]]
    for zone in ("aceptadas", "rechazadas", "archivadas"):
        assert body["zones"][zone] == []


def test_catalog_compact_entry_holds_the_four_keys_without_contact(auth) -> None:
    approved = auth("u_ana").post("/ideas", json=_fields()).json()
    auth("u_ana").post(f"/ideas/{approved['id']}/request-publication")
    auth("u_solo").post(f"/validation/{approved['id']}/approve")

    entry = auth("u_solo").get("/catalog/public").json()["zones"]["en-proceso"][0]
    assert set(entry) == {"id", "title", "publishedAt", "description"}
    assert entry["id"] == approved["id"]
    assert entry["title"] == "Optimización de la aprobación de proveedores"
    assert entry["description"] == "Digitalizar la validación de proveedores."
    assert entry["publishedAt"]
    # The compact item carries no fields, no origin, no dates beyond the
    # publication, no proponent data: the contact is never exposed (RNF-7).
    for absent in ("fields", "origin", "createdAt", "proponent", "contact"):
        assert absent not in entry


def test_public_catalog_never_leaks_another_users_contact(auth) -> None:
    idea = auth("u_beto").post("/ideas", json=_fields(
        proponent={"name": "Beto", "area": "Logistica", "contact": "beto@corp.com"}
    )).json()
    auth("u_beto").post(f"/ideas/{idea['id']}/request-publication")
    auth("u_solo").post(f"/validation/{idea['id']}/approve")
    entry = auth("u_ana").get("/catalog/public").json()["zones"]["en-proceso"][0]
    assert entry["id"] == idea["id"]
    assert "beto@corp.com" not in str(entry)
    assert "contact" not in str(entry)


def test_single_zone_returns_only_that_zone(auth) -> None:
    approved = auth("u_ana").post("/ideas", json=_fields()).json()
    auth("u_ana").post(f"/ideas/{approved['id']}/request-publication")
    auth("u_solo").post(f"/validation/{approved['id']}/approve")

    body = auth("u_solo").get("/catalog/public", params={"zone": "en-proceso"}).json()
    assert set(body) == {"zone", "items"}
    assert body["zone"] == "en-proceso"
    assert [entry["id"] for entry in body["items"]] == [approved["id"]]
    for entry in body["items"]:
        assert set(entry) == {"id", "title", "publishedAt", "description"}

    empty = auth("u_solo").get("/catalog/public", params={"zone": "aceptadas"}).json()
    assert empty == {"zone": "aceptadas", "items": []}


def test_an_unknown_zone_is_a_422(auth) -> None:
    response = auth("u_solo").get("/catalog/public", params={"zone": "todas"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CATALOG_ZONE_INVALID"


# -- public detail (T-077, T-083, RF-23/D21) --------------------------------------------


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


def _decide(auth, idea_id: str, outcome: str, reason: str | None = None) -> dict:
    response = auth("u_solo").post(f"/validation/{idea_id}/decision",
                                   json={"outcome": outcome, "reason": reason})
    assert response.status_code == 200
    return response.json()


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


def test_detail_holds_the_fields_and_no_decision_before_the_debate_closes(auth, mock) -> None:
    # No AI runs at publication: the evaluation is generated at the debate's
    # closure (RF-26), so before that there is none yet (no PENDING seed).
    idea = _publish(auth, mock, available=True)
    detail = auth("u_ana").get(f"/catalog/{idea['id']}").json()
    assert set(detail) == {
        "id", "fields", "origin", "createdAt", "publishedAt", "state",
        "decision", "evaluation", "aiEvaluation",
    }
    assert detail["id"] == idea["id"]
    assert set(detail["fields"]) == set(IDEA_FIELDS)
    # The proponent is reduced to name/area; the contact is never exposed (RNF-7).
    assert detail["fields"]["proponent"] == {"name": "Ana Torres", "area": "Compras"}
    assert "contact" not in str(detail)
    assert detail["origin"] == "manual"
    assert detail["createdAt"] and detail["publishedAt"]
    # In the calibration stage: the en-proceso zone's state, no decision yet.
    assert detail["state"] == "VALIDADA_PUBLICA"
    assert detail["decision"] is None
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
    # The idea is still in calibration: the state and the decision are unchanged.
    assert detail["state"] == "VALIDADA_PUBLICA"
    assert detail["decision"] is None


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
    # Accepting the AI evaluation does not decide the idea: it stays in the
    # calibration stage (en-proceso) with no decision yet (T-083, D21).
    assert detail["state"] == "VALIDADA_PUBLICA"
    assert detail["decision"] is None
    # The AI snapshot is kept untouched by the acceptance (RF-26, RNF-8).
    assert detail["aiEvaluation"]["status"] == "GENERADA"
    assert detail["aiEvaluation"]["decidedBy"] is None


def test_detail_after_the_final_decision_shows_the_state_and_the_decision(auth, mock) -> None:
    idea = _publish(auth, mock, available=True, respond=lambda _p: evaluation_json())
    _close(auth, idea["id"])
    # Average 7.0 == acceptanceThreshold -> band ACEPTADA (case 26).
    decision = _decide(auth, idea["id"], "ACEPTADA")
    assert decision["state"] == "ACEPTADA"
    detail = auth("u_ana").get(f"/catalog/{idea['id']}").json()
    assert detail["state"] == "ACEPTADA"
    assert detail["decision"]["outcome"] == "ACEPTADA"
    assert detail["decision"]["decidedBy"] == "u_solo"
    assert detail["decision"]["decidedAt"]
    # The idea left the en-proceso zone for the aceptadas one (D21).
    zones = auth("u_solo").get("/catalog/public").json()["zones"]
    assert [entry["id"] for entry in zones["aceptadas"]] == [idea["id"]]
    assert [entry["id"] for entry in zones["en-proceso"]] == []
    # The evaluation judgment is kept in the detail of the final state.
    assert detail["evaluation"]["status"] == "GENERADA"
    assert detail["aiEvaluation"] is not None
