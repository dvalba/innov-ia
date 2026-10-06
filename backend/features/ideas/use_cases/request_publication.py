"""Request-publication use case (T-021, RF-10, RF-18, RNF-9).

Moves the idea to SOLICITANDO_PUBLICACION, the only way to reach that state
(plan §4.6), and fixes `requestDate`. It is the proponent's explicit action
(decision #1: accepting an AI version never publishes). The transition is
persisted with compare-and-set, so a request in flight loses 409 to the
first transition without leaving an inconsistent state (RNF-9, case 11).

The `IDEA_REQUESTED` notification to every specialist (RF-18) is emitted
through the emitter injected by the caller: `features.ideas` never imports
the `notifications` feature (G10/T-033 binds the real emission point, plan
§1.2 coupling note).
"""

from collections.abc import Callable

from features.ideas.domain.idea import Idea
from features.ideas.domain.state_machine import transicionar
from features.ideas.infrastructure.idea_store import IdeaStore
from shared.contracts.idea_ledger import STATE_EN_DESARROLLO
from shared.exceptions.handlers import DomainError


def request_publication(ledger: IdeaStore, *, idea_id: str, user_id: str,
                        user_name: str = "", emit_notification: Callable | None = None) -> dict:
    """Requests publication of `idea_id` by its proponent and returns the payload.

    Guards (RNF-7/RNF-9): unknown idea -> 404; not the proponent -> 403
    (only the proponent requests publication, RF-10); a state other than
    EN_DESARROLLO -> 409 through the state machine. After the compare-and-set
    transition, `emit_notification(specialist_id, idea_id, "IDEA_REQUESTED")`
    is called for every specialist target resolved by the caller (fanout,
    RF-18); the emissions happen after the state is committed.
    """
    payload = ledger.get(idea_id)
    if payload is None:
        raise DomainError("IDEA_NOT_FOUND", "La idea no existe.", status_code=404)
    if payload["ownerId"] != user_id:
        raise DomainError(
            "NOT_IDEA_OWNER",
            "Solo el proponente puede solicitar la publicación de su idea (RF-10).",
            status_code=403,
        )
    idea = transicionar(Idea.from_payload(payload), "request-publication",
                        by_user=user_id, by_name=user_name)
    updated = ledger.update_state(idea, expected_state=STATE_EN_DESARROLLO)
    if emit_notification is not None:
        emit_notification(updated)
    return updated.to_payload()
