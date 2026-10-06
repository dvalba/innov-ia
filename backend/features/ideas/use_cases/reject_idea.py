"""Reject-idea use case (T-021, RF-16, RF-18, RNF-8).

Sends an idea back from SOLICITANDO_PUBLICACION to EN_DESARROLLO with the
mandatory rejection comment (block without it, case 13) and the identity of
the issuer attached (`rejectionNote`, RNF-8). The `IDEA_REJECTED`
notification to the proponent is emitted through the emitter injected by the
caller (G10/T-033); `features.ideas` never imports the `notifications`
feature.
"""

from collections.abc import Callable

from features.ideas.domain.idea import Idea
from features.ideas.domain.state_machine import transicionar
from features.ideas.infrastructure.idea_store import IdeaStore
from shared.contracts.idea_ledger import STATE_SOLICITANDO_PUBLICACION
from shared.contracts.roles import ROLE_SPECIALIST
from shared.exceptions.handlers import DomainError, Forbidden


def reject_idea(ledger: IdeaStore, *, idea_id: str, user_id: str,
                user_name: str = "", user_roles: tuple[str, ...] = (),
                comment: str = "",
                emit_notification: Callable | None = None) -> dict:
    """Rejects `idea_id` with `comment` and returns the EN_DESARROLLO payload.

    Guards (RNF-7/RNF-9): unknown idea -> 404; the session lacks the
    specialist role -> 403 (RF-16); an empty or blank comment -> 400
    (`REJECTION_COMMENT_REQUIRED`, case 13, enforced by the state machine);
    a state other than SOLICITANDO_PUBLICACION -> 409. The comment and the
    issuer's identity (`by`/`byName`/`at`) are attached to the idea and
    survive the round-trip (RNF-8). After the compare-and-set transition,
    `emit_notification(updated)` is called once; the payload gives the
    caller the proponent (`ownerId`) for the `IDEA_REJECTED` event.
    """
    payload = ledger.get(idea_id)
    if payload is None:
        raise DomainError("IDEA_NOT_FOUND", "La idea no existe.", status_code=404)
    if ROLE_SPECIALIST not in tuple(user_roles):
        raise Forbidden(code="ROLE_NOT_ALLOWED",
                        message="Se requiere el rol especialista para rechazar una idea (RF-16).")
    idea = transicionar(Idea.from_payload(payload), "reject",
                        by_user=user_id, by_name=user_name, comment=comment)
    updated = ledger.update_state(idea, expected_state=STATE_SOLICITANDO_PUBLICACION)
    if emit_notification is not None:
        emit_notification(updated)
    return updated.to_payload()
