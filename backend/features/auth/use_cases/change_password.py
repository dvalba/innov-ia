"""Forced password change on first access (T-012, RF-17).

The change is only allowed while the account is in the "must change" state
(first access with the temporary password); after it, the flag is cleared and
the new credential is stored as the hash.
"""

from dataclasses import dataclass

from features.auth.domain.session import Session
from shared.contracts.user_directory import UserDirectory
from shared.exceptions.handlers import AuthError, DomainError
from shared.utils.password import hash_password, verify_password

MIN_NEW_PASSWORD_LENGTH = 6


class PasswordNotForced(DomainError):
    """The account is not in the forced-change state (409)."""

    def __init__(self, message: str = "No es necesario cambiar la contraseña en este momento.") -> None:
        super().__init__("PASSWORD_CHANGE_NOT_REQUIRED", message, status_code=409)


class WrongCurrentPassword(AuthError):
    """The provided current password does not match (401, single message)."""

    def __init__(self) -> None:
        super().__init__(code="INVALID_CREDENTIALS", message="Las credenciales no son válidas.")


@dataclass(frozen=True)
class ChangePasswordCommand:
    user_id: str
    current: str
    new: str


def change_password(command: ChangePasswordCommand, session: Session, directory: UserDirectory) -> dict:
    """Verifies the current password, applies the new one and clears the flag.

    Only allowed while the account is in the forced-change state (first
    access); a non-forced change is a conflict (409). The change always
    applies to the session's own user.
    """
    if command.user_id != session.user_id:
        raise AuthError(code="SESSION_REQUIRED", message="Solo se permite cambiar la propia contraseña.")
    if len(command.new) < MIN_NEW_PASSWORD_LENGTH:
        raise DomainError("PASSWORD_TOO_SHORT",
                          "La nueva contraseña debe tener al menos 6 caracteres.", status_code=400)
    user = directory.get(command.user_id)
    if not user.get("shouldChangePassword", False):
        raise PasswordNotForced()
    if user is None or not verify_password(command.current, user.get("passwordHash", "")):
        raise WrongCurrentPassword()
    updated = directory.update(command.user_id, {
        "passwordHash": hash_password(command.new),
        "shouldChangePassword": False,
    })
    return {key: value for key, value in updated.items() if key != "passwordHash"}
