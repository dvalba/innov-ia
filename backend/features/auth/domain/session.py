"""Auth domain: active session and pure rules (T-010, RF-1).

`Session` is an opaque-token session with an explicit expiry (plan D3:
bearer tokens, no JWT). The domain stays pure: no FastAPI/Pydantic imports,
only `shared` utilities and exceptions.
"""

from dataclasses import dataclass
from datetime import datetime

from shared.exceptions.handlers import DomainError


@dataclass(frozen=True)
class Session:
    """An active work session (plan §2.1 `Session`).

    `token` is the opaque bearer, `user_id` links the session to the account,
    `expires_at` bounds the session and `roles` mirrors the account roles at
    issue time.
    """

    token: str
    user_id: str
    expires_at: datetime
    roles: tuple[str, ...]

    def __post_init__(self) -> None:
        # A session without an account or a token is malformed (RF-1: while
        # there is no active session, no access).
        if not self.token or not self.user_id:
            raise DomainError("SESSION_INVALID",
                              "La sesión requiere un token y un identificador de cuenta.",
                              status_code=400)

    def is_valid(self, now: datetime) -> bool:
        """True while the session has not expired (case 15: expired -> 401)."""
        return self.expires_at > now

    def has_role(self, role: str) -> bool:
        """True if the session holds the given role."""
        return role in self.roles

    def has_roles(self, roles: tuple[str, ...], all_of: bool = True) -> bool:
        """Checks `roles`: all of them by default, any of them when `all_of=False`."""
        if all_of:
            return all(role in self.roles for role in roles)
        return any(role in self.roles for role in roles)
