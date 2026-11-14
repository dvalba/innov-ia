"""Debate feature infrastructure: the global debate-days store (T-089, RF-24).

`DebateDaysStore` persists the single administrator debate-days record in a
JSON file through `JsonStore` under the fixed key `"debateDays"` (same
pattern as `ThresholdStore`). Writes are atomic (the store contract) and
records are returned by value so the in-memory copy stays insulated from
storage mutations. There is no legacy shape to migrate: the record is always
`{debateDays, updatedBy, updatedAt}` (the audit fields are stamped by the
use case, RNF-11).
"""

import copy

from shared.utils.persistence import JsonStore

_DEBATE_DAYS_KEY = "debateDays"


class DebateDaysStore:
    """JSON-backed single-record store for the global debate days."""

    def __init__(self, store: JsonStore) -> None:
        self._store = store

    def _raw(self) -> dict | None:
        data = self._store.load()
        record = data.get(_DEBATE_DAYS_KEY)
        return copy.deepcopy(record) if isinstance(record, dict) else None

    def has(self) -> bool:
        """Whether a debate-days record has been saved yet."""
        return self._raw() is not None

    def get(self) -> dict | None:
        """The stored debate-days record, or None when the admin has not saved any."""
        return self._raw()

    def put(self, record: dict) -> dict:
        """Atomically replaces the debate-days record and returns it."""
        self._store.update(lambda data: {**data, _DEBATE_DAYS_KEY: copy.deepcopy(record)})
        return self.get()  # type: ignore[return-value]
