"""Users domain tests (T-014): User entity and the "last administrator" rule."""

from features.users.domain.user import (
    ROLE_PROPOSER,
    ROLE_VALIDATOR,
    UnknownRole,
    Usuario,
    is_last_active_admin,
)
from shared.exceptions.handlers import DomainError


def _user(user_id="u_1", username="ana", roles=("proponente",), active=True) -> Usuario:
    return Usuario(
        id=user_id,
        username=username,
        name="Ana",
        area="Produccion",
        contact="ana@corp.com",
        roles=tuple(roles),
        active=active,
        passwordHash="innov$aa$bb",
        shouldChangePassword=False,
    )


def test_roles_are_validated_to_the_known_set() -> None:
    user = _user(roles=(ROLE_PROPOSER, ROLE_VALIDATOR))
    assert user.roles == ("proponente", "especialista")
    try:
        _user(roles=("proponente", "inventado"))
        raise AssertionError("expected DomainError")
    except DomainError as error:
        assert isinstance(error, UnknownRole)
        assert "desconocido" in error.message.lower()


def test_username_is_required() -> None:
    try:
        Usuario(id="u", username="  ", name="", area="", contact="",
                roles=(), active=True, passwordHash="x", shouldChangePassword=False)
        raise AssertionError("expected DomainError")
    except DomainError:
        pass


def test_last_active_admin_detection() -> None:
    users = [
        _user("u_1", "solo", roles=("admin",), active=True),
        _user("u_2", "otro", roles=("proponente",), active=True),
        _user("u_3", "caido", roles=("admin",), active=False),
    ]
    assert is_last_active_admin(users, "u_1") is True
    assert is_last_active_admin(users, "u_2") is False
    # A deactivated admin does not count: the active admin is the last one.
    users2 = [
        _user("u_1", "a", roles=("admin",), active=True),
        _user("u_2", "b", roles=("admin",), active=False),
    ]
    assert is_last_active_admin(users2, "u_1") is True


def test_last_admin_rule_blocks_removal_of_active_admin() -> None:
    """Revoking/disabling the only active admin raises the 409 DomainError rule."""
    from features.users.domain.role_rules import ensure_admin_remains

    users = [
        _user("u_1", "solo-admin", roles=("admin",), active=True),
        _user("u_2", "resto", roles=("proponente",), active=True),
    ]
    try:
        ensure_admin_remains(users, target_id="u_1")
        raise AssertionError("expected DomainError")
    except DomainError as error:
        assert error.status_code == 409
        assert "administrador" in error.message


def test_last_admin_rule_allows_removal_when_another_active_admin_exists() -> None:
    from features.users.domain.role_rules import ensure_admin_remains

    users = [
        _user("u_1", "a", roles=("admin",), active=True),
        _user("u_2", "b", roles=("admin",), active=True),
    ]
    # No exception means the operation is allowed.
    ensure_admin_remains(users, target_id="u_1")
    ensure_admin_remains(users, target_id="u_2")


def test_last_admin_rule_allows_losing_non_admin_roles() -> None:
    from features.users.domain.role_rules import ensure_admin_remains

    users = [_user("u_1", "a", roles=("proponente",), active=True)]
    ensure_admin_remains(users, target_id="u_1")
