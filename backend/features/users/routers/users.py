"""Users feature router (T-016, RF-17, RNF-7).

Endpoints (plan §3.1), all guarded to the administrator role (403 otherwise):
  GET   /users            -> 200 list of public user payloads
  POST  /users            -> 201 public payload + one-time temporary password
  PUT   /users/{id}/roles -> 200 updated payload (400 unknown role,
                             409 last-administrator rule)
  PATCH /users/{id}/active-> 200 toggled payload (409 last-administrator rule)

Pydantic schemas live in this layer only (plan D8, Constitution §4.2); the
business rules are enforced by the `users` use cases (T-015).
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.deps import UserDirectoryDep, role_dependency
from features.users.use_cases.assign_roles import assign_roles
from features.users.use_cases.create_user import create_user
from features.users.use_cases.toggle_active import toggle_active

users_router = APIRouter(prefix="/users", tags=["users"])

AdminDep = role_dependency("admin")


def _public(user: dict) -> dict:
    """Strips the password hash from a stored user payload."""
    return {key: value for key, value in user.items() if key != "passwordHash"}


class CreateUserRequest(BaseModel):
    username: str
    name: str = ""
    area: str = ""
    contact: str = ""
    roles: list[str] = []


class AssignRolesRequest(BaseModel):
    roles: list[str]


@users_router.get("")
def list_users(session: AdminDep, directory: UserDirectoryDep) -> list[dict]:
    return [_public(user) for user in directory.list()]


@users_router.post("", status_code=201)
def create_user_endpoint(payload: CreateUserRequest, session: AdminDep,
                         directory: UserDirectoryDep) -> dict:
    """Creates the account; the temporary password is returned exactly once (RF-17)."""
    public, temporary = create_user(directory, payload.username, payload.name,
                                    payload.area, payload.contact, tuple(payload.roles))
    return {"user": public, "temporaryPassword": temporary}


@users_router.put("/{user_id}/roles")
def assign_roles_endpoint(payload: AssignRolesRequest, user_id: str,
                          session: AdminDep, directory: UserDirectoryDep) -> dict:
    updated = assign_roles(directory, user_id, tuple(payload.roles))
    return _public(updated)


@users_router.patch("/{user_id}/active")
def toggle_active_endpoint(user_id: str, session: AdminDep, directory: UserDirectoryDep) -> dict:
    updated = toggle_active(directory, user_id)
    return _public(updated)
