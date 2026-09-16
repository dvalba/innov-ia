"""Domain Session tests (T-010): validity, expiry and role rules.

Pure domain: no FastAPI/Pydantic imports are allowed here.
"""

from datetime import datetime, timedelta

from features.auth.domain.session import Session
from shared.exceptions.handlers import DomainError

NOW = datetime(2026, 9, 16, 12, 0, 0)


def _session(user_id: str = "u_1", expires_at: datetime = NOW + timedelta(hours=8),
             roles: tuple[str, ...] = ("proponente",)) -> Session:
    return Session(token="tok_1", user_id=user_id, expires_at=expires_at, roles=roles)


def test_valid_session_is_active() -> None:
    session = _session()
    assert session.is_valid(NOW) is True
    assert session.user_id == "u_1"


def test_expired_session_is_not_valid() -> None:
    session = _session(expires_at=NOW - timedelta(seconds=1))
    assert session.is_valid(NOW) is False


def test_session_expiring_exactly_now_is_invalid() -> None:
    session = _session(expires_at=NOW)
    # An expired session (expiry reached) ends access (RF-1).
    assert session.is_valid(NOW) is False


def test_role_combination() -> None:
    session = _session(roles=("especialista", "admin"))
    assert session.has_role("admin") is True
    assert session.has_role("especialista") is True
    assert session.has_role("proponente") is False


def test_role_check_requires_all_requested_roles_by_default() -> None:
    session = _session(roles=("proponente",))
    assert session.has_roles(("proponente", "admin")) is False
    assert session.has_roles(("proponente",)) is True


def test_role_check_any_of() -> None:
    session = _session(roles=("especialista", "admin"))
    assert session.has_roles(("especialista", "proponente"), all_of=False) is True


def test_session_requires_user_id_and_token() -> None:
    for user_id, token in (("", "t"), ("u", ""), ("", "")):
        try:
            Session(token=token, user_id=user_id, expires_at=NOW + timedelta(1), roles=())
            assert False, "expected DomainError"
        except DomainError:
            pass
