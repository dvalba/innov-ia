"""Organization feature infrastructure (admin-managed organization profile).

`OrgStore` persists the single organization profile in a JSON file through
`JsonStore` under the fixed key `"profile"`. Writes are atomic (the store
contract) and payloads are deep-copied on read to keep the in-memory copy
insulated from storage mutations.
"""

import copy

from shared.utils.persistence import JsonStore

_PROFILE_KEY = "profile"


class OrgStore:
    """JSON-backed single-record store for the organization profile."""

    def __init__(self, store: JsonStore) -> None:
        self._store = store

    def get(self) -> dict | None:
        profile = self._store.load().get(_PROFILE_KEY)
        return copy.deepcopy(profile) if profile is not None else None

    def has(self) -> bool:
        return self._store.load().get(_PROFILE_KEY) is not None

    def put(self, payload: dict) -> dict:
        self._store.update(lambda data: {**data, _PROFILE_KEY: payload})
        return self.get()  # type: ignore[return-value]

    def seed(self, payload: dict) -> None:
        """Stores the profile when (and only when) none exists yet (idempotent)."""
        if self.has():
            return
        self.put(payload)
