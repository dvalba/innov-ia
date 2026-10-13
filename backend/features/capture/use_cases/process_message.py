"""Process a capture message use case (T-028, RF-3/RF-4/RF-5, RF-7 case 2).

Orchestration of `POST /capture/messages` (plan §3.3 step 2/3, §4.1
`PROCESAR_MENSAJE`):

  - a selected **chip** is the field's COMPLETE answer (RF-5): the chip's text
    is stored verbatim for the field in the course;
  - a **free narrative** goes through the assistant's extraction (RF-3): the
    model assigns the fragments to the PENDING fields only, each assigned field
    is marked captured and never re-asked, and an insufficient fragment
    (``__CLARIFICAR__``) triggers a clarification turn WITHOUT advancing
    (RF-3);
  - the turn then advances to the first still-pending field, skipping the
    captured ones (RF-3); when the 7 fields complete, the conversation moves to
    ``RESUMEN`` (RF-6) and the editable summary is returned;
  - a turn that lands on ``title`` is the suggestion turn (RF-4);
  - if the assistant is required and unavailable — the ping fails, `generate`
    raises, or the reply cannot be interpreted (case 14) — the conversation is
    marked ``CONTINGENCIA`` and its captured fields travel as the 503 fallback
    so the client continues on the pre-filled manual form without losing
    anything (RF-7 case 2, RNF-10).
"""

from features.assistant.domain.prompts import extract_fields_prompt
from features.assistant.domain.refinement import extract_json_object
from features.capture.domain import capture_rules as rules
from features.capture.domain.conversation import Conversation
from features.capture.infrastructure.conversation_store import ConversationStore
from features.capture.use_cases.suggest_title import propose_title
from shared.contracts.assistant_client import AssistantClient
from shared.exceptions.handlers import AssistantUnavailable, DomainError

_FALLBACK_CODE = "ASSISTANT_UNAVAILABLE"
_FALLBACK_MESSAGE = "El asistente no está disponible; continúa por el formulario manual."


def _unavailable(conversation: Conversation) -> AssistantUnavailable:
    """The 503 failure carrying the captured fields (RF-7 case 2, RNF-10)."""
    return AssistantUnavailable(
        _FALLBACK_CODE,
        _FALLBACK_MESSAGE,
        fallback={
            "conversationId": conversation.id,
            "capturedFields": conversation.capturedFields,
        },
    )


def _pending_fields(conversation: Conversation) -> tuple[str, ...]:
    return tuple(name for name in conversation.order if not conversation.has_field(name))


def _extract_fields(assistant: AssistantClient, conversation: Conversation, narrative: str):
    """Runs the extraction (RF-3) and normalizes the reply.

    Returns `{"fields": mapping, "clarify": bool}`, or `None` when the reply
    cannot be interpreted deterministically (case 14). Raises
    `AssistantUnavailable` when the model is unreachable.
    """
    pending = _pending_fields(conversation)
    if not pending:
        return {"fields": {}, "clarify": False}
    try:
        raw = assistant.generate(extract_fields_prompt(narrative, pending))
    except AssistantUnavailable:
        raise
    data = extract_json_object(raw)
    if not isinstance(data, dict):
        return None
    clarify = any(
        str(value).strip() == rules.CLARIFY_FLAG for key, value in data.items() if key in pending
    )
    # The clarification marker is a flag for the flow, not a field value: it is
    # never stored (otherwise ``has_field`` would treat the field as captured).
    fields = {
        key: str(value)
        for key, value in data.items()
        if key in pending and str(value).strip() and str(value).strip() != rules.CLARIFY_FLAG
    }
    return {"fields": fields, "clarify": clarify}


def _assistant_turn(store: ConversationStore, conversation: Conversation, assistant: AssistantClient) -> dict:
    """The reply turn for the conversation's current field (chips per field).

    The turn landing on `title` carries the title suggestion (RF-4); a model
    failure there degrades to the manual fallback as in any other step (RF-7).
    """
    current = conversation.currentField
    if current is None:  # the 7 fields are complete (summary is built by finish)
        return {}
    turn = rules.build_question(current_field=current)
    if current == "title":
        try:
            turn.update(propose_title(store, assistant, conversation_id=conversation.id))
        except AssistantUnavailable:
            _mark_contingency(store, conversation.id)
            raise
    return {
        "text": turn["text"],
        "currentField": current,
        "quickOptions": turn["quickOptions"],
        "titleSuggestion": turn.get("titleSuggestion"),
    }


