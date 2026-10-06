"""Approve-idea use case (T-021, RF-15, RF-18, RNF-8).

Moves an idea in SOLICITANDO_PUBLICACION to VALIDADA_PUBLICA (terminal in
the MVP) and records the audit trail who/when, including the self-validation
allowed by decision #3 / case 9: the proponent who is also a specialist can
approve his own idea, and the trail (`publishedBy`/`publishedAt`) is
mandatory either way (RNF-8). The `IDEA_PUBLISHED` notification to the
proponent is emitted through the emitter injected by the caller (G10/T-033);
`features.ideas` never imports the `notifications` feature.
"""

from collections.abc import Callable

from features.ideas.domain.idea import Idea
from features.ideas.domain.state_machine import transicionar
from features.ideas.infrastructure.idea_store import IdeaStore
from shared.contracts.idea_ledger import STATE_SOLICITANDO_PUBLICACION
from shared.contracts.roles import ROLE_SPECIALIST
from shared.exceptions.handlers import DomainError, Forbidden


def approve_idea(ledger: IdeaStore, *, idea_id: str, user_id: str,
                 user_name: str = "", user_roles: tuple[str, ...] = (),
                 emit_notification: Callable | None = None) -> dict:
    """Approves `idea_id` and returns the VALIDADA_PUBLICA payload.

    Guards (RNF-7/RNF-9): unknown idea -> 404; the session lacks the
    specialist role -> 403 (RF-15); a state other than
    SOLICITANDO_PUBLICACION -> 409 through the state machine. The
    self-validation (case 9) passes the role guard naturally: the approver
    is an active specialist, and the trail stays mandatory (RNF-8).
    `user_id`/now are recorded as `publishedBy`/`publishedAt`. After the
    compare-and-set transition, `emit_notification(updated)` is called once;
    the payload gives the caller the proponent (`ownerId`) for the
    `IDEA_PUBLISHED` event.
    """
    payload = ledger.get(idea_id)
    if payload is None:
        raise DomainError("IDEA_NOT_FOUND", "La idea no existe.", status_code=404)
    if ROLE_SPECIALIST not in tuple(user_roles):
        raise Forbidden(code="ROLE_NOT_ALLOWED",
                        message="Se requiere el rol especialista para validar una idea (RF-15).")
    idea = transicionar(Idea.from_payload(payload), "approve",
                        by_user=user_id, by_name=user_name)
    updated = ledger.update_state(idea, expected_state=STATE_SOLICITANDO_PUBLICACION)
    if emit_notification is not None:
        emit_notification(updated)
    return updated.to_payload()
