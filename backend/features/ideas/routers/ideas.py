"""Ideas feature router (T-023/T-024, RF-8, RF-9, RF-10, RF-19, plan §3.1).

Endpoints (plan §3.1), all guarded to an active `proponente` session
(401 without session, 403 for other roles):
  POST  /ideas                              -> 201 payload (422 RNF-5,
                               400 unknown origin)
  GET   /ideas/me                           -> 200 "Mis ideas" entries (RF-19)
  GET   /ideas/{id}                         -> 200 payload + versions
                                                 (403 not the owner)
  PUT   /ideas/{id}                         -> 200 updated payload
                                                 (409 generating / state)
  POST  /ideas/{id}/improve                 -> 200 {version, idea} with the IA
                                                 (pending version, RF-8) or
                                                 {notice, improvementRequest}
                                                 without it (case 10, §4.5)
  POST  /ideas/{id}/versions/{vid}/decide   -> 200 payload after
                                                 accept (`VIGENTE`) / discard
  POST  /ideas/{id}/request-publication     -> 200 payload in
                                                  SOLICITANDO_PUBLICACION
  POST  /ideas/{id}/request-reevaluation    -> 200 {state, decision, note}
                                                  (ARCHIVADA back to the
                                                  calibration queue, RF-29)

Pydantic schemas live in this layer only (plan D8, Constitution §4.2). The
field schemas are deliberately permissive (empty/omitted allowed): the single
source of truth for the 6 fields (RNF-5) and the contact format (case 12) is
the `ideas` domain, so every 422 keeps the unified error contract (plan §3.6).
Business rules live in the use cases and `IdeaStore` (T-019..T-024): `improve`
is orchestrated there with the injected assistant client (G04).
"""

from typing import Literal

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from app.deps import (
    AssistantCheckDep,
    AssistantClientDep,
    IdeaLedgerDep,
    OrgStoreDep,
    ReevaluatedEmitterDep,
    RequestedEmitterDep,
    role_dependency,
)
from features.auth.domain.session import Session
from features.ideas.infrastructure.idea_store import IdeaStore
from features.ideas.use_cases.create_idea import create_idea
from features.ideas.use_cases.decide_version import decide_version
from features.ideas.use_cases.edit_idea import edit_idea
from features.ideas.use_cases.improve_idea import improve_idea
from features.ideas.use_cases.list_my_ideas import list_my_ideas
from features.ideas.use_cases.request_publication import request_publication
from features.ideas.use_cases.request_reevaluation import request_reevaluation
from features.org.use_cases.get_context import get_context
from shared.contracts.idea_ledger import ORIGIN_MANUAL
from shared.exceptions.handlers import DomainError

ideas_router = APIRouter(prefix="/ideas", tags=["ideas"])

ProponentDep = role_dependency("proponente")


class ProponentIn(BaseModel):
    name: str = ""
    area: str = ""
    contact: str = ""


class IdeaFieldsIn(BaseModel):
    """The 6 idea fields (RNF-5); permissive here, validated by the domain."""

    title: str = ""
    proponent: ProponentIn | None = None
    description: str = ""
    problem: str = ""
    expectedBenefit: str = ""
    strategicAlignment: str = ""


class CreateIdeaRequest(IdeaFieldsIn):
    origin: str = ORIGIN_MANUAL


class ImproveRequest(BaseModel):
    instruction: str


class DecideRequest(BaseModel):
    decision: Literal["accept", "discard"]


def _require_idea(ledger: IdeaStore, session: Session, idea_id: str) -> dict:
    """404 when the idea is unknown, 403 for a non-owner (RNF-7); else payload."""
    payload = ledger.get(idea_id)
    if payload is None:
        raise DomainError("IDEA_NOT_FOUND", "La idea no existe.", status_code=404)
    if payload["ownerId"] != session.user_id:
        raise DomainError(
            "NOT_IDEA_OWNER",
            "Solo el propietario de la idea puede verla o modificarla (RNF-7).",
            status_code=403,
        )
    return payload


@ideas_router.get("/me")
def my_ideas_endpoint(session: ProponentDep, ledger: IdeaLedgerDep) -> list[dict]:
    """Lists the proponent's own ideas (RF-19), newest first."""
    return list_my_ideas(ledger, owner_id=session.user_id)


