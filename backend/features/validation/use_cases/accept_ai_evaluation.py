"""Accept the AI evaluation as the final judgment (T-074, RF-26, plan §4.8).

Specialist decision endpoint (RF-26): `POST /validation/{ideaId}/evaluation/accept`
makes the AI's evaluation the final judgment. The guard is role-based
(especialista, 403 handled by the router) plus the domain guard — there must
be an AI evaluation to accept: without it (still `PENDING`, case 22) the
decision is a 409 (plan §4.8: `if idea.aiEvaluation == null: lanzar 409`).
The decision is idempotent-friendly in the "last action wins" sense (case 23):
accepting again after a replacement re-accepts the snapshot with a fresh
audit; both actions remain available in any order.
"""

from datetime import datetime

from features.validation.domain.evaluation_rules import (
    build_accepted_evaluation,
    require_ai_evaluation,
)
from shared.contracts.idea_ledger import IdeaLedger
from shared.exceptions.handlers import DomainError


def accept_ai_evaluation(
    ledger: IdeaLedger, *, idea_id: str, user_id: str, now: str | None = None
) -> dict:
    """Accepts the AI evaluation of `idea_id`; returns the updated payload.

    Guards: unknown idea -> 404; no `aiEvaluation` -> 409 (nothing to accept,
    case 22). The stored `evaluation` becomes a copy of the immutable
    `aiEvaluation` snapshot with `status=ACEPTADA` and the decision audit
    (`decidedBy` = the specialist id, `decidedAt` = now, RNF-8) — the
    judgment is always the last action (case 23).
    """
    payload = ledger.get(idea_id)
    if payload is None:
        raise DomainError("IDEA_NOT_FOUND", "La idea no existe.", status_code=404)
    snapshot = require_ai_evaluation(idea_id, payload.get("aiEvaluation"))
    evaluation = build_accepted_evaluation(snapshot, user_id, now or datetime.now().isoformat())
    return ledger.update(idea_id, {"evaluation": evaluation})
