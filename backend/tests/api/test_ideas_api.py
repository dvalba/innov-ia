"""Ideas router API tests (T-023/T-024, RF-8, RF-9, RF-10, RF-19).

Covers the proponent surface of `/ideas`: creation (201 / 422 RNF-5 / 400
origin), "Mis ideas" (owner-only summary), detail (403 not the owner, 404),
manual editing (409 generating RF-9, 409 state), the AI improvement
(T-024 orchestration: with the IA a `requestedBy=improvement` PENDIENTE
version is returned and manual editing blocks; without it the case-10
pending request + notice), the accept/discard decision (`currentVersionId`
moves on accept, EN_DESARROLLO kept, decision once) and the publication
request (409 on the second transition, RNF-9).

The `auth` fixture injects an unavailable assistant by default (deterministic
case-10, no network to the local Ollama); the with-IA tests re-override the
provider with an available mock whose reply is programmed in-place.

Versions for the `decide` tests are registered directly on the in-memory
ledger — the same shape the assistant client produces
(`requestedBy=improvement`, `PENDIENTE`); the router under test is the
decide endpoint itself.
"""

import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app import deps as deps_module
from app.main import app as main_app
from features.auth.infrastructure.token_store import TokenStore
from features.ideas.domain.validate import validar_campos
from features.ideas.infrastructure.idea_store import IdeaStore
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


def _register_version(ledger: IdeaStore, idea_id: str, title: str) -> dict:
    """Registers a PENDIENTE improvement version, as the assistant produces it."""
    fields = _fields(title=title)
    assert not validar_campos(fields), "test fixture must be complete"
    return ledger.add_version(idea_id=idea_id, fields=fields, requested_by="improvement")


def _improved_fields_json(**overrides: object) -> str:
    """A strict-JSON reply with the 7 complete fields (interpretable by the domain)."""
    return json.dumps(_fields(**overrides))


