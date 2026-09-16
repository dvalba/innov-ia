"""Users feature infrastructure (T-015, RF-17).

`UserStore` is the reference implementation of the `UserDirectory` shared
contract (plan §1.2 coupling note): it persists user payloads in a JSON file
through `JsonStore` and is the object wired to `get_user_directory` in
`app.deps`.
"""

import copy

from shared.exceptions.handlers import DomainError
from shared.utils.persistence import JsonStore


class UserStore:
    """JSON-backed user directory.

    Records are stored keyed by user id, mirroring `JsonStore` semantics
    (atomic writes). Payloads follow the documented camelCase contract.
    """

    def __init__(self, store: JsonStore) -> None:
        self._store = store

    def get(self, user_id: str) -> dict | None:
        user = self._store.load().get(user_id)
        return copy.deepcopy(user) if user is not None else None

    def get_by_username(self, username: str) -> dict | None:
        for user in self._store.load().values():
            if user.get("username") == username:
                return copy.deepcopy(user)
        return None

    def create(self, payload: dict) -> dict:
        user_id = payload["id"]
        if self.get(user_id) is not None:
            raise DomainError("USER_EXISTS", "Ya existe un usuario con ese identificador.",
                              status_code=409)
        self._store.update(lambda data: {**data, user_id: payload})
        return self.get(user_id)  # type: ignore[return-value]

    def update(self, user_id: str, changes: dict) -> dict:
        def apply(data: dict) -> dict:
            user = data.get(user_id)
            if user is None:
                raise DomainError("USER_NOT_FOUND", "El usuario no existe.", status_code=404)
            user = {**user, **changes}
            return {**data, user_id: user}

        self._store.update(apply)
        return self.get(user_id)  # type: ignore[return-value]

    def list(self) -> list[dict]:
        return [copy.deepcopy(user) for user in self._store.load().values()]
