"""Process a capture message use case (T-028, RF-3/RF-4/RF-5, RF-7 case 2).

Orchestration of `POST /capture/messages` (plan §3.3 step 2/3, §4.1
`PROCESAR_MENSAJE`):

  - a selected **chip** is the field's COMPLETE answer (RF-5): the chip's text
    is stored verbatim for the field in the course; a chip is only valid when
    it was ACTUALLY OFFERED on the turn in the course (the per-turn options the
    assistant generated, D7 replacement);
  - a **free narrative** goes through the assistant's extraction (RF-3): the
    model assigns the fragments to the PENDING fields only, each assigned field
    is marked captured and never re-asked, and an insufficient fragment
    (``__CLARIFICAR__``) triggers a clarification turn WITHOUT advancing
    (RF-3); on a clarification nothing is persisted — the user re-answers;
  - the turn then advances to the first still-pending field, skipping the
    captured ones (RF-3); on the landing the assistant generates the field's
    quick options AND improves the free-text fields already captured (the
    single per-turn IA call, `turn_assist.land_turn`); when the 7 fields
    complete, the conversation moves to ``RESUMEN`` (RF-6) and the editable
    summary is returned;
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
from features.capture.use_cases.turn_assist import build_turn, land_turn
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


def _mark_contingency(store: ConversationStore, conversation_id: str) -> Conversation:
    """Marks the conversation ``CONTINGENCIA`` (from ``ACTIVA`` only) and returns it."""
    payload = store.get(conversation_id)
    conversation = Conversation.from_payload(payload)
    conversation.state = "CONTINGENCIA"
    if payload["state"] == "ACTIVA":
        store.save_conversation(conversation)
    return conversation


def _clarify_turn(conversation: Conversation) -> dict:
    """The clarification turn (RF-3): it REPEATS the question in the course
    WITHOUT advancing, reusing the options the assistant had already offered
    for it (a re-asked field is not re-offered new chips)."""
    turn = build_turn(conversation)
    if turn:
        turn["needsClarification"] = True
    return turn


def process_message(
    store: ConversationStore,
    assistant: AssistantClient,
    *,
    conversation_id: str,
    user_id: str,
    message: str | None = None,
    quick_option: str | None = None,
    org_profile: dict | None = None,
) -> dict:
    """Processes one user message of the capture conversation and returns the next turn.

    Exactly one of `message` (free narrative) or `quick_option` (a chip) must be
    given. `org_profile` is the organization profile grounding the per-turn
    assistant call (D7 replacement); when absent the assistant still answers
    (the prompt is told the profile is missing).

    Returns:
      - a clarification turn (`needsClarification: True`) when the answer is
        insufficient, without advancing (RF-3);
      - the next question + its per-turn options (RF-5, D7 replacement), or the
        title-suggestion turn (RF-4), after advancing over the captured fields;
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
        # A chip is the field's COMPLETE answer, taken verbatim (RF-5): it is
        # only valid when it was offered on the turn in the course.
        chip = str(quick_option).strip()
        current = conversation.currentField
        if current is None or chip not in conversation.offered_options(current):
            raise DomainError(
                "UNKNOWN_QUICK_OPTION",
                "Esa opción rápida no corresponde al campo en curso.",
                status_code=400,
            )
        rules.apply_capture(conversation.capturedFields, {current: chip}, current)
        turn = _advance(store, assistant, conversation, org_profile=org_profile)
        return _result(store, conversation_id, turn)

    narrative = str(message).strip()
    if not assistant.ping():
        _mark_contingency(store, conversation_id)
        raise _unavailable(conversation)
    extracted = _extract_fields(assistant, conversation, narrative)
    if extracted is None:  # uninterpretable reply (case 14): manual fallback
        _mark_contingency(store, conversation_id)
        raise _unavailable(conversation)
    fields, clarify = extracted["fields"], extracted["clarify"]

    if clarify:
        # An insufficient answer: the question repeats WITHOUT advancing and
        # nothing is persisted — the user re-answers (RF-3). The options offered
        # for the field in the course are reused.
        return {
            "conversationId": conversation_id,
            "state": "ACTIVA",
            "assistant": _clarify_turn(conversation),
        }

    if not fields:
        # The narrative captured nothing usable: re-ask the field in the course
        # unchanged (no advance, no extra IA call).
        stored = Conversation.from_payload(store.get(conversation_id))
        return {
            "conversationId": conversation_id,
            "state": "ACTIVA",
            "assistant": build_turn(stored),
        }

    rules.apply_capture(conversation.capturedFields, fields, conversation.currentField)
    turn = _advance(store, assistant, conversation, org_profile=org_profile)
    return _result(store, conversation_id, turn)


def _advance(
    store: ConversationStore,
    assistant: AssistantClient,
    conversation: Conversation,
    *,
    org_profile: dict | None = None,
) -> dict:
    """Advances the turn to the next pending field (or closes the conversation)
    via `land_turn` and returns the reply turn.

    A mid-advance assistant failure — the only one that can raise, on the
    ``title`` turn its proactive proposal is required (RF-4) — is the
    contingency fallback (RF-7 case 2, RNF-10).
    """
    try:
        return land_turn(store, assistant, conversation, org_profile=org_profile) or {}
    except AssistantUnavailable:
        _mark_contingency(store, conversation.id)
        raise


def _result(store: ConversationStore, conversation_id: str, turn: dict) -> dict:
    """Wraps an advanced turn: when the 7 fields closed the conversation, the
    editable summary is returned (RF-6); otherwise the assistant turn (RF-3/5)."""
    stored = Conversation.from_payload(store.get(conversation_id))
    if stored.state == "RESUMEN":
        return {
            "conversationId": conversation_id,
            "state": "RESUMEN",
            "summary": stored.to_summary(),
        }
    return {
        "conversationId": conversation_id,
        "state": "ACTIVA",
        "assistant": turn,
    }
