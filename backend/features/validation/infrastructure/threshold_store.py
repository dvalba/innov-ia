"""Validation feature infrastructure: the calibration-thresholds store (T-081).

`ThresholdStore` persists the single administrator calibration-thresholds
record in a JSON file through `JsonStore` under the fixed key `"thresholds"`.
Writes are atomic (the store contract) and records are returned by value so the
in-memory copy stays insulated from storage mutations. There is no legacy shape
to migrate: the record is always `{rejectionThreshold, acceptanceThreshold,
updatedBy, updatedAt}` (the audit fields are stamped by the use case, RNF-8).
"""

import copy

from shared.utils.persistence import JsonStore

_THRESHOLDS_KEY = "thresholds"


class ThresholdStore:
    """JSON-backed single-record store for the calibration thresholds."""

    def __init__(self, store: JsonStore) -> None:
        self._store = store

    def _raw(self) -> dict | None:
        data = self._store.load()
        record = data.get(_THRESHOLDS_KEY)
        return copy.deepcopy(record) if isinstance(record, dict) else None

    def has(self) -> bool:
        """Whether a thresholds record has been saved yet."""
        return self._raw() is not None

    def get(self) -> dict | None:
        """The stored thresholds record, or None when the admin has not set any."""
        return self._raw()

    def put(self, record: dict) -> dict:
        """Atomically replaces the thresholds record and returns it."""
        self._store.update(lambda data: {**data, _THRESHOLDS_KEY: copy.deepcopy(record)})
        return self.get()  # type: ignore[return-value]
