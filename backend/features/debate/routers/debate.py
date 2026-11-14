"""Public-idea debate router (T-073, RF-24, RF-25, plan §3.1).

Endpoints, all guarded to an active session (401 without one):
  GET  /catalog/{idea_id}/debate     -> 200 the debate (messages, deadline,
                                         closure, summary, trace); the first read
                                         at/after the deadline closes it once,
                                         generates the summary, generates the
                                         AI evaluation (RF-26) and retries a
                                         pending `@asistant` request (cases 18-21)
   POST /catalog/{idea_id}/debate     -> 201 the posted message (and the
                                         assistant's reply, when the text is a
                                         valid `@asistant` invocation — the
                                         token plus a non-blank request, the
                                         linked message being optional context,
                                         v2.5); 409 when the debate is closed,
                                         400 when the provided link is dangling

The deadline of a debate is fixed at opening from the global debate-days
setting (RF-24, v2.4, T-089) and can no longer be adjusted per idea: the
`PUT /admin/ideas/{idea_id}/debate/deadline` endpoint was removed.

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
)
from features.debate.use_cases.assist import make_evaluate, make_summarize
from features.debate.use_cases.post_debate import post_debate_message
from features.debate.use_cases.read_debate import read_debate
from features.org.use_cases.get_context import get_context
from shared.contracts.user_directory import UserDirectory

debate_router = APIRouter(tags=["debate"])


class DebateMessageRequest(BaseModel):
    """One debate message (plan §3.2); `linkedMessageId` is the optional context
    message of an `@asistant` invocation (RF-25, v2.5) or the reply reference of
    a plain message."""

    text: str = ""
    linkedMessageId: str | None = None


def _author_name(directory: UserDirectory, session) -> str:
    user = directory.get(session.user_id)
    if user is None:
        return ""
    # `name` is optional on a user (it can be created blank); fall back to the
    # `username` (always present) so a bubble is never left without an author,
    # mirroring the layout's `name || username` convention.
    return str(user.get("name") or "").strip() or str(user.get("username") or "").strip()


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
