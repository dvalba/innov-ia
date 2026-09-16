"""Token store and first-admin seed tests (T-011, plan D3 + decision #6).

Session tokens are opaque bearer tokens persisted through `JsonStore`;
the seed creates the first administrator at initialization, idempotently.
"""

import uuid
from datetime import datetime, timedelta

from features.auth.domain.session import Session
from features.auth.infrastructure.token_store import TokenStore, seed_first_admin
from tests.conftest import InMemoryStore

NOW = datetime(2026, 9, 16, 12, 0, 0)


def _store(ttl_minutes: int = 480) -> TokenStore:
    return TokenStore(InMemoryStore(), ttl_minutes=ttl_minutes, now_factory=lambda: NOW)


class _Directory:
    """Minimal in-memory directory satisfying the UserDirectory contract."""

    def __init__(self) -> None:
        self.users: dict[str, dict] = {}

    def get(self, user_id: str) -> dict | None:
        return self.users.get(user_id)

    def get_by_username(self, username: str) -> dict | None:
        for user in self.users.values():
            if user["username"] == username:
                return user
        return None

    def create(self, payload: dict) -> dict:
        payload = dict(payload)
        payload.setdefault("id", f"u_{uuid.uuid4().hex[:8]}")
        self.users[payload["id"]] = payload
        return payload

    def update(self, user_id: str, changes: dict) -> dict:
        user = self.users[user_id]
        user.update(changes)
        return user

    def list(self) -> list[dict]:
        return list(self.users.values())


def test_issue_and_resolve_round_trip() -> None:
    store = _store()
    session = store.issue("u_1", ("proponente",), now=NOW)
    assert isinstance(session, Session)
    resolved = store.resolve(session.token, now=NOW)
    assert resolved is not None
    assert resolved.user_id == "u_1"
    assert resolved.roles == ("proponente",)


def test_issue_tokens_are_opaque_and_unique() -> None:
    store = _store()
    first = store.issue("u_1", (), now=NOW)
    second = store.issue("u_1", (), now=NOW)
    assert first.token != second.token


def test_resolve_unknown_token_returns_none() -> None:
    store = _store()
    assert store.resolve("no-existe", now=NOW) is None


def test_expired_token_is_not_resolved() -> None:
    store = _store()
    session = store.issue("u_1", ("admin",), now=NOW)
    future = NOW + timedelta(days=1)
    assert store.resolve(session.token, now=future) is None


def test_custom_ttl_is_applied() -> None:
    store = _store(ttl_minutes=30)
    session = store.issue("u_1", (), now=NOW)
    assert store.resolve(session.token, now=NOW + timedelta(minutes=29)) is not None
    assert store.resolve(session.token, now=NOW + timedelta(minutes=31)) is None


def test_revoke_deactivates_token() -> None:
    store = _store()
    session = store.issue("u_1", ("admin",), now=NOW)
    store.revoke(session.token)
    assert store.resolve(session.token, now=NOW) is None


def test_revoke_of_unknown_token_is_safe() -> None:
    store = _store()
    store.revoke("no-existe")  # must not raise


def test_seed_creates_first_admin() -> None:
    directory = _Directory()
    created = seed_first_admin(directory, "admin", "S3guraAdmin", now=NOW)
    assert created is not None
    admin = directory.get_by_username("admin")
    assert admin is not None
    assert admin["roles"] == ["admin"]
    assert admin["active"] is True
    assert admin["shouldChangePassword"] is False
    from shared.utils.password import verify_password

    assert verify_password("S3guraAdmin", admin["passwordHash"]) is True


def test_seed_is_idempotent() -> None:
    directory = _Directory()
    first = seed_first_admin(directory, "admin", "S3guraAdmin", now=NOW)
    second = seed_first_admin(directory, "admin", "OtraClave", now=NOW)
    assert len(directory.users) == 1
    assert first is not None
    assert second is not None
    assert first["id"] == second["id"]
    # Existing credentials are never overwritten by a repeated seed.
    from shared.utils.password import verify_password

    stored = directory.users[first["id"]]
    assert verify_password("S3guraAdmin", stored["passwordHash"]) is True
    assert verify_password("OtraClave", stored["passwordHash"]) is False


def test_seed_returns_none_when_no_credentials_configured() -> None:
    directory = _Directory()
    assert seed_first_admin(directory, "admin", None, now=NOW) is None
    assert not directory.users
