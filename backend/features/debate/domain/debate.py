"""Debate feature domain: the published-idea debate (RF-24, RF-25, RNF-11).

Pure domain: no FastAPI/Pydantic (decision D8). The `Debate` is an attribute
of a `VALIDADA_PUBLICA` idea (D12 — the published idea is never edited; the
debate lives alongside it).

Rules owned here:
- The debate opens when the idea is published with a deadline of
  `publication date + 30 days` (RF-24).
- Messages are only admitted while the debate is open; the deadline is
  enforced at read time (the first read after the deadline closes the debate
  exactly once — RF-24, case 18).
- Only the administrator adjusts the deadline, per idea, even on a closed
  debate; setting it to a future date re-opens it. Every adjustment is audited
  with who/when/before/after (RNF-11, case 18).
- The `@asistant` invocation, the assistant reply and the closure summary are
  AI operations (RF-25, RF-24); the domain only stores the assistant request
  as "pending" (retry at the next interaction, case 20) and the closure flag
  plus the AI-generated summary.

Audit fields (RNF-8 / RNF-11): `closedAt`/`closedById`, `deadlineHistory`
(every admin adjustment) and the assistant request/summary timestamps.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from shared.exceptions.handlers import DomainError

# Fixed deadline of the debate: publication date + 30 days (RF-24).
DEBATE_DAYS = 30

# The exact token that, at the start of a message, invokes the assistant in
# the thread (RF-25). The spec spells it `@asistant` (one s) — the single
# source of truth for the detection.
ASSISTANT_TOKEN = "@asistant"

# Displayed author of the AI messages (RF-25: "identified as the assistant's
# message, distinct from the user's ones"; plan §2.8 spells it "Asistente (IA)").
ASSISTANT_AUTHOR = "Asistente (IA)"

# The assistant's own messages carry this authorId (the user messages carry the
# account id; RNF-11 audit).
ASSISTANT_AUTHOR_ID = "assistant"


class DebateError(DomainError):
    """The `Debate` record is malformed, missing or unusable (400)."""

    def __init__(self, message: str) -> None:
        super().__init__("DEBATE_INVALID", message, status_code=400)


def _require_iso(value: Any, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise DebateError(f"El campo {name} del debate es obligatorio.")
    try:
        datetime.fromisoformat(text)
    except ValueError:
        raise DebateError(f"El campo {name} del debate no es una fecha ISO válida.") from None
    return text


def _as_str(value: Any) -> str:
    return str(value or "").strip()


@dataclass
class DebateMessage:
    """One message in the published-idea debate (RF-24, RNF-11).

    `id`/`ideaId` identify the message and the debate it belongs to;
    `authorId`/`authorName` register who wrote it ("Asistente (IA)" for the AI,
    RF-25); `text` the content; `linkedMessageId` the id of the message the
    reply references (the `@asistant` contract, RF-25); `isAssistant` flags
    the AI's own replies; `createdAt` the registration date (audit, RNF-11).
    """

    id: str
    ideaId: str
    authorId: str
    authorName: str
    text: str
    createdAt: str
    linkedMessageId: str | None = None
    isAssistant: bool = False
    processed: bool = True

    def __post_init__(self) -> None:
        if not str(self.id).strip():
            raise DebateError("El id del mensaje del debate es obligatorio.")
        if not str(self.ideaId).strip():
            raise DebateError("El id de la idea del mensaje del debate es obligatorio.")
        if not str(self.text).strip():
            raise DebateError("El texto del mensaje del debate no puede estar vacío.")
        _require_iso(self.createdAt, "createdAt")

    def to_payload(self) -> dict:
        """The stored camelCase message payload (plan §2.8)."""
        return {
            "id": self.id,
            "ideaId": self.ideaId,
            "authorId": self.authorId,
            "authorName": self.authorName,
            "text": self.text,
            "createdAt": self.createdAt,
            "linkedMessageId": self.linkedMessageId,
            "isAssistant": self.isAssistant,
            "processed": self.processed,
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "DebateMessage":
        """Rebuilds a message from a stored payload, rejecting a malformed one."""
        payload = payload or {}
        return cls(
            id=str(payload.get("id", "")),
            ideaId=str(payload.get("ideaId", "")),
            authorId=str(payload.get("authorId", "")),
            authorName=str(payload.get("authorName", "")),
            text=str(payload.get("text", "")),
            createdAt=str(payload.get("createdAt", "")),
            linkedMessageId=(payload.get("linkedMessageId") or None),
            isAssistant=bool(payload.get("isAssistant", False)),
            processed=bool(payload.get("processed", True)),
        )


def assistant_request(text: str) -> str | None:
    """The assistant's request, or `None` when the message is not an `@asistant`
    invocation (RF-25, case 19).

    A message invokes the assistant only when it starts with the token
    `@asistant`. The request is what remains after the token; blank requests
    are still invocations (the prompt falls back to the linked message as the
    question, case 19), so a non-`None` result means "ask the assistant".
    """
    stripped = str(text or "").strip()
    if not stripped.lower().startswith(ASSISTANT_TOKEN):
        return None
    return stripped[len(ASSISTANT_TOKEN):].strip()


@dataclass
class Debate:
    """The discussion thread of a `VALIDADA_PUBLICA` idea (RF-24).

    `deadline` is the end date (open when `now < deadline`); `closed` makes
    the closure definitive (once a debate closes it stays closed until the
    administrator extends the deadline to a future date); `summary` is the
    AI's closure summary, only when the debate had at least one message
    (otherwise `None`, case 21 — the UI says "there was no debate").
    `pendingAssistant` holds an `@asistant` request the assistant could not
    process (assistant down, case 20); it is retried at the next interaction.
    `deadlineHistory` is the audit of every admin adjustment (RNF-11).

    The `pendingAssistant` mapping is `{messageId, request, at}`: `messageId`
    is the (unprocessed) message the user wrote (visible in the thread with a
    warning), `request` the text that followed the `@asistant` token and `at`
    the moment the request was registered. It is `None` when there is nothing
    pending.
    """

    id: str
    ideaId: str
    deadline: str
    open: bool = True
    closed: bool = False
    closedAt: str | None = None
    closedBy: str | None = None
    summary: str | None = None
    summaryAt: str | None = None
    pendingAssistant: dict | None = None
    deadlineHistory: list = field(default_factory=list)
    messages: list = field(default_factory=list)

    def __post_init__(self) -> None:
        if not str(self.ideaId).strip():
            raise DebateError("El id de la idea del debate es obligatorio.")
        self.deadline = _require_iso(self.deadline, "deadline")
        self.open = not self.closed
        self.messages = [
            message if isinstance(message, DebateMessage) else DebateMessage.from_payload(message)
            for message in (self.messages or [])
        ]

    # -- time helpers -------------------------------------------------------
    def is_open(self, now: str) -> bool:
        """The debate accepts messages when it has not closed and `now < deadline`."""
        if self.closed:
            return False
        try:
            return datetime.fromisoformat(now) < datetime.fromisoformat(self.deadline)
        except ValueError:
            return False

    def is_past_deadline(self, now: str) -> bool:
        """`True` when the deadline has been reached or exceeded (`now >= deadline`)."""
        try:
            return datetime.fromisoformat(now) >= datetime.fromisoformat(self.deadline)
        except ValueError:
            return False

    # -- mutations (the use cases decide *when*, this fixes the shape) ------
    def add_message(self, message: DebateMessage) -> None:
        """Appends a message. The closed/open rule is enforced by the use case."""
        self.messages.append(message)

    def close(self, now: str, by_user: str | None = None) -> None:
        """Closes the debate definitively, once (idempotent, RF-24)."""
        if self.closed:
            return
        self.closed = True
        self.open = False
        self.closedAt = now
        self.closedBy = by_user

    def adjust_deadline(self, new_deadline: str, now: str, by_user: str | None = None,
                        by_name: str = "") -> None:
        """Admin per-idea deadline adjustment (RF-24, RNF-11).

        Advances or extends the deadline, even on a closed debate. Re-opening
        is adjusting the date to a future one (RF-24); a non-future date keeps
        (or makes) the debate closed. Every adjustment is audited with
        who/when/before/after in `deadlineHistory`.
        """
        new_deadline = _require_iso(new_deadline, "deadline")
        previous = self.deadline
        self.deadline = new_deadline
        try:
            future = datetime.fromisoformat(new_deadline) > datetime.fromisoformat(now)
        except ValueError:
            future = False
        if future:
            self.closed = False
            self.open = True
            self.closedAt = None
        else:
            self.closed = True
            self.open = False
            if self.closedAt is None:
                self.closedAt = now
        self.deadlineHistory.append({
            "by": by_user or "",
            "byName": by_name or "",
            "at": now,
            "before": previous,
            "after": new_deadline,
        })

    def set_summary(self, text: str, at: str) -> None:
        """Stores the AI closure summary (only when there was a debate, case 21)."""
        self.summary = text
        self.summaryAt = at

    # -- payloads ------------------------------------------------------------
    def to_payload(self) -> dict:
        """The stored camelCase debate payload (plan §2.8)."""
        return {
            "id": self.id,
            "ideaId": self.ideaId,
            "deadline": self.deadline,
            "open": self.open,
            "closed": self.closed,
            "closedAt": self.closedAt,
            "closedBy": self.closedBy,
            "summary": self.summary,
            "summaryAt": self.summaryAt,
            "pendingAssistant": self.pendingAssistant,
            "deadlineHistory": list(self.deadlineHistory or []),
            "messages": [message.to_payload() for message in self.messages],
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "Debate":
        """Rebuilds a debate from a stored payload, rejecting a malformed one."""
        payload = payload or {}
        return cls(
            id=str(payload.get("id", "")),
            ideaId=str(payload.get("ideaId", "")),
            deadline=str(payload.get("deadline", "")),
            open=bool(payload.get("open", True)),
            closed=bool(payload.get("closed", False)),
            closedAt=payload.get("closedAt"),
            closedBy=payload.get("closedBy"),
            summary=payload.get("summary"),
            summaryAt=payload.get("summaryAt"),
            pendingAssistant=payload.get("pendingAssistant"),
            deadlineHistory=list(payload.get("deadlineHistory") or []),
            messages=list(payload.get("messages") or []),
        )


def deadline_after_days(reference: str, days: int = DEBATE_DAYS) -> str:
    """The debate deadline: `reference` (the publication date) + `days` (RF-24)."""
    moment = datetime.fromisoformat(str(reference))
    return (moment + timedelta(days=days)).isoformat()
