"""Finish the capture use case (T-030, RF-6, RNF-5).

Orchestration of `POST /capture/finish` (plan §3.3 step 5): when the
proponent confirms the editable summary, the 7 fields of the confirmed
payload are validated through `create_idea` (G06, the single source of
RNF-5 and of the contact format, case 12) and the idea is registered in
`EN_DESARROLLO` with origin `asistida`; the conversation is then closed as
`TERMINADA` (compare-and-set, RNF-9).

Case 7 (abandonment without submit): without a confirmation nothing is
left — no draft, no idea. Finishing from any state other than `RESUMEN`
is refused (409), so a partial conversation can never register an idea.
"""

import json
from contextlib import suppress

from features.capture.domain.conversation import STRUCTURED_FIELDS, Conversation
from features.capture.infrastructure.conversation_store import ConversationStore
from features.ideas.use_cases.create_idea import create_idea
from shared.contracts.idea_ledger import ORIGIN_ASISTIDA
from shared.exceptions.handlers import DomainError


def _own(store: ConversationStore, conversation_id: str, user_id: str) -> dict:
    payload = store.get(conversation_id)
    if payload is None:
        raise DomainError("CONVERSATION_NOT_FOUND", "La conversación no existe.", status_code=404)
    if payload["userId"] != user_id:
        raise DomainError(
            "NOT_CONVERSATION_OWNER",
            "Solo el propietario puede finalizar su conversación de captura.",
            status_code=403,
        )
    return payload


def _normalized(fields: dict) -> dict:
    """The structured fields may arrive as JSON strings (as stored during the
    capture, plan §2.2); they are parsed back into their objects before the
    idea's 7-field validation (RNF-5). A value that parses keeps its object
    form; a text that does not parse is left as-is (it will fail the
    structured check, as it must)."""
    normalized = dict(fields)
    for key in STRUCTURED_FIELDS:
        value = normalized.get(key)
        if isinstance(value, str) and value.strip():
            with suppress(json.JSONDecodeError):
                normalized[key] = json.loads(value)
    return normalized


def finish_capture(
    store: ConversationStore,
    ledger,
    *,
    conversation_id: str,
    user_id: str,
    captured: dict | None = None,
) -> dict:
    """Confirms the summary and registers the idea (RF-6).

    `captured` is the confirmed summary: it wins over the stored values for
    the fields it carries (a free correction overrides the capture). It is
    validated by `create_idea`: a missing/empty field (RNF-5) or a malformed
    contact (case 12) is a `ValidationFailed` (422) and the conversation is
    left as-is, in `RESUMEN`, so the proponent can correct and retry — no
    idea ever exists with a gap. On success the idea payload is returned
    with the conversation id.
    """
    payload = _own(store, conversation_id, user_id)
    if payload["state"] != "RESUMEN":
        raise DomainError(
            "CONVERSATION_NOT_IN_SUMMARY",
            "La conversación debe estar en el resumen confirmado para finalizar; "
            "sin confirmar no se registra nada (caso 7).",
            status_code=409,
        )
    conversation = Conversation.from_payload(payload)
    # The confirmed summary wins over the stored value for the fields it
    # carries (a free correction overrides the capture); the merged mapping is
    # then normalized before the 7-field validation.
    confirmed = _normalized({**conversation.capturedFields, **(captured or {})})
    idea = create_idea(ledger, owner_id=user_id, origin=ORIGIN_ASISTIDA, fields=confirmed)
    # Compare-and-set (RNF-9): only from RESUMEN, so a concurrent state change
    # cannot terminate a conversation that has already moved on.
    store.set_state(conversation_id, "TERMINADA", current_state="RESUMEN")
    return {**idea, "conversationId": conversation_id}
