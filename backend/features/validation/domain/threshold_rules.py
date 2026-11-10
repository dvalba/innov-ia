"""Administrator calibration-thresholds rules (T-081, RF-28, case 31).

Pure domain module (Constitution §4.2, no FastAPI). The final-decision band
(`decision_rules.band`) is a function of the administrator-configured
thresholds, which default to rejection at 4 and acceptance at 7 (RF-28, case
31) until the administrator saves their own. This module owns that default and
the payload validation for saving a new pair:

  - both `rejectionThreshold` and `acceptanceThreshold` must be integers in
    `1..10`;
  - `rejectionThreshold` must be strictly less than `acceptanceThreshold`.

A malformed payload is a 422 `THRESHOLDS_INVALID` (the shared `ValidationFailed`
always maps to 422) with the offending problems in `details.problems`. Saving a
new pair never recalculates any previously decided idea (case 31): the band is
always recomputed from the thresholds in force at decision time.
"""

from typing import Any

from shared.exceptions.handlers import ValidationFailed

# The default calibration thresholds (RF-28, case 31): rejection at 4,
# acceptance at 7. Used when the administrator has never saved their own.
DEFAULT_REJECTION_THRESHOLD = 4
DEFAULT_ACCEPTANCE_THRESHOLD = 7
DEFAULT_THRESHOLD: dict[str, int] = {
    "rejectionThreshold": DEFAULT_REJECTION_THRESHOLD,
    "acceptanceThreshold": DEFAULT_ACCEPTANCE_THRESHOLD,
}

_MIN_THRESHOLD = 1
_MAX_THRESHOLD = 10


def _is_int(value: Any) -> bool:
    """True for real integers only (a JSON boolean is an `int` subclass: reject it)."""
    return isinstance(value, int) and not isinstance(value, bool)


def validate_thresholds(payload: Any) -> dict[str, int]:
    """Validates a thresholds payload and returns the normalized pair (RF-28).

    422s `THRESHOLDS_INVALID` with the problems in `details.problems` when a
    value is not an integer in `1..10` or `rejectionThreshold >= acceptance`.
    """
    data = payload if isinstance(payload, dict) else {}
    rejection = data.get("rejectionThreshold")
    acceptance = data.get("acceptanceThreshold")
    problems: list[str] = []

    if not _is_int(rejection):
        problems.append("rejectionThreshold debe ser un entero entre 1 y 10.")
    elif not _MIN_THRESHOLD <= rejection <= _MAX_THRESHOLD:
        problems.append(f"rejectionThreshold={rejection} está fuera del rango 1-10.")
    if not _is_int(acceptance):
        problems.append("acceptanceThreshold debe ser un entero entre 1 y 10.")
    elif not _MIN_THRESHOLD <= acceptance <= _MAX_THRESHOLD:
        problems.append(f"acceptanceThreshold={acceptance} está fuera del rango 1-10.")
    if _is_int(rejection) and _is_int(acceptance) and rejection >= acceptance:
        problems.append("rejectionThreshold debe ser menor que acceptanceThreshold.")

    if problems:
        raise ValidationFailed(
            code="THRESHOLDS_INVALID",
            message="Los umbrales de calificación no son válidos.",
            details={"problems": problems},
        )
    return {"rejectionThreshold": rejection, "acceptanceThreshold": acceptance}