@pytest.fixture()
def directory() -> InMemoryDirectory:
    store = InMemoryDirectory()
    for user_id, name in (("u_ana", "Ana"), ("u_beto", "Beto")):
        store.create({
            "id": user_id,
            "username": user_id.removeprefix("u_"),
            "name": name,
            "area": "Produccion",
            "contact": f"{user_id.removeprefix('u_')}@corp.com",
            "roles": ["proponente"],
            "active": True,
            "passwordHash": hash_password("clave123"),
            "shouldChangePassword": False,
        })
    store.create({
        "id": "u_solo",
        "username": "solo",
        "name": "Solo",
        "area": "",
        "contact": "",
        "roles": ["especialista"],
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
    """Issues bearer-authenticated clients for a given user id."""
    token_store = TokenStore(InMemoryStore(), ttl_minutes=480, now_factory=datetime.now)
    main_app.dependency_overrides[deps_module.get_user_directory] = lambda: directory
    main_app.dependency_overrides[deps_module.get_token_store] = lambda: token_store
    main_app.dependency_overrides[deps_module.get_idea_ledger] = lambda: idea_ledger
    # Deterministic case-10 by default: no network to the local Ollama. The
    # with-IA tests re-override the provider with an available mock in-place.
    main_app.dependency_overrides[deps_module.get_assistant_client] = (
        lambda: OllamaMock(available=False)
    )
    # T-062: the /improve background check must not reach the real stores.
    main_app.dependency_overrides[deps_module.get_assistant_check] = (
        lambda: (lambda: {"status": "OK", "refined": 0, "failed": 0, "pending": 0})
    )

    def _client(user_id: str = "u_ana", token: bool = True) -> TestClient:
        if not token:
            return TestClient(main_app)
        roles = tuple(directory.get(user_id)["roles"])
        session = token_store.issue(user_id, roles, now=datetime.now())
        return TestClient(main_app, headers={"Authorization": f"Bearer {session.token}"})

    return _client


# -- access guards (RF-1, plan §3.1) -----------------------------------------------


def test_endpoints_require_session_401_and_proponent_role_403(auth) -> None:
    assert auth(token=False).get("/ideas/me").status_code == 401
    assert auth(token=False).post("/ideas", json=_fields()).status_code == 401
    assert auth("u_solo").get("/ideas/me").status_code == 403
    assert auth("u_solo").post("/ideas", json=_fields()).status_code == 403


# -- POST /ideas (RNF-5, case 12) ----------------------------------------------------


def test_create_idea_201_payload_in_en_desarrollo(auth) -> None:
    response = auth().post("/ideas", json={**_fields(), "origin": "manual"})
    assert response.status_code == 201
    body = response.json()
    assert body["origin"] == "manual"
    assert body["state"] == "EN_DESARROLLO"
    assert body["ownerId"] == "u_ana"
    assert body["id"].startswith("idea_")
    assert body["reviewedByAI"] is False
    assert body["currentVersionId"] is None
    assert body["improvementRequest"] is None


def test_create_idea_asistida_origin(auth) -> None:
    response = auth().post("/ideas", json={**_fields(), "origin": "asistida"})
    assert response.status_code == 201
    assert response.json()["origin"] == "asistida"


def test_create_idea_422_missing_fields(auth) -> None:
    missing = _fields()
    missing["description"] = ""
    response = auth().post("/ideas", json=missing)
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "IDEA_FIELDS_INVALID"
    assert "description" in error["details"]["fields"]


def test_create_idea_422_invalid_contact_case_12(auth) -> None:
    fields = _fields(proponent={"name": "Ana", "area": "Compras", "contact": "telefono??"})
    response = auth().post("/ideas", json=fields)
    assert response.status_code == 422
    assert "proponent" in response.json()["error"]["details"]["fields"]


def test_create_idea_400_unknown_origin(auth) -> None:
    response = auth().post("/ideas", json={**_fields(), "origin": "magnetica"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "IDEA_INVALID"


# -- GET /ideas/me (RF-19) -------------------------------------------------------------


def test_my_ideas_lists_only_the_owners_summary(auth) -> None:
    owned = auth().post("/ideas", json=_fields()).json()
    other = auth("u_beto").post("/ideas", json=_fields(title="Idea de Beto")).json()

    listing = auth().get("/ideas/me").json()
    assert [entry["id"] for entry in listing] == [owned["id"]]
    assert listing[0]["title"] == "Optimización de la aprobación de proveedores"
    assert set(listing[0]) == {"id", "title", "createdAt", "origin", "state"}
    assert auth("u_beto").get("/ideas/me").json()[0]["id"] == other["id"]


def test_my_ideas_empty_for_a_user_without_ideas(auth) -> None:
    assert auth().get("/ideas/me").json() == []


# -- GET /ideas/{id} (owner visibility, RNF-7) -------------------------------------------


def test_detail_200_returns_payload_and_versions(auth) -> None:
    idea = auth().post("/ideas", json=_fields()).json()
    response = auth().get(f"/ideas/{idea['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["idea"] == idea
    assert body["versions"] == []


def test_detail_403_for_a_non_owner(auth) -> None:
    idea = auth().post("/ideas", json=_fields()).json()
    response = auth("u_beto").get(f"/ideas/{idea['id']}")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "NOT_IDEA_OWNER"


def test_detail_404_for_an_unknown_idea(auth) -> None:
    assert auth().get("/ideas/idea_nadie").status_code == 404


# -- PUT /ideas/{id} (RF-9) -----------------------------------------------------------------


def test_edit_200_applies_the_seven_fields(auth) -> None:
    idea = auth().post("/ideas", json=_fields()).json()
    response = auth().put(f"/ideas/{idea['id']}", json=_fields(title="Título corregido"))
    assert response.status_code == 200
    assert response.json()["title"] == "Título corregido"


def test_edit_409_while_generation_is_in_flight(auth, idea_ledger) -> None:
    idea = auth().post("/ideas", json=_fields()).json()
    idea_ledger.add_version(idea_id=idea["id"], fields=_fields(title="Generando"),
                            requested_by="improvement", generating=True)

    response = auth().put(f"/ideas/{idea['id']}", json=_fields(title="Nunca"))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "GENERATION_IN_PROGRESS"


def test_edit_409_outside_en_desarrollo(auth) -> None:
    idea = auth().post("/ideas", json=_fields()).json()
    auth().post(f"/ideas/{idea['id']}/request-publication")
    response = auth().put(f"/ideas/{idea['id']}", json=_fields(title="Nunca"))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "IDEA_NOT_EDITABLE"


def test_edit_403_for_a_non_owner_and_404_unknown(auth) -> None:
    idea = auth().post("/ideas", json=_fields()).json()
    assert auth("u_beto").put(f"/ideas/{idea['id']}", json=_fields(title="X")).status_code == 403
    assert auth().put("/ideas/idea_nadie", json=_fields(title="X")).status_code == 404


def test_edit_422_incomplete_fields(auth) -> None:
    idea = auth().post("/ideas", json=_fields()).json()
    response = auth().put(f"/ideas/{idea['id']}", json=_fields(problem="   "))
    assert response.status_code == 422
    assert "problem" in response.json()["error"]["details"]["fields"]


# -- POST /ideas/{id}/improve (RF-8, case 10 — sin IA aún) ---------------------------------


def test_improve_registers_the_pending_request_with_the_case_10_notice(auth) -> None:
    idea = auth().post("/ideas", json=_fields()).json()
    response = auth().post(f"/ideas/{idea['id']}/improve",
                           json={"instruction": "Cuantifica el beneficio"})
    assert response.status_code == 200
    body = response.json()
    assert body["notice"] == "IA no disponible; tu solicitud quedará registrada."
    assert body["improvementRequest"]["instruction"] == "Cuantifica el beneficio"
    assert body["improvementRequest"]["requestedBy"] == "u_ana"
    assert body["improvementRequest"]["requestedAt"]

    stored = auth().get(f"/ideas/{idea['id']}").json()["idea"]
    assert stored["improvementRequest"]["instruction"] == "Cuantifica el beneficio"
    assert stored["reviewedByAI"] is False
    assert stored["state"] == "EN_DESARROLLO"


def test_improve_409_outside_en_desarrollo(auth) -> None:
    idea = auth().post("/ideas", json=_fields()).json()
    auth().post(f"/ideas/{idea['id']}/request-publication")
    response = auth().post(f"/ideas/{idea['id']}/improve", json={"instruction": "X"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "IDEA_NOT_IMPROVABLE"


def test_improve_403_non_owner_and_404_unknown(auth) -> None:
    idea = auth().post("/ideas", json=_fields()).json()
    assert auth("u_beto").post(f"/ideas/{idea['id']}/improve",
                               json={"instruction": "X"}).status_code == 403
    assert auth().post("/ideas/idea_nadie/improve",
                       json={"instruction": "X"}).status_code == 404


def test_improve_409_while_a_generation_is_in_flight(auth, idea_ledger) -> None:
    idea = auth().post("/ideas", json=_fields()).json()
    idea_ledger.add_version(idea_id=idea["id"], fields=_fields(title="Generando"),
                            requested_by="improvement", generating=True)

    response = auth().post(f"/ideas/{idea['id']}/improve", json={"instruction": "X"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "GENERATION_IN_PROGRESS"


# -- POST /ideas/{id}/improve (RF-8, con IA — T-024) ---------------------------------


def test_improve_with_ia_creates_a_pending_version_and_blocks_edits(auth) -> None:
    mock = OllamaMock(available=True)
    mock.respond = lambda prompt: _improved_fields_json(
        expectedBenefit="180 horas ahorradas al mes, cuantificadas.")
    main_app.dependency_overrides[deps_module.get_assistant_client] = lambda: mock

    idea = auth().post("/ideas", json=_fields()).json()
    response = auth().post(f"/ideas/{idea['id']}/improve",
                           json={"instruction": "Cuantifica el beneficio"})
    assert response.status_code == 200
    body = response.json()
    version = body["version"]
    assert version["requestedBy"] == "improvement"
    assert version["status"] == "PENDIENTE"
    assert version["fields"]["expectedBenefit"].startswith("180 horas")
    assert "Cuantifica el beneficio" in mock.prompts[0]

    stored = auth().get(f"/ideas/{idea['id']}").json()["idea"]
    assert stored["reviewedByAI"] is True
    assert stored["generando"] is True
    assert stored["title"] == idea["title"]  # the proposal is never auto-applied (RF-8)

    edit = auth().put(f"/ideas/{idea['id']}", json=_fields(title="Nunca"))
    assert edit.status_code == 409
    assert edit.json()["error"]["code"] == "GENERATION_IN_PROGRESS"


def test_improve_with_an_uninterpretable_reply_returns_the_case_10_notice(auth) -> None:
    mock = OllamaMock(available=True)
    mock.respond = lambda prompt: "respuesta sin JSON"
    main_app.dependency_overrides[deps_module.get_assistant_client] = lambda: mock

    idea = auth().post("/ideas", json=_fields()).json()
    response = auth().post(f"/ideas/{idea['id']}/improve", json={"instruction": "X"})
    assert response.status_code == 200
    body = response.json()
    assert body["notice"] == "IA no disponible; tu solicitud quedará registrada."
    assert body["improvementRequest"]["instruction"] == "X"

    detail = auth().get(f"/ideas/{idea['id']}").json()
    assert detail["idea"]["reviewedByAI"] is False
    assert detail["versions"] == []


# -- POST /ideas/{id}/versions/{vid}/decide (RF-8, RF-13, decision once) -------------------


def test_decide_accept_moves_current_version_id_and_keeps_en_desarrollo(auth, idea_ledger) -> None:
    idea = auth().post("/ideas", json=_fields()).json()
    version = _register_version(idea_ledger, idea["id"], "Versión aprobada")

    response = auth().post(f"/ideas/{idea['id']}/versions/{version['id']}/decide",
                           json={"decision": "accept"})
    assert response.status_code == 200
    body = response.json()
    assert body["currentVersionId"] == version["id"]
    assert body["title"] == "Versión aprobada"
    assert body["reviewedByAI"] is True
    assert body["state"] == "EN_DESARROLLO"  # decision #1: acceptance does not publish

    detail = auth().get(f"/ideas/{idea['id']}").json()
    assert detail["versions"][0]["status"] == "VIGENTE"


def test_decide_discard_keeps_the_current_version(auth, idea_ledger) -> None:
    idea = auth().post("/ideas", json=_fields()).json()
    version = _register_version(idea_ledger, idea["id"], "Candidata")

    response = auth().post(f"/ideas/{idea['id']}/versions/{version['id']}/decide",
                           json={"decision": "discard"})
    assert response.status_code == 200
    body = response.json()
    assert body["currentVersionId"] is None
    assert body["title"] == "Optimización de la aprobación de proveedores"
    assert body["reviewedByAI"] is False
    assert auth().get(f"/ideas/{idea['id']}").json()["versions"][0]["status"] == "DESCARTADA"


def test_decide_is_once_409_on_the_second_attempt(auth, idea_ledger) -> None:
    idea = auth().post("/ideas", json=_fields()).json()
    version = _register_version(idea_ledger, idea["id"], "Única")
    url = f"/ideas/{idea['id']}/versions/{version['id']}/decide"

    assert auth().post(url, json={"decision": "accept"}).status_code == 200
    again = auth().post(url, json={"decision": "discard"})
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "VERSION_ALREADY_DECIDED"


def test_decide_403_non_owner_404_unknown_version_and_idea(auth, idea_ledger) -> None:
    idea = auth().post("/ideas", json=_fields()).json()
    version = _register_version(idea_ledger, idea["id"], "X")
    url = f"/ideas/{idea['id']}/versions/{version['id']}/decide"

    assert auth("u_beto").post(url, json={"decision": "accept"}).status_code == 403
    missing_version = auth().post(f"/ideas/{idea['id']}/versions/ver_nope_99/decide",
                                  json={"decision": "accept"})
    assert missing_version.status_code == 404
    assert auth().post("/ideas/idea_nadie/versions/ver_nadie_01/decide",
                       json={"decision": "accept"}).status_code == 404


def test_decide_rejects_an_unknown_decision_value(auth, idea_ledger) -> None:
    idea = auth().post("/ideas", json=_fields()).json()
    version = _register_version(idea_ledger, idea["id"], "Y")
    response = auth().post(f"/ideas/{idea['id']}/versions/{version['id']}/decide",
                           json={"decision": "maybe"})
    assert response.status_code == 422


# -- POST /ideas/{id}/request-publication (RF-10, RNF-9) ----------------------------------


def test_request_publication_200_transitions_and_sets_request_date(auth) -> None:
    idea = auth().post("/ideas", json=_fields()).json()
    response = auth().post(f"/ideas/{idea['id']}/request-publication")
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "SOLICITANDO_PUBLICACION"
    assert body["requestDate"]
    assert body["publishedAt"] is None


def test_request_publication_twice_is_a_409_stale_transition(auth) -> None:
    idea = auth().post("/ideas", json=_fields()).json()
    assert auth().post(f"/ideas/{idea['id']}/request-publication").status_code == 200
    again = auth().post(f"/ideas/{idea['id']}/request-publication")
    assert again.status_code == 409
    stored = auth().get(f"/ideas/{idea['id']}").json()["idea"]
    assert stored["state"] == "SOLICITANDO_PUBLICACION"


def test_request_publication_403_non_owner_and_404_unknown(auth) -> None:
    idea = auth().post("/ideas", json=_fields()).json()
    assert auth("u_beto").post(f"/ideas/{idea['id']}/request-publication").status_code == 403
    assert auth().post("/ideas/idea_nadie/request-publication").status_code == 404
