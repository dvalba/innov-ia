"""Auth use cases tests (T-012): login/logout/me + forced password change.

Covers RF-1 and the forced change on first access (RF-17). Failed
credential attempts never reveal which datum is wrong (single message).
"""

from datetime import datetime

from features.auth.domain.session import Session
from features.auth.infrastructure.token_store import TokenStore, verify_credentials
from features.auth.use_cases.change_password import (
    ChangePasswordCommand,
    PasswordNotForced,
    WrongCurrentPassword,
    change_password,
)
from features.auth.use_cases.login import LoginCommand, login
from features.auth.use_cases.logout import logout
from features.auth.use_cases.me import me
from shared.exceptions.handlers import AuthError, DomainError
from tests.conftest import InMemoryDirectory, InMemoryStore

NOW = datetime(2026, 9, 16, 12, 0, 0)


def _env(directory=None):
    from shared.utils.password import hash_password

    directory = directory or InMemoryDirectory()
    directory.create({
        "id": "u_1",
        "username": "ana",
        "name": "Ana",
        "area": "Producción",
        "contact": "ana@corp.com",
        "roles": ["proponente"],
        "active": True,
        "passwordHash": hash_password("clave123"),
        "shouldChangePassword": False,
    })
    directory.create({
        "id": "u_2",
        "username": "deshab",
        "name": "Deshab",
        "area": "",
        "contact": "",
        "roles": ["proponente"],
        "active": False,
        "passwordHash": hash_password("clave456"),
        "shouldChangePassword": False,
    })
    store = InMemoryStore()
    token_store = TokenStore(store, ttl_minutes=480, now_factory=lambda: NOW)
    return directory, token_store


def _session(directory, user_id="u_1", roles=("proponente",)) -> Session:
    from features.auth.domain.session import Session

    return Session(token="tok_" + user_id, user_id=user_id,
                   expires_at=datetime(2026, 9, 17, 12, 0, 0), roles=roles)


def test_login_valid_credentials_return_token_and_user() -> None:
    directory, token_store = _env()
    result = login(LoginCommand(username="ana", password="clave123", now=NOW), directory, token_store)
    assert result.session.user_id == "u_1"
    assert result.user["username"] == "ana"
    assert result.user["roles"] == ["proponente"]
    assert result.must_change_password is False
    resolved = token_store.resolve(result.session.token, now=NOW)
    assert resolved is not None and resolved.user_id == "u_1"


def test_login_invalid_credentials_single_message() -> None:
    directory, token_store = _env()
    try:
        login(LoginCommand(username="ana", password="mala", now=NOW), directory, token_store)
        raise AssertionError("expected AuthError")
    except AuthError as error:
        assert error.message == "Las credenciales no son válidas."
        assert error.code == "INVALID_CREDENTIALS"
    try:
        login(LoginCommand(username="alguien", password="mala", now=NOW), directory, token_store)
        raise AssertionError("expected AuthError")
    except AuthError as error:
        assert error.message == "Las credenciales no son válidas."


def test_login_deactivated_user_rejected_with_same_message() -> None:
    directory, token_store = _env()
    try:
        login(LoginCommand(username="deshab", password="clave456", now=NOW), directory, token_store)
        raise AssertionError("expected AuthError")
    except AuthError as error:
        assert error.code == "INVALID_CREDENTIALS"
        assert error.message == "Las credenciales no son válidas."


def test_login_sets_must_change_when_flagged() -> None:
    directory, token_store = _env()
    directory.update("u_1", {"shouldChangePassword": True})
    result = login(LoginCommand(username="ana", password="clave123", now=NOW), directory, token_store)
    assert result.must_change_password is True


def test_logout_revokes_session_token() -> None:
    directory, token_store = _env()
    session = token_store.issue("u_1", ("proponente",), now=NOW)
    logout(session.token, token_store)
    assert token_store.resolve(session.token, now=NOW) is None


def test_me_returns_user_and_roles() -> None:
    directory, _ = _env()
    directory.update("u_1", {"roles": ["proponente", "admin"]})
    session = _session(directory, "u_1", ("proponente", "admin"))
    result = me(session, directory)
    assert result["id"] == "u_1"
    assert result["name"] == "Ana"
    assert result["roles"] == ["proponente", "admin"]
    assert "passwordHash" not in result
    assert result["shouldChangePassword"] is False


def test_change_password_only_for_own_session() -> None:
    directory, _ = _env()
    directory.update("u_1", {"shouldChangePassword": True})
    session = _session(directory, "u_2")
    try:
        change_password(ChangePasswordCommand(user_id="u_1", current="clave123", new="nueva123"),
                        session, directory)
        raise AssertionError("expected AuthError")
    except AuthError:
        pass


def test_change_password_wrong_current_password() -> None:
    directory, _ = _env()
    directory.update("u_1", {"shouldChangePassword": True})
    session = _session(directory)
    try:
        change_password(ChangePasswordCommand(user_id=session.user_id, current="mala", new="nueva123"),
                        session, directory)
        raise AssertionError("expected WrongCurrentPassword")
    except WrongCurrentPassword:
        pass


def test_change_password_forced_and_clears_flag() -> None:
    directory, _ = _env()
    directory.update("u_1", {"shouldChangePassword": True})
    session = _session(directory)
    updated = change_password(
        ChangePasswordCommand(user_id=session.user_id, current="clave123", new="nueva123"),
        session, directory,
    )
    assert updated["shouldChangePassword"] is False
    user = directory.get("u_1")
    assert verify_credentials(user, "nueva123") is True
    assert verify_credentials(user, "clave123") is False


def test_change_password_rejects_when_not_forced() -> None:
    directory, _ = _env()
    session = _session(directory)
    try:
        change_password(ChangePasswordCommand(user_id=session.user_id, current="clave123", new="nueva123"),
                        session, directory)
        raise AssertionError("expected PasswordNotForced")
    except PasswordNotForced as error:
        assert error.status_code == 409


def test_change_password_rejects_short_new_password() -> None:
    directory, _ = _env()
    directory.update("u_1", {"shouldChangePassword": True})
    session = _session(directory)
    try:
        change_password(ChangePasswordCommand(user_id=session.user_id, current="clave123", new="12345"),
                        session, directory)
        raise AssertionError("expected DomainError")
    except DomainError:
        pass
