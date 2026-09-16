"""Users use cases tests (T-015): create (temp password), roles, deactivate.

Covers RF-17 and case 16 (deactivation preserves account/history), and the
last-administrator rule (409).
"""

import pathlib

import pytest

from features.users.domain.role_rules import LAST_ADMIN_REQUIRED
from features.users.use_cases.assign_roles import assign_roles, revoke_roles
from features.users.use_cases.create_user import create_user
from features.users.use_cases.toggle_active import toggle_active
from features.users.infrastructure.user_store import UserStore
from shared.exceptions.handlers import DomainError
from shared.utils.password import verify_password
from shared.utils.persistence import JsonStore
from tests.conftest import InMemoryDirectory


def _admin(directory: InMemoryDirectory, user_id="u_a", username="admin") -> dict:
    return directory.create({
        "id": user_id,
        "username": username,
        "name": "Admin",
        "area": "",
        "contact": "",
        "roles": ["admin"],
        "active": True,
        "passwordHash": "innov$aa$bb",
        "shouldChangePassword": False,
    })


def test_create_user_returns_temp_password_once_and_marks_forced_change() -> None:
    directory = InMemoryDirectory()
    payload, temporary = create_user(directory, "ana", "Ana", "Produccion", "a@x.com",
                                     roles=("proponente",))
    assert temporary and len(temporary) >= 12
    assert "passwordHash" not in payload
    stored = directory.get_by_username("ana")
    assert "passwordHash" in stored
    assert verify_password(temporary, stored["passwordHash"]) is True
    assert stored["shouldChangePassword"] is True
    assert stored["active"] is True


def test_create_user_rejects_duplicate_username() -> None:
    directory = InMemoryDirectory()
    create_user(directory, "ana", "Ana", "", "", roles=())
    with pytest.raises(DomainError) as error:
        create_user(directory, "ana", "Otra", "", "", roles=())
    assert error.value.status_code == 409


def test_create_user_rejects_unknown_role() -> None:
    directory = InMemoryDirectory()
    with pytest.raises(DomainError) as error:
        create_user(directory, "ana", "Ana", "", "", roles=("no-existe",))
    assert error.value.status_code == 400


def test_assign_roles_replaces_and_validates() -> None:
    directory = InMemoryDirectory()
    created, _ = create_user(directory, "ana", "Ana", "", "", roles=("proponente",))
    updated = assign_roles(directory, created["id"], ("proponente", "especialista"))
    assert set(updated["roles"]) == {"proponente", "especialista"}
    with pytest.raises(DomainError) as error:
        assign_roles(directory, created["id"], ("no-existe",))
    assert error.value.status_code == 400


def test_revoking_roles_keeps_the_rest() -> None:
    directory = InMemoryDirectory()
    created, _ = create_user(directory, "ana", "Ana", "", "", roles=("proponente", "especialista"))
    updated = revoke_roles(directory, created["id"], ("proponente",))
    assert updated["roles"] == ["especialista"]


def test_deactivating_preserves_account_and_history() -> None:
    """Case 16: deactivation preserves the user record (account/history intact)."""
    directory = InMemoryDirectory()
    created, _ = create_user(directory, "ana", "Ana", "", "", roles=("proponente",))
    deactivated = toggle_active(directory, created["id"])
    stored = directory.get(created["id"])
    assert deactivated["active"] is False
    assert stored is not None, "the account record is preserved"
    assert stored["username"] == "ana"
    # Re-activating restores access.
    assert toggle_active(directory, created["id"])["active"] is True


def test_deactivating_last_admin_is_blocked_409() -> None:
    directory = InMemoryDirectory()
    admin = _admin(directory)
    create_user(directory, "ana", "Ana", "", "", roles=("proponente",))
    with pytest.raises(DomainError) as error:
        toggle_active(directory, admin["id"])
    assert error.value.status_code == 409
    assert LAST_ADMIN_REQUIRED in error.value.message


def test_revoking_last_admin_is_blocked_409() -> None:
    directory = InMemoryDirectory()
    admin = _admin(directory)
    with pytest.raises(DomainError) as error:
        assign_roles(directory, admin["id"], ("proponente",))
    assert error.value.status_code == 409


def test_with_second_active_admin_deactivating_one_is_allowed() -> None:
    directory = InMemoryDirectory()
    first = _admin(directory, "u_a1", "admin1")
    second = _admin(directory, "u_a2", "admin2")
    assert toggle_active(directory, first["id"])["active"] is False
    # admin2 is still active-admin.
    assert directory.get(second["id"])["active"] is True


def test_user_store_round_trip_over_file(tmp_path: pathlib.Path) -> None:
    store = UserStore(JsonStore(tmp_path / "data" / "users.json"))
    created = store.create({
        "id": "u_1", "username": "ana", "name": "Ana", "area": "",
        "contact": "a@x.com", "roles": ["proponente"], "active": True,
        "passwordHash": "innov$aa$bb", "shouldChangePassword": False,
    })
    assert created["username"] == "ana"
    assert store.get_by_username("ana")["id"] == "u_1"
    updated = store.update("u_1", {"active": False})
    assert updated["active"] is False
    assert store.get("u_1")["active"] is False
    assert len(store.list()) == 1
    # A fresh store over the same file sees the persisted state.
    reopened = UserStore(JsonStore(tmp_path / "data" / "users.json"))
    assert reopened.get("u_1")["username"] == "ana"
    assert reopened.get("u_1")["active"] is False
