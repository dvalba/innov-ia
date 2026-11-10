"""Public-idea debate router (T-073, RF-24, RF-25, plan §3.1).

Endpoints, all guarded to an active session (401 without one) except the admin
deadline (403 for non-admins):
  GET  /catalog/{idea_id}/debate     -> 200 the debate (messages, deadline,
                                         closure, summary, trace); the first read
                                         at/after the deadline closes it once,
                                         generates the summary, generates the
                                         AI evaluation (RF-26) and retries a
                                         pending `@asistant` request (cases 18-21)
  POST /catalog/{idea_id}/debate     -> 201 the posted message (and the
                                        assistant's reply, when it is a valid
                                        `@asistant` invocation); 409 when the
                                        debate is closed, 400 when the link is
                                        dangling
  PUT  /admin/ideas/{idea_id}/debate/deadline -> 200 the adjusted deadline
                                        (admin only; audited; a future date
                                        re-opens a closed debate)

The AI pieces (the `@asistant` reply, the closure summary, the closure
evaluation) and the company context / idea fields are read at request time
and injected into the use cases (RF-22); a down assistant degrades the
operation gracefully (RNF-1, cases 20-22). Pydantic schemas live in this
layer only (plan D8).
"""

from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

from app.deps import (
    AssistantClientDep,
    CalibrationEmitterDep,
    DebateStoreDep,
    IdeaLedgerDep,
    OrgStoreDep,
    SessionDep,
    UserDirectoryDep,
    role_dependency,
)
from features.debate.use_cases.adjust_deadline import adjust_deadline
from features.debate.use_cases.assist import make_evaluate, make_summarize
from features.debate.use_cases.post_debate import post_debate_message
from features.debate.use_cases.read_debate import read_debate
from features.org.use_cases.get_context import get_context
from shared.contracts.user_directory import UserDirectory

debate_router = APIRouter(tags=["debate"])

AdminDep = role_dependency("admin")


class DebateMessageRequest(BaseModel):
    """One debate message (plan §3.2); `linkedMessageId` is the message the
    `@asistant` answer references (RF-25)."""

    text: str = ""
    linkedMessageId: str | None = None


class DebateDeadlineRequest(BaseModel):
    """The new deadline (ISO date) of the debate (RF-24, admin)."""

    deadline: str


def _author_name(directory: UserDirectory, session) -> str:
    user = directory.get(session.user_id)
    return user.get("name", "") if user is not None else ""


def _now() -> str:
    return datetime.now().isoformat()


@debate_router.get("/catalog/{idea_id}/debate")
def read_debate_endpoint(idea_id: str, session: SessionDep, store: DebateStoreDep,
                          ledger: IdeaLedgerDep, assistant: AssistantClientDep,
                          org_store: OrgStoreDep, calibration: CalibrationEmitterDep) -> dict:
    """Returns the debate of a published idea after the read-time rules run
    (closure at the deadline, summary, evaluation at closure, pending
    `@asistant` retry)."""
    idea_payload = ledger.get(idea_id) or {}
    context = get_context(org_store)
    return read_debate(
        store,
        idea_id=idea_id,
        summary=make_summarize(assistant, idea_payload, context),
        assistant=assistant,
        idea_fields=idea_payload,
        company_context=context,
        evaluate=make_evaluate(assistant, ledger, context, idea_id,
                               on_generated=calibration),
        now=_now(),
    )


@debate_router.post("/catalog/{idea_id}/debate", status_code=201)
def post_debate_endpoint(idea_id: str, payload: DebateMessageRequest, session: SessionDep,
                          store: DebateStoreDep, ledger: IdeaLedgerDep,
                          assistant: AssistantClientDep, org_store: OrgStoreDep,
                          directory: UserDirectoryDep, calibration: CalibrationEmitterDep) -> dict:
    """Posts a message in the open debate (201); a valid `@asistant` invocation
    also returns the assistant's reply; a closed debate is a 409 and a dangling
    link a 400 (cases 18-20)."""
    idea_payload = ledger.get(idea_id) or {}
    context = get_context(org_store)
    return post_debate_message(
        store,
        idea_id=idea_id,
        author_id=session.user_id,
        author_name=_author_name(directory, session),
        text=payload.text,
        linked_message_id=payload.linkedMessageId,
        summary=make_summarize(assistant, idea_payload, context),
        assistant=assistant,
        idea_fields=idea_payload,
        company_context=context,
        evaluate=make_evaluate(assistant, ledger, context, idea_id,
                               on_generated=calibration),
        now=_now(),
    )


@debate_router.put("/admin/ideas/{idea_id}/debate/deadline")
def deadline_endpoint(idea_id: str, payload: DebateDeadlineRequest, session: AdminDep,
                      store: DebateStoreDep, directory: UserDirectoryDep) -> dict:
    """Adjusts the deadline of the debate of an idea (admin only, audited); a
    future date re-opens a closed debate (RF-24)."""
    return adjust_deadline(
        store,
        idea_id=idea_id,
        new_deadline=payload.deadline,
        now=_now(),
        user_id=session.user_id,
        user_name=_author_name(directory, session),
        user_roles=session.roles,
    )
