"""Session token store and first-admin seed (T-011, plan D3 + decision #6).

Sessions are opaque bearer tokens persisted in a JSON-backed store (one
record per token, keyed by token). The seed creates the first administrator
at system initialization from environment-provided credentials, idempotently
(spec RF-17: "El primer administrador se define de forma manual en la
inicialización del sistema").
"""

import secrets
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from features.auth.domain.session import Session
from shared.contracts.user_directory import UserDirectory
from shared.utils.password import hash_password, verify_password
from shared.utils.persistence import JsonStore

ROLE_ADMIN = "admin"


@dataclass
class TokenStore:
    """Issues, resolves and revokes opaque session tokens.

    `now_factory` is injectable for deterministic expiry tests (case 15);
    the production wiring passes `datetime.now`.
    """

    store: JsonStore
    ttl_minutes: int = 480
    now_factory: Callable[[], datetime] = datetime.now

    def issue(self, user_id: str, roles: tuple[str, ...], now: datetime | None = None) -> Session:
        """Issues a new token for the account with the given roles."""
        moment = now if now is not None else self.now_factory()
        token = "innov-" + secrets.token_urlsafe(32)
        session = Session(token=token, user_id=user_id, expires_at=moment + timedelta(minutes=self.ttl_minutes),
                          roles=roles)
        self.store.update(lambda data: {**data, token: {
            "token": token,
            "user_id": user_id,
            "roles": list(roles),
            "expires_at": session.expires_at.isoformat(),
        }})
        return session

    def resolve(self, token: str, now: datetime | None = None) -> Session | None:
        """Returns the valid `Session` for the token, or `None` (unknown/expired)."""
        moment = now if now is not None else self.now_factory()
        record = self.store.load().get(token)
        if record is None:
            return None
        expires_at = datetime.fromisoformat(record["expires_at"])
        if expires_at <= moment:
            return None
        return Session(token=token, user_id=record["user_id"], expires_at=expires_at,
                       roles=tuple(record["roles"]))

    def revoke(self, token: str) -> None:
        """Revokes the token (logout). Safe if the token is unknown."""
        self.store.update(lambda data: {key: value for key, value in data.items() if key != token})


def seed_first_admin(directory: UserDirectory,
                     username: str,
                     password: str | None,
                     now: datetime | None = None) -> dict | None:
    """Creates the first administrator once (idempotent).

    Returns the created/existing admin payload, or `None` when no password
    was configured (initialization without credentials is a no-op).
    """
    existing = directory.get_by_username(username)
    if existing is not None:
        return existing
    if not password:
        return None
    moment = now if now is not None else datetime.now()
    return directory.create({
        "id": "u_" + uuid.uuid4().hex[:8],
        "username": username,
        "name": username,
        "area": "",
        "contact": "",
        "roles": [ROLE_ADMIN],
        "active": True,
        "passwordHash": hash_password(password),
        "shouldChangePassword": False,
        "createdAt": moment.isoformat(),
    })


def verify_credentials(user: dict | None, password: str) -> bool:
    """True when the user exists, is active and the password matches."""
    if user is None or not user.get("active", True):
        return False
    return verify_password(password, user.get("passwordHash", ""))
