"""Replace the idea's evaluation with the specialist's own (T-074, RF-26).

Specialist decision endpoint (RF-26): `POST /validation/{ideaId}/evaluation`
substitutes the current final judgment with the specialist's evaluation over
the same 5 fixed criteria (RNF-5: missing/unknown/duplicated criteria or a
score out of 1-10 are 422). There is NO state guard (case 23): the
replacement may apply before or after accepting the AI evaluation, and the
final judgment is always the result of the last action, audited with
who/when (RNF-8, RNF-11). The AI's `aiEvaluation` snapshot is never modified:
it stays visible on the detail view although the judgment is replaced (RF-26).
"""

from datetime import datetime

from features.validation.domain.evaluation_rules import (
    build_replacement_evaluation,
    validate_criteria_input,
)
from shared.contracts.idea_ledger import IdeaLedger
from shared.exceptions.handlers import DomainError


def replace_evaluation(
    ledger: IdeaLedger, *, idea_id: str, user_id: str, user_name: str, criteria,
    now: str | None = None
) -> dict:
    """Replaces the final judgment of `idea_id` with the specialist's criteria.

    Guards (plan §4.8 `SUSTITUIR_EVALUACION`, same order): criteria that are
    not exactly the 5 fixed ones -> 422 (via `ValidationFailed`,
    `details.problems` lists the problems); unknown idea -> 404. The stored
    `evaluation` carries `status=SUSTITUIDA`, author = the specialist's name,
    and the decision audit (RNF-8); the `aiEvaluation` snapshot keeps the AI's
    original judgment untouched.
    """
    validate_criteria_input(criteria)
    payload = ledger.get(idea_id)
    if payload is None:
        raise DomainError("IDEA_NOT_FOUND", "La idea no existe.", status_code=404)
    evaluation = build_replacement_evaluation(criteria, user_id, user_name,
                                              now or datetime.now().isoformat())
    return ledger.update(idea_id, {"evaluation": evaluation})