@ideas_router.post("", status_code=201)
def create_idea_endpoint(payload: CreateIdeaRequest, session: ProponentDep,
                         ledger: IdeaLedgerDep) -> dict:
    """Registers a complete idea in EN_DESARROLLO (origen `asistida`/`manual`)."""
    return create_idea(ledger, owner_id=session.user_id, origin=payload.origin,
                       fields=payload.model_dump())


@ideas_router.get("/{idea_id}")
def idea_detail_endpoint(idea_id: str, session: ProponentDep,
                         ledger: IdeaLedgerDep) -> dict:
    """Returns the idea plus its versions, for the owner only (RF-19)."""
    payload = _require_idea(ledger, session, idea_id)
    return {"idea": payload, "versions": list(ledger.versions_of(idea_id))}


@ideas_router.put("/{idea_id}")
def edit_idea_endpoint(idea_id: str, payload: IdeaFieldsIn, session: ProponentDep,
                       ledger: IdeaLedgerDep) -> dict:
    """Manual editing of the 6 fields (RF-9): owner + EN_DESARROLLO + no generation."""
    return edit_idea(ledger, idea_id=idea_id, owner_id=session.user_id,
                     fields=payload.model_dump())


@ideas_router.post("/{idea_id}/improve")
def improve_idea_endpoint(idea_id: str, payload: ImproveRequest, session: ProponentDep,
                           ledger: IdeaLedgerDep, assistant: AssistantClientDep,
                           org_store: OrgStoreDep, background: BackgroundTasks,
                           check: AssistantCheckDep) -> dict:
    """Requests an AI improvement (RF-8): with the IA a pending version is
    registered for the proponent to accept/discard; without it the request is
    saved as pending on the idea with the case-10 notice (plan §4.5). The
    improvement is grounded on the current company-context document (RF-22)
    and the on-demand refinement verification (RF-11) runs in the background."""
    result = improve_idea(ledger, assistant, idea_id=idea_id, owner_id=session.user_id,
                           instruction=payload.instruction,
                           company_context=get_context(org_store))
    background.add_task(check)
    return result


@ideas_router.post("/{idea_id}/versions/{version_id}/decide")
def decide_version_endpoint(idea_id: str, version_id: str, payload: DecideRequest,
                             session: ProponentDep, ledger: IdeaLedgerDep) -> dict:
    """Accepts or discards a pending version (RF-8, RF-13, decision once).

    Accepting makes the version VIGENTE and moves the idea's
    `currentVersionId` to it; the idea keeps EN_DESARROLLO (decision #1).
    """
    return decide_version(ledger, idea_id=idea_id, version_id=version_id,
                          owner_id=session.user_id, accept=payload.decision == "accept")


@ideas_router.post("/{idea_id}/request-publication")
def request_publication_endpoint(idea_id: str, session: ProponentDep,
                                 ledger: IdeaLedgerDep, emit: RequestedEmitterDep) -> dict:
    """Moves the idea to SOLICITANDO_PUBLICACION (RF-10, the only way).

    Fans `IDEA_REQUESTED` out to every active specialist (RF-18); the emitter
    is injected from the composition root (G10/T-033).
    """
    return request_publication(ledger, idea_id=idea_id, user_id=session.user_id,
                                emit_notification=emit)


@ideas_router.post("/{idea_id}/request-reevaluation")
def request_reevaluation_endpoint(idea_id: str, session: ProponentDep,
                                  ledger: IdeaLedgerDep,
                                  emit: ReevaluatedEmitterDep) -> dict:
    """Requests the re-evaluation of an ARCHIVADA idea (RF-29, case 30).

    The idea goes back to the calibration queue (`VALIDADA_PUBLICA`) keeping
    the closed debate and the AI evaluation, and its previous final decision is
    cleared. Only the owner may request it (403 otherwise) and only an
    `ARCHIVADA` idea admits it (409, case 29: ACEPTADA/RECHAZADA are terminal).
    The owner is notified with `IDEA_REEVALUATED` (RF-18).
    """
    return request_reevaluation(ledger, idea_id=idea_id, owner_id=session.user_id,
                                emit_notification=emit)
