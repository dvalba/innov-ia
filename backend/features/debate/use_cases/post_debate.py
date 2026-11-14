"""Post a message in a published-idea debate (RF-24, RF-25, cases 18-20).

Posting is where the time and the `@asistant` rules run (plan §4.7): the
debate first closes automatically if its deadline was reached, and a closed
debate never admits a new message (case 18, 409). A message that starts with
the `@asistant` token **and carries a non-blank request** is an invocation
(v2.5, case 19): the assistant replies inline, and the linked message — when
one is provided — is optional context for the answer. A dangling `@asistant`
link is a 400. When the assistant is down the request is kept pending
(case 20).

The AI pieces (the reply, the summary at closure, the company context, the
idea fields) are read by the caller at request time and passed in (RF-22), so
this use case stays pure and feature-isolated.
"""

from collections.abc import Callable
from datetime import datetime

from features.debate.domain.debate import assistant_request
from features.debate.infrastructure.debate_store import DebateStore
from features.debate.use_cases.assist import (
    process_pending_assistant,
    try_assist,
)
from features.debate.use_cases.close_debate import close_debate
from features.debate.use_cases.post_message import build_message
from shared.contracts.assistant_client import AssistantClient
from shared.exceptions.handlers import DomainError


def _resolve_linked(debate, linked_message_id: str | None) -> object | None:
    if not linked_message_id:
        return None
    return next((m for m in debate.messages if m.id == str(linked_message_id)), None)


def post_debate_message(
    store: DebateStore,
    *,
    idea_id: str,
    author_id: str,
    author_name: str,
    text: str,
    linked_message_id: str | None,
    summary: Callable[[list], str | None] | None,
    assistant: AssistantClient | None,
    idea_fields: dict | None,
    company_context: dict | None,
    evaluate: Callable[[str], None] | None = None,
    now: str | None = None,
) -> dict:
    """Registers a message in the open debate and, when it is a valid
    `@asistant` invocation, the assistant replies inline in the thread
    (v2.5: `@asistant` + non-blank request; the linked message, when provided,
    is optional context).

    Returns `{"message", "assistantReply", "debate"}`. A 404 when the idea has
    no debate, a 409 when it is closed (case 18) — or just closed at its
    deadline — and a 400 when the `@asistant` link is dangling. A blank `text`
    is a 400 (domain error, raised by the message builder).
    """
    moment = now or datetime.now().isoformat()
    # An empty/blank `linkedMessageId` is the same as no link (plan §3.2): it
    # never counts as a dangling reference.
    if linked_message_id is not None and not str(linked_message_id).strip():
        linked_message_id = None
    # The deadline closure runs at write time (case 18): a missing debate is a
    # 404 (close_debate) and, if the deadline was reached, the debate closes
    # now (its summary is generated and the AI evaluation is generated at the
    # closure) before we reject the post.
    close_debate(store, idea_id=idea_id, now=moment, summarize=summary, evaluate=evaluate)
    debate = store.get_debate(idea_id)
    assert debate is not None  # close_debate guarantees a record from here on
    if debate.closed:
        raise DomainError(
            "DEBATE_CLOSED",
            "El debate está cerrado (fecha límite alcanzada).",
            status_code=409,
        )

    # Every write gives a pending `@asistant` request one more retry (case 20).
    process_pending_assistant(
        debate,
        idea_id=idea_id,
        assistant=assistant,
        idea_fields=idea_fields,
        company_context=company_context,
        now=moment,
    )

    request = assistant_request(text)
    linked = _resolve_linked(debate, linked_message_id)
    if request is not None and linked_message_id is not None and linked is None:
        # A provided link that does not exist in the thread is an invalid
        # reference (plan §4.7): 400. A `@asistant` with *no* link still
        # invokes the assistant (v2.5, case 19): the link is optional context.
        raise DomainError(
            "DEBATE_LINK_INVALID",
            "El mensaje enlazado de la invocación @asistant no existe en el debate.",
            status_code=400,
        )
    message = build_message(
        idea_id=idea_id,
        author_id=author_id,
        author_name=author_name,
        text=text,
        now=moment,
        linked_message_id=linked_message_id,
    )
    debate.add_message(message)
    if request is not None:
        reply = try_assist(
            debate,
            idea_id=idea_id,
            user_message=message,
            linked_message=linked,
            request=request,
            assistant=assistant,
            idea_fields=idea_fields,
            company_context=company_context,
            now=moment,
        )
    else:
        reply = None

    payload = store.set(debate)
    return {
        "message": message.to_payload(),
        "assistantReply": reply.to_payload() if reply is not None else None,
        "debate": payload,
    }
