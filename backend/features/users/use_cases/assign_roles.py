"""Assign / revoke roles use case (T-015, RF-17).

Applies the last-administrator rule before replacing a user's roles, so an
operation can never leave the system without an active administrator.
"""

from features.users.domain.role_rules import ensure_admin_remains
from features.users.domain.user import KNOWN_ROLES, Usuario
from shared.contracts.user_directory import UserDirectory
from shared.exceptions.handlers import DomainError


def assign_roles(directory: UserDirectory, user_id: str, roles: tuple[str, ...]) -> dict:
    """Replaces the user's roles (an empty tuple revokes all roles)."""
    for role in roles:
        if role not in KNOWN_ROLES:
            raise DomainError("UNKNOWN_ROLE", f"Rol desconocido: «{role}».", status_code=400)
    users = [Usuario.from_payload(payload) for payload in directory.list()]
    target = next((user for user in users if user.id == user_id), None)
    if target is None:
        raise DomainError("USER_NOT_FOUND", "El usuario no existe.", status_code=404)
    remains_admin = "admin" in roles
    ensure_admin_remains(users, user_id, remains_active_admin=remains_admin and target.active)
    updated = directory.update(user_id, {"roles": list(roles)})
    return updated


def revoke_roles(directory: UserDirectory, user_id: str, roles_to_remove: tuple[str, ...]) -> dict:
    """Removes the given roles keeping the rest (delegates to `assign_roles`)."""
    user = directory.get(user_id)
    if user is None:
        raise DomainError("USER_NOT_FOUND", "El usuario no existe.", status_code=404)
    keep = [role for role in user.get("roles", []) if role not in roles_to_remove]
    return assign_roles(directory, user_id, tuple(keep))
