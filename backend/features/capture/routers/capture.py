"""Capture feature router (T-031, RF-2..RF-7, plan §3.1).

Endpoints (plan §3.1), all guarded to an active `proponente` session
(401 without session, 403 for other roles):
  POST  /capture/start            -> 200 start-or-resume outcome (RF-2; RF-7
                                      manual signal when the assistant is
                                      unavailable, no conversation created)
  GET   /capture/assistant-status -> 200 {status: OK | UNAVAILABLE} (the
                                      availability probe only; the refinement
                                      queue belongs to /assistant/check, T-062)
  POST  /capture/messages         -> 200 next turn (chips, title suggestion,
                                      resolution summary) or 503 with
                                      {fallback: {capturedFields}} when the
                                      assistant falls mid conversation (RF-7
                                      case 2, RNF-10)
  POST  /capture/title            -> 200 outcome of a title action (RF-4:
                                      accept/another/manual)
  POST  /capture/finish           -> 201 the idea in EN_DESARROLLO origin
                                      asistida (RF-6), 422 when the confirmed
                                      summary is incomplete (RNF-5, case 12)
  POST  /capture/activate-manual  -> 200 the pre-filled contingency payload
                                      (RF-7 case 2, RNF-10)

Plan §3.1/§3.2 list five capture endpoints; `POST /capture/title` is the
surface the `title-suggestion` UI block (T-042, RF-4) calls: the three fixed
actions of the use case `suggest_title` (T-029), exposed without inventing
magic values in the message body.

When a body omits `conversationId`, the user's conversation is resolved as
the newest one (`RF-2`: there is at most one active per user); a proponent
without any conversation gets 404.

Pydantic schemas live in this layer only (plan D8, Constitution §4.2).
Business rules live in the use cases (T-027..T-030) and `ConversationStore`
(T-026).
"""

from collections.abc import Iterable
from typing import Literal

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from app.deps import (
    AssistantCheckDep,
    AssistantClientDep,
    ConversationStoreDep,
    IdeaLedgerDep,
    UserDirectoryDep,
    role_dependency,
)
from features.assistant.use_cases.check_availability import check_availability
from features.auth.domain.session import Session
from features.capture.infrastructure.conversation_store import ConversationStore
from features.capture.use_cases.activate_manual import activate_manual
from features.capture.use_cases.finish_capture import finish_capture
from features.capture.use_cases.process_message import process_message
from features.capture.use_cases.start_conversation import start_conversation
from features.capture.use_cases.suggest_title import suggest_title
from shared.exceptions.handlers import DomainError

capture_router = APIRouter(prefix="/capture", tags=["capture"])

ProponentDep = role_dependency("proponente")


class MessageRequest(BaseModel):
    """One capture message (plan §3.2); exactly one of `message` /
    `quickOptionSelected` must be present (the use case enforces it)."""

    conversationId: str | None = None
    message: str | None = None
    quickOptionSelected: str | None = None


class FinishRequest(BaseModel):
    """The confirmed editable summary (plan §3.2 `captured`)."""

    conversationId: str | None = None
    captured: dict = {}


class ActivateManualRequest(BaseModel):
    conversationId: str | None = None


class TitleRequest(BaseModel):
    """A title-suggestion action (RF-4); `manualText` is required for
    `manual` (stored unmodified by the use case)."""

    conversationId: str | None = None
    action: Literal["accept", "another", "manual"] = "manual"
    manualText: str | None = None


def _resolve_id(
    store: ConversationStore, session: Session, conversation_id: str | None
) -> str:
    """The explicit conversation id, or the user's newest one (404 if none)."""
    if conversation_id:
        return conversation_id
    conversations: Iterable[dict] = store.list_by_user(session.user_id)
    newest = max(conversations, key=lambda payload: payload.get("createdAt", ""), default=None)
    if newest is None:
        raise DomainError(
            "CONVERSATION_NOT_FOUND",
            "No existe una conversación de captura para este usuario.",
            status_code=404,
        )
    return newest["id"]


@capture_router.get("/assistant-status")
def assistant_status_endpoint(session: ProponentDep, assistant: AssistantClientDep) -> dict:
    """The assistant availability (RF-7): probes the client's ping without
    triggering anything (the refinement queue is /assistant/check, T-062)."""
    return check_availability(assistant)


@capture_router.post("/start")
def start_endpoint(session: ProponentDep, store: ConversationStoreDep,
                   assistant: AssistantClientDep, directory: UserDirectoryDep,
                   background: BackgroundTasks, check: AssistantCheckDep) -> dict:
    """Starts (or resumes) the capture conversation (RF-2, case 8); without the
    assistant it returns the manual-form signal (RF-7 case 1), creating
    nothing. The on-demand refinement verification (RF-11) runs in the
    background so the response is never blocked."""
    background.add_task(check)
    return start_conversation(store, assistant, directory, user_id=session.user_id)


@capture_router.post("/messages")
def messages_endpoint(payload: MessageRequest, session: ProponentDep,
                      store: ConversationStoreDep, assistant: AssistantClientDep) -> dict:
    """Processes one capture message (RF-3/RF-5) and returns the next turn;
    a mid-conversation assistant failure is the 503 with the captured fields
    as pre-fill (RF-7 case 2, RNF-10)."""
    conversation_id = _resolve_id(store, session, payload.conversationId)
    return process_message(
        store,
        assistant,
        conversation_id=conversation_id,
        user_id=session.user_id,
        message=payload.message,
        quick_option=payload.quickOptionSelected,
    )


@capture_router.post("/title")
def title_endpoint(payload: TitleRequest, session: ProponentDep,
                   store: ConversationStoreDep, assistant: AssistantClientDep) -> dict:
    """Applies a title action (RF-4): `accept` the proposed title, `another`
    distinct candidate, or `manual` text stored unmodified."""
    conversation_id = _resolve_id(store, session, payload.conversationId)
    return suggest_title(
        store,
        assistant,
        conversation_id=conversation_id,
        user_id=session.user_id,
        action=payload.action,
        manual_text=payload.manualText,
    )


@capture_router.post("/finish", status_code=201)
def finish_endpoint(payload: FinishRequest, session: ProponentDep,
                    store: ConversationStoreDep, ledger: IdeaLedgerDep) -> dict:
    """Confirms the summary and registers the idea (RF-6): 201
    {ideaId, state, origin}; 422 when the confirmed fields are incomplete
    (RNF-5, case 12) — the conversation stays in RESUMEN for a retry."""
    conversation_id = _resolve_id(store, session, payload.conversationId)
    idea = finish_capture(
        store, ledger,
        conversation_id=conversation_id,
        user_id=session.user_id,
        captured=payload.captured,
    )
    return {"ideaId": idea["id"], "state": idea["state"], "origin": idea["origin"]}


@capture_router.post("/activate-manual")
def activate_manual_endpoint(payload: ActivateManualRequest, session: ProponentDep,
                             store: ConversationStoreDep) -> dict:
    """Converts the capture into the pre-filled manual form (RF-7 case 2):
    marks the conversation CONTINGENCIA and returns its captured fields with
    no loss (RNF-10)."""
    conversation_id = _resolve_id(store, session, payload.conversationId)
    return activate_manual(
        store, conversation_id=conversation_id, user_id=session.user_id
    )
