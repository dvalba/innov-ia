"""Organization feature router (admin-managed organization profile, decision
D7 replacement).

Endpoints (all guarded to the administrator role, 403 otherwise):
  GET /admin/organizacion -> 200 the stored profile (or an empty one)
  PUT /admin/organizacion -> 200 the updated profile (400 when the name is
                              blank)

Pydantic schemas live in this layer only (plan D8, Constitution §4.2); the
business rules are enforced by the `org` use cases.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.deps import OrgStoreDep, role_dependency
from features.org.use_cases.get_org_profile import get_org_profile
from features.org.use_cases.update_org_profile import update_org_profile

org_router = APIRouter(prefix="/admin/organizacion", tags=["org"])

AdminDep = role_dependency("admin")


class OrgProfileRequest(BaseModel):
    name: str
    sector: str = ""
    description: str = ""
    mission: str = ""
    strategicObjectives: list[str] = []


@org_router.get("")
def read_org_profile(store: OrgStoreDep, session: AdminDep) -> dict:
    return get_org_profile(store)


@org_router.put("")
def write_org_profile(payload: OrgProfileRequest, store: OrgStoreDep,
                      session: AdminDep) -> dict:
    return update_org_profile(store, payload.model_dump())
