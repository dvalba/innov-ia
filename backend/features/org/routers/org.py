"""Organization feature router: the admin-managed company context (RF-21, D13/D14).

Endpoints (all guarded to the administrator role, 403 otherwise):
  GET  /admin/contexto/plantilla -> 200 `text/plain` template with the guiding
                                     sections (RF-21)
  GET  /admin/contexto           -> 200 the current document (or a blank one,
                                     case 24)
  PUT  /admin/contexto           -> 200 the updated document (400 when the
                                     profile is left blank)
  POST /admin/contexto/subida    -> 200 the document replaced by the uploaded
                                    text file (400 when the text is blank or
                                    corrupt, case 25)

Pydantic schemas live in this layer only (plan D8, Constitution §4.2); the
business rules are enforced by the `org` use cases.
"""

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from app.deps import OrgStoreDep, role_dependency
from features.org.use_cases.context_template import get_context_template
from features.org.use_cases.get_context import get_context
from features.org.use_cases.update_context import update_context
from features.org.use_cases.upload_context import upload_context

org_router = APIRouter(prefix="/admin/contexto", tags=["org"])

AdminDep = role_dependency("admin")


class ProfileIn(BaseModel):
    name: str = ""
    sector: str = ""
    description: str = ""
    mission: str = ""
    strategicObjectives: list[str] = []


class ContextIn(BaseModel):
    profile: ProfileIn = ProfileIn()
    guideText: str = ""


class UploadIn(BaseModel):
    content: str


@org_router.get("/plantilla", response_class=PlainTextResponse)
def read_template(session: AdminDep) -> str:
    """The downloadable `text/plain` company-context template (RF-21)."""
    return get_context_template()


@org_router.get("")
def read_context(store: OrgStoreDep, session: AdminDep) -> dict:
    """The current company-context document, or a blank one (case 24)."""
    return get_context(store)


@org_router.put("")
def write_context(payload: ContextIn, store: OrgStoreDep, session: AdminDep) -> dict:
    """Online editing of the document (profile + guide text, RF-21)."""
    return update_context(store, payload.model_dump())


@org_router.post("/subida")
def upload(payload: UploadIn, store: OrgStoreDep, session: AdminDep) -> dict:
    """Upload of a text file that replaces the current document entirely
    (RF-21); the text arrives as a JSON `content` field (D14, no multipart)."""
    return upload_context(store, payload.content)
