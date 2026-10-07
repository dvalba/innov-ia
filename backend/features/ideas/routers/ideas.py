"""Ideas feature router (T-023, RF-8, RF-9, RF-10, RF-19, plan §3.1).

Endpoints (plan §3.1), all guarded to an active `proponente` session
(401 without session, 403 for other roles):
  POST  /ideas                              -> 201 payload (422 RNF-5,
                              400 unknown origin)
  GET   /ideas/me                           -> 200 "Mis ideas" entries (RF-19)
  GET   /ideas/{id}                         -> 200 payload + versions
                                                (403 not the owner)
  PUT   /ideas/{id}                         -> 200 updated payload
                                                (409 generating / state)
  POST  /ideas/{id}/improve                 -> 200 pending request + notice
                                                (case 10, plan §4.5)
  POST  /ideas/{id}/versions/{vid}/decide   -> 200 payload after
                                                accept (`VIGENTE`) / discard
  POST  /ideas/{id}/request-publication     -> 200 payload in
                                                SOLICITANDO_PUBLICACION

Pydantic schemas live in this layer only (plan D8, Constitution §4.2). The
field schemas are deliberately permissive (empty/omitted allowed): the single
source of truth for the 7 fields (RNF-5) and the contact format (case 12) is
the `ideas` domain, so every 422 keeps the unified error contract (plan §3.6).
Business rules live in the use cases and `IdeaStore` (T-019..T-022).

Until T-024 wires the assistant client, `POST /{id}/improve` registers the
instruction as a pending request on the idea (`improvementRequest`) and
returns the case-10 notice; the queue processor converts it when the IA is
back (plan §4.5).
"""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.deps import IdeaLedgerDep, role_dependency
from features.auth.domain.session import Session
from features.ideas.infrastructure.idea_store import IdeaStore
from features.ideas.use_cases.create_idea import create_idea
from features.ideas.use_cases.edit_idea import edit_idea
from features.ideas.use_cases.list_my_ideas import list_my_ideas
from features.ideas.use_cases.request_publication import request_publication
from shared.contracts.idea_ledger import ORIGIN_MANUAL, STATE_EN_DESARROLLO
from shared.exceptions.handlers import DomainError

ideas_router = APIRouter(prefix="/ideas", tags=["ideas"])

ProponentDep = role_dependency("proponente")


class ProponentIn(BaseModel):
    name: str = ""
    area: str = ""
    contact: str = ""


class ResourcesIn(BaseModel):
    time: str = ""
    people: str = ""
    budget: str = ""


class IdeaFieldsIn(BaseModel):
    """The 7 idea fields (RNF-5); permissive here, validated by the domain."""

    title: str = ""
    proponent: ProponentIn | None = None
    description: str = ""
    problem: str = ""
    expectedBenefit: str = ""
    strategicAlignment: str = ""
    estimatedResources: ResourcesIn | None = None


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
    """Manual editing of the 7 fields (RF-9): owner + EN_DESARROLLO + no generation."""
    return edit_idea(ledger, idea_id=idea_id, owner_id=session.user_id,
                     fields=payload.model_dump())


@ideas_router.post("/{idea_id}/improve")
def improve_idea_endpoint(idea_id: str, payload: ImproveRequest, session: ProponentDep,
                          ledger: IdeaLedgerDep) -> dict:
    """Requests an AI improvement; without the IA (pre-T-024) the request is
    registered as pending on the idea and the case-10 notice is returned."""
    own = _require_idea(ledger, session, idea_id)
    if own["state"] != STATE_EN_DESARROLLO:
        raise DomainError(
            "IDEA_NOT_IMPROVABLE",
            f"La idea está en estado {own['state']}; solo se solicita mejora en "
            "EN_DESARROLLO (RF-8).",
            status_code=409,
        )
    request = {
        "instruction": payload.instruction,
        "requestedBy": session.user_id,
        "requestedAt": datetime.now().isoformat(),
    }
    ledger.update(idea_id, {"improvementRequest": request})
    return {
        "notice": "IA no disponible; tu solicitud quedará registrada.",
        "improvementRequest": request,
    }


@ideas_router.post("/{idea_id}/versions/{version_id}/decide")
def decide_version_endpoint(idea_id: str, version_id: str, payload: DecideRequest,
                            session: ProponentDep, ledger: IdeaLedgerDep) -> dict:
    """Accepts or discards a pending version (RF-8, RF-13, decision once).

    Accepting makes the version VIGENTE and moves the idea's
    `currentVersionId` to it; the idea keeps EN_DESARROLLO (decision #1).
    """
    _require_idea(ledger, session, idea_id)
    ledger.decide(idea_id=idea_id, version_id=version_id,
                  accept=payload.decision == "accept")
    return ledger.get(idea_id)


@ideas_router.post("/{idea_id}/request-publication")
def request_publication_endpoint(idea_id: str, session: ProponentDep,
                                 ledger: IdeaLedgerDep) -> dict:
    """Moves the idea to SOLICITANDO_PUBLICACION (RF-10, the only way)."""
    return request_publication(ledger, idea_id=idea_id, user_id=session.user_id)
