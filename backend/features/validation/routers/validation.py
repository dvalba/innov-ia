"""Validation router (T-034, RF-14/RF-15/RF-16).

Specialist review surface, all guarded to the `especialista` role (403
otherwise):
  GET  /validation/queue          -> 200 the review queue (SOLICITANDO only,
                                      proponent without contact)
  POST /validation/{id}/approve   -> 200 payload (VALIDADA_PUBLICA, rastro +
                                      `IDEA_PUBLISHED`)
  POST /validation/{id}/reject    -> 200 payload (EN_DESARROLLO, comentario +
                                      `IDEA_REJECTED`; 400 sin comentario)

The approve/reject endpoints do NOT reimplement the transition: they reuse
`approve_idea`/`reject_idea` from the `ideas` feature (G06), preserving the
audit trail and the emission points. The emitted notifications are wired in
the composition root (`app/deps`) so this feature imports only `ideas`.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.deps import (
    IdeaLedgerDep,
    PublishedEmitterDep,
    RejectedEmitterDep,
    UserDirectoryDep,
    role_dependency,
)
from features.ideas.use_cases.approve_idea import approve_idea
from features.ideas.use_cases.reject_idea import reject_idea
from features.validation.use_cases.review_queue import review_queue
from shared.contracts.user_directory import UserDirectory

validation_router = APIRouter(prefix="/validation", tags=["validation"])

SpecialistDep = role_dependency("especialista")


class RejectRequest(BaseModel):
    comment: str = ""


def _specialist_name(directory: UserDirectory, session) -> str:
    user = directory.get(session.user_id)
    return user.get("name", "") if user is not None else ""


@validation_router.get("/queue")
def queue_endpoint(session: SpecialistDep, ledger: IdeaLedgerDep) -> list[dict]:
    """Lists the review queue (RF-14): ideas in SOLICITANDO_PUBLICACION."""
    return review_queue(ledger)


@validation_router.post("/{idea_id}/approve")
def approve_endpoint(idea_id: str, session: SpecialistDep, ledger: IdeaLedgerDep,
                     directory: UserDirectoryDep, emit: PublishedEmitterDep) -> dict:
    """Approves/publishes the idea, reusing `approve_idea` (G06) + `IDEA_PUBLISHED`."""
    return approve_idea(ledger, idea_id=idea_id, user_id=session.user_id,
                        user_name=_specialist_name(directory, session),
                        user_roles=session.roles, emit_notification=emit)


@validation_router.post("/{idea_id}/reject")
def reject_endpoint(idea_id: str, payload: RejectRequest, session: SpecialistDep,
                    ledger: IdeaLedgerDep, directory: UserDirectoryDep,
                    emit: RejectedEmitterDep) -> dict:
    """Rejects the idea (400 sin comentario, caso 13), reusing `reject_idea` (G06).

    The comment itself may be blank; `reject_idea` then raises the domain 400
    `REJECTION_COMMENT_REQUIRED` (case 13).
    """
    return reject_idea(ledger, idea_id=idea_id, user_id=session.user_id,
                       user_name=_specialist_name(directory, session),
                       user_roles=session.roles, comment=payload.comment,
                       emit_notification=emit)
