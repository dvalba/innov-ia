"""The `@asistant` intervention in a published-idea debate (RF-25, case 20).

The invocation rule (RF-25, case 19, v2.5): a message starting with the
`@asistant` token **and carrying a non-blank request** is an invocation; the
assistant then replies inline in the thread. The message link is *optional*
context for the answer:

- no request after   the token (`@asistant` alone) -> the message is posted
                as a plain user message (case 19);
- a request given    -> the assistant replies in the thread (RF-25), with the
                linked message as context when one is provided, or a general
                answer about the idea and the debate otherwise;
- a provided link    that does not exist in the thread -> 400 (invalid
                reference).

When the assistant is down or the generation fails (RNF-1, case 20), the user
message is kept in the thread with `processed=False` and the request is stored
as `debate.pendingAssistant` so the very next interaction retries it. The
rest of the thread keeps operating without the AI.

This module only produces the assistant's reply, the pending state and the
closure-summary binding; it stays pure (the `assistant`, the company context
and the idea fields are injected by the caller — the composition root, RF-22).
"""

from collections.abc import Callable
from datetime import datetime

from features.assistant.domain.evaluation import generate_evaluation
from features.assistant.domain.prompts import debate_assistant_prompt, debate_summary_prompt
from features.debate.domain.debate import (
    ASSISTANT_AUTHOR,
    ASSISTANT_AUTHOR_ID,
    Debate,
    DebateMessage,
)
from features.debate.use_cases.post_message import build_message
from shared.contracts.assistant_client import AssistantClient
from shared.exceptions.handlers import AssistantUnavailable


def make_summarize(
    assistant: AssistantClient | None,
    idea_fields: dict | None,
    company_context: dict | None,
) -> Callable[[list], str | None] | None:
    """Builds the `summarize` binding for `close_debate` (RF-24, case 21).

    Returns `None` when there is no assistant (the summary then stays pending
    forever on a down assistant — the debate still closes). The returned
    callable maps a list of message payloads to the summary text, or `None`
    when the assistant is down / the generation fails (RF-1).
    """
    if assistant is None:
        return None

    def _summarize(messages: list) -> str | None:
        if not assistant.ping():
            return None
        prompt = debate_summary_prompt(
            idea_fields=idea_fields or {},
            company_context=company_context,
            messages=messages,
        )
        try:
            text = assistant.generate(prompt)
        except AssistantUnavailable:
            return None
        text = str(text or "").strip()
        return text or None

    return _summarize


def make_evaluate(
    assistant: AssistantClient | None,
    ledger,
    company_context: dict | None,
    idea_id: str,
    on_generated: Callable[[str], None] | None = None,
) -> Callable[[str], None] | None:
    """Builds the `evaluate` binding for `close_debate` (RF-26, case 22).

    Returns `None` when there is no assistant (the evaluation then stays
    `PENDING` on a down assistant — the debate still closes). The returned
    callable runs `generate_evaluation` for the idea once, at the debate's
    closure and again at every later read (or write) while the evaluation
    stays `PENDING`; the final status is read back from the ledger (a decided
    evaluation is never clobbered, the retry belongs to
    `retry_pending_evaluations`).

    `on_generated` (T-083) is forwarded to `generate_evaluation`, so the first
    time the evaluation reaches `GENERADA` through this binding the caller's
    fanout fires exactly once per idea (RNF-9).
    """
    if assistant is None:
        return None

    def _evaluate(target_idea_id: str) -> None:
        generate_evaluation(
            ledger, assistant,
            idea_id=target_idea_id or idea_id,
            company_context=company_context,
            now=datetime.now().isoformat(),
            on_generated=on_generated,
        )

    return _evaluate


def _resolve_linked(debate: Debate, linked_message_id: str | None) -> DebateMessage | None:
    """The linked message of the thread, or `None` when the id is absent/dangling."""
    if not linked_message_id:
        return None
    return next((m for m in debate.messages if m.id == str(linked_message_id)), None)


