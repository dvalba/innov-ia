"""Company-context API tests (T-070, RF-21/RF-22, D13/D14, cases 24/25).

Covers the administrator-only company-context surface on
`/admin/contexto`: the `text/plain` template download, the online editing
(GET/PUT), the file upload that replaces the whole document, the 403 for a
non-admin session, and the case 24 (blank context is readable) / case 25
(blank or corrupt upload rejected, current document untouched).
"""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app import deps as deps_module
from app.main import app as main_app
from features.auth.infrastructure.token_store import TokenStore
from features.org.infrastructure.org_store import OrgStore
from shared.utils.password import hash_password
from tests.conftest import InMemoryDirectory, InMemoryStore

PLANTILLA_MINIMA = (
    "# Contexto de empresa — Innov-IA\n"
    "[PERFIL]\n"
    "name: Grupo Innov\n"
    "sector: Industria\n"
    "description: Automación industrial.\n"
    "mission: Reducir carga manual.\n"
    "strategicObjectives:\n"
    "- Digitalizar la cadena de suministro\n"
    "- Datos y analítica\n"
    "# Alineación estratégica, prioridades y líneas de innovación\n"
    "[GUÍA]\n"
    "Automatización, datos, sostenibilidad.\n"
    "[/GUÍA]\n"
)


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
def org_store() -> OrgStore:
    return OrgStore(InMemoryStore())


@pytest.fixture()
def auth(directory, org_store):
    """Issues bearer-authenticated clients against an in-memory org store."""
    token_store = TokenStore(InMemoryStore(), ttl_minutes=480, now_factory=datetime.now)
    main_app.dependency_overrides[deps_module.get_user_directory] = lambda: directory
    main_app.dependency_overrides[deps_module.get_token_store] = lambda: token_store
    main_app.dependency_overrides[deps_module.get_org_store] = lambda: org_store
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


def test_all_context_endpoints_require_admin_session(auth) -> None:
    proponente = auth("u_ana")
    assert proponente.get("/admin/contexto/plantilla").status_code == 403
    assert proponente.get("/admin/contexto").status_code == 403
    assert proponente.put(
        "/admin/contexto",
        json={"profile": {"name": "x"}, "guideText": ""},
    ).status_code == 403
    assert proponente.post(
        "/admin/contexto/subida", json={"content": PLANTILLA_MINIMA}
    ).status_code == 403

    # Without a session at all, the surface is 401.
    anon = auth(token=False)
    assert anon.get("/admin/contexto").status_code == 401
    assert anon.post(
        "/admin/contexto/subida", json={"content": PLANTILLA_MINIMA}
    ).status_code == 401


# -- template (RF-21) -----------------------------------------------------------


def test_template_is_plain_text_with_the_guide_sections(auth) -> None:
    response = auth().get("/admin/contexto/plantilla")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    body = response.text
    assert "[PERFIL]" in body
    assert "[GUÍA]" in body
    assert "[/GUÍA]" in body
    assert "Alineación estratégica" in body
    assert "strategicObjectives:" in body


# -- read blank context (case 24) ----------------------------------------------


def test_get_blank_context_returns_empty_document_case_24(auth, org_store) -> None:
    response = auth().get("/admin/contexto")
    assert response.status_code == 200
    body = response.json()
    assert body["profile"] == {
        "name": "", "sector": "", "description": "", "mission": "",
        "strategicObjectives": [],
    }
    assert body["guideText"] == ""
    assert org_store.get() is None  # nothing was persisted by a read


# -- online editing (PUT / GET, RF-21) -----------------------------------------


def test_put_context_persists_profile_and_guide(auth, org_store) -> None:
    response = auth().put("/admin/contexto", json={
        "profile": {
            "name": "  Grupo Innov  ",
            "sector": "Industria",
            "description": "Automatización industrial.",
            "mission": "Reducir carga manual.",
            "strategicObjectives": ["Digitalizar", "Datos", "Digitalizar"],
        },
        "guideText": " LÍNEAS: automatización, datos. ",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["profile"]["name"] == "Grupo Innov"
    assert body["profile"]["strategicObjectives"] == ["Digitalizar", "Datos"]
    assert body["guideText"] == "LÍNEAS: automatización, datos."
    assert body["updatedAt"]

    # The second GET reflects the persisted document.
    again = auth().get("/admin/contexto")
    assert again.status_code == 200
    assert again.json() == body


def test_put_context_with_blank_profile_is_400(auth, org_store) -> None:
    body = {"profile": {"name": "  ", "strategicObjectives": [""], }, "guideText": ""}
    response = auth().put("/admin/contexto", json=body)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "CONTEXT_INVALID"
    assert org_store.get() is None


def test_put_with_only_guide_text_is_400(auth, org_store) -> None:
    # A blank profile blocks the save even if the guide text has content.
    response = auth().put("/admin/contexto", json={
        "profile": {"name": "", "sector": "", "description": "", "mission": "",
                    "strategicObjectives": []},
        "guideText": "Solo guía, sin perfil.",
    })
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "CONTEXT_INVALID"


# -- file upload (RF-21, D14) ---------------------------------------------------


def test_upload_replaces_the_whole_document(auth, org_store) -> None:
    # Establish a prior document first.
    auth().put("/admin/contexto", json={
        "profile": {"name": "Antiguo", "sector": "Antiguo"}, "guideText": "vieja"})
    assert org_store.get()["profile"]["name"] == "Antiguo"

    response = auth().post("/admin/contexto/subida", json={"content": PLANTILLA_MINIMA})
    assert response.status_code == 200
    body = response.json()
    # The upload replaced the old document entirely.
    assert body["profile"]["name"] == "Grupo Innov"
    assert body["profile"]["strategicObjectives"] == [
        "Digitalizar la cadena de suministro", "Datos y analítica"]
    assert body["guideText"] == "Automatización, datos, sostenibilidad."
    assert body["updatedAt"]


def test_upload_empty_file_is_rejected_case_25(auth, org_store) -> None:
    auth().put("/admin/contexto", json={
        "profile": {"name": "Vigente"}, "guideText": "previa"})
    before = org_store.get()

    response = auth().post("/admin/contexto/subida", json={"content": "   \n  "})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "CONTEXT_UPLOAD_EMPTY"
    # The current context is untouched.
    assert org_store.get() == before


def test_upload_corrupt_file_is_rejected_case_25(auth, org_store) -> None:
    response = auth().post(
        "/admin/contexto/subida", json={"content": "sin marcado de secciones"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "CONTEXT_UPLOAD_INVALID"
    assert org_store.get() is None


def test_upload_with_blank_profile_is_rejected_case_25(auth, org_store) -> None:
    text = (
        "[PERFIL]\n"
        "name:\n"
        "sector:\n"
        "description:\n"
        "mission:\n"
        "strategicObjectives:\n"
        "[GUÍA]\n"
        "Solo guía.\n"
        "[/GUÍA]\n"
    )
    response = auth().post("/admin/contexto/subida", json={"content": text})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "CONTEXT_UPLOAD_INVALID"
    assert org_store.get() is None
