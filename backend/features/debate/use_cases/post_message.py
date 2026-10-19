"""Post a message in a published-idea debate (RF-24).

Any user with an active session may post while the debate is open. The debate
is opened with `deadline = publication date + 30 days` and closes definitively
when `now >= deadline` (the closure itself is owned by `close_debate`, which
also runs at read time). A message is never admitted on a closed debate (case
18). The audit registers the author (id and name) and the creation date
(RNF-11).

`@asistant` detection and the AI reply are the router/`post_message_with_ai`
concerns (RF-25, T-073); here the message is only registered.
"""

import uuid

from features.debate.domain.debate import DebateMessage
from features.debate.infrastructure.debate_store import DebateStore
from shared.exceptions.handlers import DomainError


def build_message(
    *,
    idea_id: str,
    author_id: str,
    author_name: str,
    text: str,
    now: str,
    linked_message_id: str | None = None,
    is_assistant: bool = False,
    processed: bool = True,
) -> DebateMessage:
    """Builds the message entity (shared with the AI reply path).

    A blank `text` is a `DebateError` (400). The id is `debate_msg_<short>`.
    `processed` lets the `@asistant` path register a user message the AI could
    not answer yet (case 20: `processed=False` until the pending request is
    retried).
    """
    return DebateMessage(
        id="debate_msg_" + uuid.uuid4().hex[:10],
        ideaId=str(idea_id),
        authorId=str(author_id),
        authorName=str(author_name),
        text=str(text or ""),
        createdAt=now,
        linkedMessageId=linked_message_id,
        isAssistant=is_assistant,
        processed=processed,
    )


def post_message(
    store: DebateStore,
    *,
    idea_id: str,
    author_id: str,
    author_name: str,
    text: str,
    now: str,
    linked_message_id: str | None = None,
    is_assistant: bool = False,
) -> dict:
    """Registers a message in the open debate and returns the debate payload.

    Raises `DomainError` (404) when the idea has no debate, `DomainError` (409)
    when the debate is closed (case 18), and `DebateError` (400) when the text
    is blank.
    """
    debate = store.get_debate(idea_id)
    if debate is None:
        raise DomainError("DEBATE_NOT_FOUND", "La idea aún no tiene debate abierto.", status_code=404)
    if debate.closed:
        raise DomainError(
            "DEBATE_CLOSED",
            "El debate está cerrado; no se admiten nuevos mensajes.",
            status_code=409,
        )
    message = build_message(
        idea_id=idea_id,
        author_id=author_id,
        author_name=author_name,
        text=text,
        now=now,
        linked_message_id=linked_message_id,
        is_assistant=is_assistant,
    )
    debate.add_message(message)
    return store.set(debate)
