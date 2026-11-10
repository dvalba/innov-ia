"""Final-decision use case (T-082, RF-27/RF-28/RF-29, plan §4.9).

The specialist closes the calibration stage of a published idea by taking a
final decision — `ACEPTADA`, `ARCHIVADA` or `RECHAZADA` (RF-27). The outcome
must match the band the average of the five criteria falls into, given the
administrator thresholds (RF-28); on a mismatch the error 409s `DECISION_MISMATCH`
exposing the `score` and the `band` the average actually maps to (case 27). The
decision is recorded on the idea (RNF-8) and the proponent is notified
(`IDEA_ACCEPTED`/`IDEA_ARCHIVED`/`IDEA_REJECTED`, the last with a
calibration-stage text, RF-18). The `validation` feature imports only `ideas`
(the emitter is injected by the caller, exactly like the G06 approve/reject
flow).
"""

from collections.abc import Callable, Mapping

from features.ideas.domain.idea import Idea
from features.ideas.domain.state_machine import transicionar
from features.ideas.infrastructure.idea_store import IdeaStore
from features.validation.domain.decision_rules import (
    OUTCOME_TO_ACTION,
    average,
    enforce_band_match,
    require_calibration_state,
    require_current_evaluation,
    require_reason,
    validate_outcome,
)
from features.validation.infrastructure.threshold_store import ThresholdStore
from features.validation.use_cases.admin_thresholds import get_thresholds
from shared.contracts.idea_ledger import STATE_VALIDADA_PUBLICA
from shared.contracts.roles import ROLE_SPECIALIST
from shared.exceptions.handlers import DomainError, Forbidden


def decide_final(
    ledger: IdeaStore,
    thresholds: ThresholdStore,
    *,
    idea_id: str,
    outcome: str,
    reason: str | None,
    user_id: str,
    user_name: str = "",
    user_roles: tuple[str, ...] = (),
    emit_notification: Callable[[Idea], None] | None = None,
) -> dict:
    """Decides `idea_id` in the calibration stage and returns the final payload.

    Guards (RF-27, RNF-7/RNF-9), in order:
      1. `outcome` not one of the three final states -> 422 `DECISION_INVALID`;
      2. unknown idea -> 404;
      3. the session lacks the specialist role -> 403;
      4. a state other than `VALIDADA_PUBLICA` -> 409 `DECISION_STATE_INVALID`;
      5. no current (non-`PENDING`) evaluation -> 409;
      6. `ARCHIVADA`/`RECHAZADA` without a reason -> 400 `DECISION_REASON_REQUIRED`;
      7. the outcome is not the average's band -> 409 `DECISION_MISMATCH`
         (carrying `score` and `band`, case 27).

    On success the idea transitions to the final state (compare-and-set,
    RNF-9), records the `decision` audit (RNF-8) and emits the notification.
    The response carries the final `state` and the `decision` itself.
    """
    validate_outcome(outcome)
    payload = ledger.get(idea_id)
    if payload is None:
        raise DomainError("IDEA_NOT_FOUND", "La idea no existe.", status_code=404)
    if ROLE_SPECIALIST not in tuple(user_roles):
        raise Forbidden(code="ROLE_NOT_ALLOWED",
                        message="Se requiere el rol especialista para decidir una idea (RF-27).")
    require_calibration_state(str(payload.get("state", "")))
    evaluation = require_current_evaluation(payload.get("evaluation"))
    require_reason(outcome, reason)
    score = average(evaluation)
    threshold: Mapping[str, object] = get_thresholds(thresholds)
    enforce_band_match(outcome, score, threshold)
    action = OUTCOME_TO_ACTION[outcome]
    idea = transicionar(Idea.from_payload(payload), action,
                        by_user=user_id, by_name=user_name,
                        reason=reason, score=score)
    updated = ledger.update_state(idea, expected_state=STATE_VALIDADA_PUBLICA)
    if emit_notification is not None:
        emit_notification(updated)
    return {"state": updated.state, "decision": updated.decision}
