"""Read and update the global debate days (T-089, RF-24, RNF-11).

`get_debate_days` returns the stored record or the default (30 when the
administrator has never saved their own). `save_debate_days` validates the
payload (422 `DEBATE_DAYS_INVALID` on a malformed one), stamps the audit
fields (`updatedBy` = the administrator id, `updatedAt` = now, RNF-11) and
persists the new record. Saving never touches the deadline of the debates
that are already open or closed (v2.4, decision D23): the configuration
only applies to the debates opened from then on.
"""

from datetime import datetime

from features.debate.domain.debate_rules import DEFAULT_DEBATE_DAYS, validate_debate_days
from features.debate.infrastructure.debate_days_store import DebateDaysStore


def get_debate_days(store: DebateDaysStore) -> dict:
    """The current debate-days record, or the default (RF-24, v2.4)."""
    stored = store.get()
    if stored is None:
        return dict(DEFAULT_DEBATE_DAYS)
    return stored


def save_debate_days(
    store: DebateDaysStore, payload: dict, *, user_id: str, now: str | None = None
) -> dict:
    """Validates the payload, persists it with the audit fields and returns it."""
    days = validate_debate_days(payload)
    record = {
        "debateDays": days,
        "updatedBy": user_id,
        "updatedAt": now or datetime.now().isoformat(),
    }
    return store.put(record)
