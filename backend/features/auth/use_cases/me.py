"""Me use case (T-012, RF-1).

Returns the data and roles of the currently authenticated user.
"""

from features.auth.domain.session import Session
from shared.contracts.user_directory import UserDirectory
from shared.exceptions.handlers import AuthError


def me(session: Session, directory: UserDirectory) -> dict:
    """Returns the public payload of the session user (without the hash).

    Raises `AuthError` if the user no longer exists in the directory.
    """
    user = directory.get(session.user_id)
    if user is None:
        raise AuthError(code="SESSION_REQUIRED", message="La sesión ya no está asociada a una cuenta.")
    return {key: value for key, value in user.items() if key != "password_hash"}
