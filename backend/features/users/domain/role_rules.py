"""Last-administrator rule (T-014, RF-17).

The panel must never leave the system without at least one active
administrator (spec §5.6 / RF-17). This pure rule is applied by the
`assign_roles` and `toggle_active` use cases (T-015).
"""

from features.users.domain.user import Usuario
from shared.exceptions.handlers import DomainError

LAST_ADMIN_REQUIRED = "No se puede dejar el sistema sin al menos un administrador activo."


def ensure_admin_remains(users: list[Usuario], target_id: str,
                         remains_active_admin: bool = False) -> None:
    """Guards an operation that would strip the target of its admin access.

    `remains_active_admin` is True when the target is still an active admin
    after the operation. The guard only acts when the target currently is an
    active admin and the operation removes that status; then it requires at
    least one other active administrator.
    """
    target = next((user for user in users if user.id == target_id), None)
    if target is None or not (target.active and target.is_admin):
        return
    if remains_active_admin:
        return
    others_active = [user for user in users if user.id != target_id and user.active and user.is_admin]
    if not others_active:
        raise DomainError("LAST_ADMIN_REQUIRED", LAST_ADMIN_REQUIRED, status_code=409)
