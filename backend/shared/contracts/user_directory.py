"""User directory contract shared between features (T-011).

Resolves the `auth` <-> `users` coupling (plan §1.2 coupling note): `auth`
must verify credentials, read roles and change passwords WITHOUT importing
`features.users`. The reference implementation is
`features.users.infrastructure.user_store` (T-015).

User payload keys (spec §2.1 `User` + RF-17 implementation fields):
`id`, `username`, `name`, `area`, `contact`, `roles` (list), `active`
(bool), `passwordHash`, `shouldChangePassword` (bool).
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class UserDirectory(Protocol):
    """User accounts shared between features (spec §2.1 `User`)."""

    def get(self, user_id: str) -> dict | None:
        """Returns the user payload by id, or `None` if it does not exist."""
        ...

    def get_by_username(self, username: str) -> dict | None:
        """Returns the user payload by username, or `None` if it does not exist."""
        ...

    def create(self, payload: dict) -> dict:
        """Creates a user from the payload and returns the stored record."""
        ...

    def update(self, user_id: str, changes: dict) -> dict:
        """Applies `changes` to the user and returns the updated user payload.

        Raises `DomainError` if the user does not exist.
        """
        ...

    def list(self) -> list[dict]:
        """Returns all user payloads (role rules need the full picture, RF-17)."""
        ...
