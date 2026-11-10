"""Read and update the administrator calibration thresholds (T-081, RF-28).

`get_thresholds` returns the stored record or the default (case 31: 4/7 when
the administrator has never saved their own). `save_thresholds` validates the
payload (422 `THRESHOLDS_INVALID` on a malformed one), stamps the audit fields
(`updatedBy` = the administrator id, `updatedAt` = now, RNF-8) and persists the
new record. Saving never recalculates previously decided ideas (case 31): the
band is recomputed from the thresholds in force at decision time.
"""

from datetime import datetime

from features.validation.domain.threshold_rules import DEFAULT_THRESHOLD, validate_thresholds
from features.validation.infrastructure.threshold_store import ThresholdStore


def get_thresholds(store: ThresholdStore) -> dict:
    """The current thresholds, or the default (RF-28, case 31)."""
    stored = store.get()
    if stored is None:
        return dict(DEFAULT_THRESHOLD)
    return stored


def save_thresholds(
    store: ThresholdStore, payload: dict, *, user_id: str, now: str | None = None
) -> dict:
    """Validates the payload, persists it with the audit fields and returns it."""
    thresholds = validate_thresholds(payload)
    record = {
        "rejectionThreshold": thresholds["rejectionThreshold"],
        "acceptanceThreshold": thresholds["acceptanceThreshold"],
        "updatedBy": user_id,
        "updatedAt": now or datetime.now().isoformat(),
    }
    return store.put(record)
