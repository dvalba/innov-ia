"""Final-judgment rules of the idea evaluation (T-074, RF-26, case 23).

Pure domain module (Constitution §4.2): the final judgment is unique at all
times (RF-26) and is always the result of the specialist's LAST action (case
23) — accepting the AI evaluation and replacing it can alternate in any
order, each action producing a new judgment and its own audit trail (RNF-8).

The criterion contract (the 5 fixed criteria, the integer 1-10 scores, the
non-empty justifications) lives in `shared.contracts.evaluation`; this module
holds the decision-side rules: what may be accepted (`aiEvaluation` must
exist — 409, there is nothing to accept) and the state of the judgment each
action produces.
"""

from shared.contracts.evaluation import (
    EVALUATION_AI_AUTHOR,
    STATE_ACEPTADA,
    STATE_SUSTITUIDA,
    validate_evaluation_criteria,
)
from shared.exceptions.handlers import DomainError, ValidationFailed


class EvaluationError(DomainError):
    """There is nothing to decide about for this idea (409)."""


def validate_criteria_input(criteria) -> None:
    """422s with the problems when the criteria are not exactly the 5 fixed (RNF-5)."""
    problems = validate_evaluation_criteria(criteria)
    if problems:
        raise ValidationFailed(
            code="EVALUATION_INVALID",
            message="La evaluación debe contener exactamente los 5 criterios, con score 1-10 "
                    "y justificación no vacía.",
            details={"problems": problems},
        )


def build_accepted_evaluation(ai_evaluation: dict, user_id: str, now: str) -> dict:
    """The final judgment after accepting the AI evaluation (plan §4.8).

    Copy of the immutable `aiEvaluation` snapshot with `status=ACEPTADA` and
    the decision audit (`decidedBy` = the user id, `decidedAt` = now); the
    author is still "Asistente (IA)" (RF-26: the final judgment is the AI's,
    accepted by the specialist).
    """
    accepted = dict(ai_evaluation)
    accepted["status"] = STATE_ACEPTADA
    accepted["decidedBy"] = user_id
    accepted["decidedAt"] = now
    return accepted


def build_replacement_evaluation(criteria, user_id: str, user_name: str, now: str) -> dict:
    """The final judgment after the specialist replaces the evaluation (plan §4.8).

    The specialist's own 5 criteria with `status=SUSTITUIDA`, author = the
    specialist's name, and the decision audit (RNF-8). The AI's `aiEvaluation`
    snapshot is NOT touched: it stays visible on the detail view although the
    final judgment is the replacement (RF-26).
    """
    return {
        "status": STATE_SUSTITUIDA,
        "criteria": list(criteria),
        "author": user_name,
        "createdAt": now,
        "decidedBy": user_id,
        "decidedAt": now,
    }


def require_ai_evaluation(idea_id: str, ai_evaluation: dict | None) -> dict:
    """409s when there is no AI evaluation to accept (plan §4.8: nothing to accept)."""
    if ai_evaluation is None:
        raise EvaluationError(
            code="EVALUATION_MISSING",
            message=f"No existe evaluación de la IA para la idea «{idea_id}» que aceptar: "
                    "quedó pendiente o está siendo generada.",
        )
    return ai_evaluation


def is_ai_generated(evaluation: dict | None) -> bool:
    """`True` when the evaluation is the AI's own (author "Asistente (IA)")."""
    return isinstance(evaluation, dict) and evaluation.get("author") == EVALUATION_AI_AUTHOR
