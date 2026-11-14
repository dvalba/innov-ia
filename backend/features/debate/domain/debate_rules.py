"""Debate feature rules: the global debate-days configuration (T-089, RF-24, RNF-11).

Pure domain module (Constitution §4.2, no FastAPI). The duration of every
debate is a **global** administrator setting (`debateDays`) instead of a
per-idea deadline adjustment (v2.4, decision D23). This module owns the
default and the payload validation for saving a new value:

  - `debateDays` must be an integer in `1..90` (a JSON boolean is an `int`
    subclass: reject it).

A malformed payload is a 422 `DEBATE_DAYS_INVALID` (the shared
`ValidationFailed` always maps to 422) with the offending problems in
`details.problems`. The deadline of a debate is fixed at opening
(`publishedAt + debateDays` in force at that moment) and is never
recomputed: changing the configuration only affects the debates opened from
then on (no migration of the stored deadlines, v2.4).
"""

from datetime import datetime, timedelta
from typing import Any

from shared.exceptions.handlers import ValidationFailed

# The default debate duration in days (RF-24, v2.4): 30, used when the
# administrator has never saved their own.
DEBATE_DAYS_DEFAULT = 30
DEBATE_DAYS_MIN = 1
DEBATE_DAYS_MAX = 90

# The default record returned by `GET /admin/debate-days` when the
# administrator has never saved their own (plan §2.9, v2.4).
DEFAULT_DEBATE_DAYS: dict[str, int | None] = {
    "debateDays": DEBATE_DAYS_DEFAULT,
    "updatedBy": None,
    "updatedAt": None,
}


def _is_int(value: Any) -> bool:
    """True for real integers only (a JSON boolean is an `int` subclass: reject it)."""
    return isinstance(value, int) and not isinstance(value, bool)


def validate_debate_days(payload: Any) -> int:
    """Validates a debate-days payload and returns the normalized value (RF-24).

    422s `DEBATE_DAYS_INVALID` with the problems in `details.problems` when the
    value is not an integer in `1..90` (booleans, floats, strings and missing
    fields are all rejected).
    """
    data = payload if isinstance(payload, dict) else {}
    value = data.get("debateDays")
    problems: list[str] = []

    if not _is_int(value):
        problems.append("debateDays debe ser un entero entre 1 y 90.")
    elif not DEBATE_DAYS_MIN <= value <= DEBATE_DAYS_MAX:
        problems.append(f"debateDays={value} está fuera del rango 1-90.")

    if problems:
        raise ValidationFailed(
            code="DEBATE_DAYS_INVALID",
            message="Los días de debate no son válidos.",
            details={"problems": problems},
        )
    return value


def deadline_after_days(reference: str, days: int = DEBATE_DAYS_DEFAULT) -> str:
    """The debate deadline: `reference` (the publication date) + `days` (RF-24).

    The deadline is fixed at opening and is never recomputed afterwards (v2.4).
    """
    moment = datetime.fromisoformat(str(reference))
    return (moment + timedelta(days=days)).isoformat()
