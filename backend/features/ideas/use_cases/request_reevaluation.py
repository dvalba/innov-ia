"""Re-evaluation use case (T-082, RF-29, plan §4.9).

Sends an `ARCHIVADA` idea back to the calibration queue (`VALIDADA_PUBLICA`)
at the proponent's request (RF-29, case 30). The decision is cleared to `None`
while the closed debate and the AI evaluation are kept (spec: the idea re-enters
the calibration stage without re-opening the debate nor regenerating the
evaluation). The proponent is notified with `IDEA_REEVALUATED` (RF-18). Only
the owner may request it (RNF-7).
"""

from collections.abc import Callable

from features.ideas.domain.idea import Idea
from features.ideas.domain.state_machine import transicionar
from features.ideas.infrastructure.idea_store import IdeaStore
from shared.contracts.idea_ledger import STATE_ARCHIVADA
from shared.exceptions.handlers import DomainError


def request_reevaluation(
    ledger: IdeaStore, *, idea_id: str, owner_id: str,
    emit_notification: Callable[[Idea], None] | None = None,
) -> dict:
    """Re-evaluates `idea_id` and returns a short summary of the re-entry.

    Guards (RNF-7/RNF-9), in order:
      1. unknown idea -> 404;
      2. the requester is not the owner -> 403;
      3. a state other than `ARCHIVADA` -> 409 through the state machine.

    On success the idea transitions back to `VALIDADA_PUBLICA` (compare-and-set),
    the `decision` is cleared and `IDEA_REEVALUATED` is emitted to the owner.
    The response is a summary: `state`, the cleared `decision` and a `note`.
    """
    payload = ledger.get(idea_id)
    if payload is None:
        raise DomainError("IDEA_NOT_FOUND", "La idea no existe.", status_code=404)
    if payload["ownerId"] != owner_id:
        raise DomainError("NOT_IDEA_OWNER",
                          "Solo el propietario de la idea puede solicitar su reevaluación (RNF-7).",
                          status_code=403)
    idea = transicionar(Idea.from_payload(payload), "reevaluate", by_user=owner_id)
    updated = ledger.update_state(idea, expected_state=STATE_ARCHIVADA)
    if emit_notification is not None:
        emit_notification(updated)
    return {
        "state": updated.state,
        "decision": updated.decision,
        "note": "La idea vuelve a la cola de calibración conservando el debate cerrado y la evaluación de la IA.",
    }
