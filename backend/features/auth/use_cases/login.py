"""Login use case (T-012, RF-1).

Verifies credentials and issues a session. A failed attempt returns a single
message without revealing which datum is wrong (spec RF-1).
"""

from dataclasses import dataclass
from datetime import datetime

from features.auth.domain.session import Session
from features.auth.infrastructure.token_store import TokenStore, verify_credentials
from shared.contracts.user_directory import UserDirectory
from shared.exceptions.handlers import AuthError


@dataclass(frozen=True)
class LoginCommand:
    username: str
    password: str
    now: datetime


@dataclass(frozen=True)
class LoginResult:
    session: Session
    user: dict
    must_change_password: bool


def login(command: LoginCommand, directory: UserDirectory, tokens: TokenStore) -> LoginResult:
    """Validates the credentials, rejects deactivated accounts and issues a session."""
    user = directory.get_by_username(command.username)
    if not verify_credentials(user, command.password):
        raise AuthError(code="INVALID_CREDENTIALS",
                        message="Las credenciales no son válidas.")
    session = tokens.issue(user["id"], tuple(user.get("roles", [])), now=command.now)
    return LoginResult(session=session, user=_public_user(user),
                       must_change_password=bool(user.get("shouldChangePassword", False)))


def _public_user(user: dict) -> dict:
    public = {key: value for key, value in user.items() if key not in ("passwordHash",)}
    return public
