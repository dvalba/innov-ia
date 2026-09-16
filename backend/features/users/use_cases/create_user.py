"""Create user use case (T-015, RF-17).

The administrator creates a user; the system issues a temporary password that
is returned exactly once (the user must change it on the first access, flag
`shouldChangePassword`).
"""

import uuid

from features.users.domain.user import Usuario
from shared.contracts.user_directory import UserDirectory
from shared.exceptions.handlers import DomainError
from shared.utils.password import generate_temp_password, hash_password


def create_user(directory: UserDirectory, username: str, name: str, area: str, contact: str,
                roles: tuple[str, ...]) -> tuple[dict, str]:
    """Creates the account and returns `(public_payload, temporary_password)`.

    The temporary password is hashed for storage and returned once, in clear,
    so the panel can show it (RF-17).
    """
    username = username.strip()
    if not username:
        raise DomainError("USER_INVALID", "El nombre de usuario es obligatorio.", status_code=400)
    if directory.get_by_username(username) is not None:
        raise DomainError("USERNAME_TAKEN",
                          f"El nombre de usuario «{username}» ya está en uso.", status_code=409)
    temporary = generate_temp_password()
    user = Usuario(
        id="u_" + uuid.uuid4().hex[:8],
        username=username,
        name=name,
        area=area,
        contact=contact,
        roles=tuple(roles),
        active=True,
        passwordHash=hash_password(temporary),
        shouldChangePassword=True,
    )
    created = directory.create(user.to_payload() | {"passwordHash": user.passwordHash})
    return {key: value for key, value in created.items() if key != "passwordHash"}, temporary
