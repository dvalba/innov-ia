"""Toggle active use case (T-015, RF-17, case 16).

Deactivating a user removes their access but preserves the account, their
ideas and history (case 16). The last-administrator rule applies when the
user being deactivated is the only active administrator.
"""

from features.users.domain.role_rules import ensure_admin_remains
from features.users.domain.user import Usuario
from shared.contracts.user_directory import UserDirectory
from shared.exceptions.handlers import DomainError


def toggle_active(directory: UserDirectory, user_id: str) -> dict:
    """Flips `active` on the user, guarding the last-administrator rule."""
    user = directory.get(user_id)
    if user is None:
        raise DomainError("USER_NOT_FOUND", "El usuario no existe.", status_code=404)
    new_state = not user["active"]
    if new_state is False and user["active"]:
        # About to deactivate: ensure another active admin remains.
        users = [Usuario.from_payload(payload) for payload in directory.list()]
        ensure_admin_remains(users, user_id, remains_active_admin=False)
    return directory.update(user_id, {"active": new_state})