def _assistant_reply(
    assistant: AssistantClient,
    *,
    idea_id: str,
    idea_fields: dict | None,
    company_context: dict | None,
    user_message: DebateMessage,
    linked: DebateMessage | None,
    request: str,
    now: str,
) -> DebateMessage:
    """Generates the assistant reply and builds its message (the AI text is
    stored verbatim in the thread, linked back to the user's `@asistant`
    message, RF-25). `linked` is the optional context message (v2.5): the
    prompt answers the request about the idea and the debate in general when
    it is `None`."""
    prompt = debate_assistant_prompt(
        idea_fields=idea_fields or {},
        company_context=company_context,
        linked_message=(
            {"authorName": linked.authorName, "text": linked.text} if linked is not None else None
        ),
        request=request,
    )
    text = assistant.generate(prompt)
    return build_message(
        idea_id=idea_id,
        author_id=ASSISTANT_AUTHOR_ID,
        author_name=ASSISTANT_AUTHOR,
        text=text,
        now=now,
        linked_message_id=user_message.id,
        is_assistant=True,
    )


def try_assist(
    debate: Debate,
    *,
    idea_id: str,
    user_message: DebateMessage,
    linked_message: DebateMessage | None,
    request: str,
    assistant: AssistantClient | None,
    idea_fields: dict | None,
    company_context: dict | None,
    now: str,
) -> DebateMessage | None:
    """Attempts the assistant reply for a valid `@asistant` invocation.

    Returns the assistant's reply message on success. On a down assistant or a
    failed generation it returns `None` and registers the request as pending
    (`debate.pendingAssistant`) with the user message marked `processed=False`
    (case 20). The caller registers the user message before calling.
    """
    if assistant is None or not assistant.ping():
        _mark_pending(debate, user_message, str(request or "").strip(), now)
        return None
    try:
        reply = _assistant_reply(
            assistant,
            idea_id=idea_id,
            idea_fields=idea_fields,
            company_context=company_context,
            user_message=user_message,
            linked=linked_message,
            request=request,
            now=now,
        )
    except AssistantUnavailable:
        _mark_pending(debate, user_message, str(request or "").strip(), now)
        return None
    if reply is None:
        _mark_pending(debate, user_message, str(request or "").strip(), now)
        return None
    user_message.processed = True
    debate.add_message(reply)
    debate.pendingAssistant = None
    return reply


def process_pending_assistant(
    debate: Debate,
    *,
    idea_id: str,
    assistant: AssistantClient | None,
    idea_fields: dict | None,
    company_context: dict | None,
    now: str,
) -> bool:
    """Retries a pending `@asistant` request (RNF-1, case 20) when the assistant
    is back. Returns `True` when a reply was produced (the original message is
    marked processed and the pending cleared). A down assistant leaves the
    request pending for the next interaction."""
    pending = debate.pendingAssistant
    if not pending or assistant is None:
        return False
    message_id = str(pending.get("messageId") or "")
    message = next((m for m in debate.messages if m.id == message_id), None)
    if message is None:
        debate.pendingAssistant = None
        return False
    # The original link (when the invocation had one) is the context again;
    # an invocation posted without a link retries without context (v2.5).
    linked = _resolve_linked(debate, message.linkedMessageId)
    reply = try_assist(
        debate,
        idea_id=idea_id,
        user_message=message,
        linked_message=linked,
        request=str(pending.get("request") or ""),
        assistant=assistant,
        idea_fields=idea_fields,
        company_context=company_context,
        now=now,
    )
    return reply is not None


def _mark_pending(debate: Debate, message: DebateMessage, request: str, now: str) -> None:
    """Stores the unprocessed request so the next interaction can retry it."""
    message.processed = False
    debate.pendingAssistant = {"messageId": message.id, "request": request, "at": now}