def _mark_contingency(store: ConversationStore, conversation_id: str) -> Conversation:
    """Marks the conversation ``CONTINGENCIA`` (from ``ACTIVA`` only) and returns it."""
    payload = store.get(conversation_id)
    conversation = Conversation.from_payload(payload)
    conversation.state = "CONTINGENCIA"
    if payload["state"] == "ACTIVA":
        store.save_conversation(conversation)
    return conversation


def process_message(
    store: ConversationStore,
    assistant: AssistantClient,
    *,
    conversation_id: str,
    user_id: str,
    message: str | None = None,
    quick_option: str | None = None,
) -> dict:
    """Processes one user message of the capture conversation and returns the next turn.

    Exactly one of `message` (free narrative) or `quick_option` (a chip) must be
    given. Returns:
      - a clarification turn (`needsClarification: True`) when the answer is
        insufficient, without advancing (RF-3);
      - the next question + its fixed chips (RF-5), or the title-suggestion
        turn (RF-4), after advancing over the captured fields;
      - the editable summary (``state == "RESUMEN"``) when the 7 fields close
        (RF-6).

    Raises `AssistantUnavailable` (503) with the captured fields as fallback
    when the assistant is needed and unavailable (RF-7, case 2).
    """
    payload = store.get(conversation_id)
    if payload is None:
        raise DomainError("CONVERSATION_NOT_FOUND", "La conversación no existe.", status_code=404)
    if payload["userId"] != user_id:
        raise DomainError(
            "NOT_CONVERSATION_OWNER",
            "Solo el propietario puede enviar mensajes a su conversación.",
            status_code=403,
        )
    if (message is None or not str(message).strip()) and not (quick_option and str(quick_option).strip()):
        raise DomainError("EMPTY_MESSAGE", "El mensaje de captura está vacío.", status_code=400)
    conversation = Conversation.from_payload(payload)
    if conversation.state == "RESUMEN":
        return {
            "conversationId": conversation_id,
            "state": "RESUMEN",
            "summary": conversation.to_summary(),
        }
    if conversation.state == "CONTINGENCIA":
        raise _unavailable(conversation)
    if conversation.state == "TERMINADA":
        raise DomainError(
            "CONVERSATION_FINISHED",
            "La conversación ya finalizó; inicia una nueva para registrar otra idea.",
            status_code=409,
        )

    if quick_option and str(quick_option).strip():
        # A chip is the field's COMPLETE answer, taken verbatim (RF-5).
        chip = str(quick_option).strip()
        current = conversation.currentField
        if current is None or chip not in list(rules.CHIPS_BY_FIELD.get(current, ())):
            raise DomainError(
                "UNKNOWN_QUICK_OPTION",
                "Esa opción rápida no corresponde al campo en curso.",
                status_code=400,
            )
        rules.apply_capture(conversation.capturedFields, {current: chip}, current)
        _advance(store, conversation)
    else:
        narrative = str(message).strip()
        if not assistant.ping():
            _mark_contingency(store, conversation_id)
            raise _unavailable(conversation)
        extracted = _extract_fields(assistant, conversation, narrative)
        if extracted is None:  # uninterpretable reply (case 14): manual fallback
            _mark_contingency(store, conversation_id)
            raise _unavailable(conversation)
        fields, clarify = extracted["fields"], extracted["clarify"]
        if fields:
            rules.apply_capture(conversation.capturedFields, fields, conversation.currentField)
        if not clarify and fields:
            _advance(store, conversation)
        payload = store.get(conversation_id)
        stored = Conversation.from_payload(payload)
        if clarify:
            current = conversation.currentField
            turn = rules.build_question(current_field=current)
            return {
                "conversationId": conversation_id,
                "state": "ACTIVA",
                "assistant": {
                    "text": turn["text"],
                    "currentField": current,
                    "quickOptions": list(turn["quickOptions"]),
                    "titleSuggestion": None,
                    "needsClarification": True,
                },
            }
        conversation = stored

    if conversation.state == "RESUMEN":
        return {
            "conversationId": conversation_id,
            "state": "RESUMEN",
            "summary": conversation.to_summary(),
        }
    turn = _assistant_turn(store, conversation, assistant)
    return {
        "conversationId": conversation_id,
        "state": "ACTIVA",
        "assistant": turn,
    }


def _advance(store: ConversationStore, conversation: Conversation) -> None:
    """Moves the turn to the next pending field, or closes the conversation as
    ``RESUMEN`` when the 7 fields complete (RF-3, RF-6); persists atomically."""
    conversation.currentField = rules.next_pending_field(conversation.order, conversation.capturedFields)
    if conversation.currentField is None:
        conversation.state = "RESUMEN"
    store.save_conversation(conversation)
