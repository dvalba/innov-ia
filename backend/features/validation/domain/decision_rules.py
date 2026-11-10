"""Final-decision rules of the calibration stage (T-080, RF-27/RF-28, plan §4.9).

Pure domain module (Constitution §4.2, no FastAPI): once an idea is published
and its evaluation is generated (`VALIDADA_PUBLICA`), the specialist takes a
final decision — `ACEPTADA`, `ARCHIVADA` or `RECHAZADA` (RF-27). The decision
is NOT free: it must match the **band** the average of the five criteria falls
into, given the administrator-configured thresholds (RF-28):

    average < rejectionThreshold            -> RECHAZADA
    rejectionThreshold <= average < acceptanceThreshold -> ARCHIVADA
    average >= acceptanceThreshold          -> ACEPTADA

The band is closed upward (case 26): an average exactly on a threshold falls
into the upper band. The average is the simple mean of the five criterion
scores, rounded to two decimals (plan §4.9 `PROMEDIO`/`BANDA`).

This module holds the decision-side rules as pure functions the `decide_final`
use case composes (plan §4.9 `DECIDIR_FINAL`):

  - the average and the band it maps to;
  - the outcome must be one of the three final states (422);
  - the idea must be in the calibration stage, `VALIDADA_PUBLICA` (409);
  - there must be a current, non-`PENDING` evaluation to decide on (409);
  - `ARCHIVADA`/`RECHAZADA` require a non-blank reason (400, case 28);
  - the chosen outcome must match the average band (409 `DECISION_MISMATCH`,
    exposing `score` and `band`, case 27 — the outcome is never forced).
"""

from collections.abc import Mapping
from typing import Any

from shared.contracts.evaluation import STATE_PENDING
from shared.contracts.idea_ledger import (
    STATE_ACEPTADA,
    STATE_ARCHIVADA,
    STATE_RECHAZADA,
    STATE_VALIDADA_PUBLICA,
)
from shared.exceptions.handlers import DomainError, ValidationFailed

# The three possible final outcomes of the calibration decision (RF-27); they
# are the target states of the `decide-*` transitions (plan §4.6).
OUTCOMES: tuple[str, ...] = (STATE_ACEPTADA, STATE_ARCHIVADA, STATE_RECHAZADA)

# The `decide-*` action of the state machine each outcome maps to (plan §4.6).
# The outcomes are Spanish states while the actions are English, so the mapping
# is explicit — never derived by name (decision T-082).
OUTCOME_TO_ACTION: dict[str, str] = {
    STATE_ACEPTADA: "decide-accepted",
    STATE_ARCHIVADA: "decide-archived",
    STATE_RECHAZADA: "decide-rejected",
}


class DecisionError(DomainError):
    """The idea is not in a situation that admits this final decision (409/400)."""


def average(evaluation: dict | None) -> float:
    """The simple average of the criterion scores, 2 decimals (RF-28, §4.9 PROMEDIO)."""
    criteria = (evaluation or {}).get("criteria") or []
    scores = [criterion["score"] for criterion in criteria]
    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 2)


def band(average_value: float, threshold: Mapping[str, Any]) -> str:
    """The band `average_value` falls into, given `threshold` (RF-28, case 26).

    The band is closed upward: an average exactly on a threshold falls into the
    upper band, so `rejectionThreshold <= avg < acceptanceThreshold` is
    `ARCHIVADA`, `avg >= acceptanceThreshold` is `ACEPTADA`, else `RECHAZADA`.
    """
    rejection = threshold["rejectionThreshold"]
    acceptance = threshold["acceptanceThreshold"]
    if average_value < rejection:
        return STATE_RECHAZADA
    if average_value >= acceptance:
        return STATE_ACEPTADA
    return STATE_ARCHIVADA


def validate_outcome(outcome: Any) -> None:
    """422s when the outcome is not one of the three final states (RF-27)."""
    if outcome not in OUTCOMES:
        raise ValidationFailed(
            code="DECISION_INVALID",
            message="El resultado de la decisión debe ser ACEPTADA, ARCHIVADA o RECHAZADA.",
            details={"problems": [f"«{outcome}» no es un resultado de calificación válido."]},
        )


def require_calibration_state(state: str) -> None:
    """409s when the idea is not in the calibration stage (RF-27, RNF-9).

    Only a published, calibrated idea (`VALIDADA_PUBLICA`) admits a final
    decision; every other state (final or not yet published) is rejected.
    """
    if state != STATE_VALIDADA_PUBLICA:
        raise DecisionError(
            code="DECISION_STATE_INVALID",
            message="Solo una idea en etapa de calificación (VALIDADA_PUBLICA) admite una "
                    "decisión final.",
        )


def require_current_evaluation(evaluation: dict | None) -> dict:
    """409s when there is no current evaluation to decide on (RF-27, case 22).

    The idea must carry an evaluation whose status is not `PENDING`; without it
    (the AI could not generate it and it is still pending) there is nothing to
    calibrate yet.
    """
    if evaluation is None:
        raise DecisionError(
            code="EVALUATION_MISSING",
            message="La idea aún no tiene una calificación vigente para decidir.",
        )
    if evaluation.get("status") == STATE_PENDING:
        raise DecisionError(
            code="EVALUATION_PENDING",
            message="La calificación de la idea está pendiente de generarse; no se puede "
                    "decidir aún.",
        )
    return evaluation


def require_reason(outcome: str, reason: str | None) -> None:
    """400s when an ARCHIVADA/RECHAZADA decision has no reason (RF-27, case 28)."""
    if outcome in (STATE_ARCHIVADA, STATE_RECHAZADA) and not (reason and reason.strip()):
        raise DecisionError(
            code="DECISION_REASON_REQUIRED",
            message="El resultado ARCHIVADA o RECHAZADA requiere un motivo.",
            status_code=400,
        )


def enforce_band_match(outcome: str, average_value: float, threshold: Mapping[str, Any]) -> str:
    """409s `DECISION_MISMATCH` when the outcome is not the average's band (case 27).

    The average's band is recomputed from the current thresholds and must equal
    the chosen outcome; on a mismatch the error carries `score` (the average)
    and `band` (the band the average maps to) so the client can show what the
    average actually implies. The outcome is never forced. Returns the band.
    """
    computed = band(average_value, threshold)
    if computed != outcome:
        raise DecisionError(
            code="DECISION_MISMATCH",
            message="El resultado elegido no coincide con la banda del promedio de la "
                    "calificación.",
            details={"score": average_value, "band": computed},
        )
    return computed
