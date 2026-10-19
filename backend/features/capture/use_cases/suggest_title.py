"""Suggest a title use case (T-029, RF-4; plan §4.3 `SUGERIR_TITULO`).

Orchestrates the proactive title suggestion (spec §5.2 / RF-4). The title is
never set by the free narrative: it is handled by this flow, where the
assistant proposes a title and the proponent picks one of the fixed actions:

  - ``accept``: store the currently proposed title, exactly as suggested;
  - ``another``: generate a NEW suggestion that is **different** from every
    earlier one (the loop persists the attempts in ``titleSuggestions``);
  - ``manual``: store the text the user typed **unmodified** (RF-4).

`propose_title` is the shared core used both here (initial/another) and by
`process_message` when it advances the turn onto ``title``, so the two use
cases never need to call each other's public entry points.
"""

import re

from features.assistant.domain.prompts import title_suggestion_prompt
from features.assistant.domain.refinement import extract_json_object
from features.capture.domain import capture_rules as rules
from features.capture.domain.conversation import Conversation
from features.capture.infrastructure.conversation_store import ConversationStore
from shared.contracts.assistant_client import AssistantClient
from shared.exceptions.handlers import AssistantUnavailable, DomainError

# The RF-4 fixed action set for a title suggestion.
TITLE_ACTIONS = ("accept", "another", "manual")
# Bounded retries so an uncooperative model cannot loop the "another" action.
MAX_TITLE_ATTEMPTS = 3

_WHITESPACE = re.compile(r"\s+")


def _own(store: ConversationStore, conversation_id: str, user_id: str) -> dict:
    payload = store.get(conversation_id)
    if payload is None:
        raise DomainError("CONVERSATION_NOT_FOUND", "La conversación no existe.", status_code=404)
    if payload["userId"] != user_id:
        raise DomainError(
            "NOT_CONVERSATION_OWNER",
            "Solo el propietario puede actuar sobre su conversación de captura.",
            status_code=403,
        )
    return payload


def _context(captured: dict) -> str:
    """A short description of what is known, as the model's context (plan §4.3)."""
    labels = {
        "description": "Descripción",
        "problem": "Problema",
        "expectedBenefit": "Beneficio esperado",
        "strategicAlignment": "Alineación estratégica",
    }
    parts = [f"{labels[key]}: {value}" for key, value in captured.items() if key in labels]
    return "\n".join(parts) if parts else "(todavía sin detalles)"


def _parse_title(raw: str) -> str | None:
    """Extracts the `title` field from the model's JSON reply, or `None`."""
    data = extract_json_object(raw)
    if isinstance(data, dict):
        title = data.get("title")
        if isinstance(title, str) and _WHITESPACE.sub(" ", title).strip():
            return _WHITESPACE.sub(" ", title).strip()
    return None


def propose_title(
    store: ConversationStore, assistant: AssistantClient, *, conversation_id: str,
    company_context: dict | None = None,
) -> dict:
    """Generates a NEW title distinct from the earlier suggestions and persists it.

    Returns the `titleSuggestion` dict (text + the RF-4 actions). Raises
    `AssistantUnavailable` (503, with the conversation's fields as fallback)
    when the model is unreachable. `company_context` grounds the suggestion on
    the company-context document (RF-22).
    """
    payload = store.get(conversation_id)
    if payload is None:
        raise DomainError("CONVERSATION_NOT_FOUND", "La conversación no existe.", status_code=404)
    conversation = Conversation.from_payload(payload)
    context = _context(conversation.capturedFields)
    avoid = list(conversation.titleSuggestions)
    for _ in range(MAX_TITLE_ATTEMPTS):
        try:
            raw = assistant.generate(
                title_suggestion_prompt(context, tuple(avoid), company_context)
            )
        except AssistantUnavailable as error:
            raise AssistantUnavailable(
                "ASSISTANT_UNAVAILABLE",
                "No se pudo sugerir un título; continúa por el formulario manual.",
                fallback={
                    "conversationId": conversation_id,
                    "capturedFields": conversation.to_payload()["capturedFields"],
                },
            ) from error
        title = _parse_title(raw)
        if title is None or title in avoid:
            if title is not None:
                avoid.append(title)
            continue
        store.add_title_suggestion(conversation_id, title)
        return {"titleSuggestion": {"text": title, "actions": list(TITLE_ACTIONS)}}
    # Bounded: nothing distinguishable was produced within the attempts.
    store.add_title_suggestion(conversation_id, avoid[-1] if avoid else "")
    return {"titleSuggestion": {"text": avoid[-1] if avoid else "", "actions": list(TITLE_ACTIONS)}}


def suggest_title(
    store: ConversationStore,
    assistant: AssistantClient,
    *,
    conversation_id: str,
    user_id: str,
    action: str,
    manual_text: str | None = None,
    company_context: dict | None = None,
) -> dict:
    """Applies a title action (RF-4) and returns the resulting turn.

    ``accept`` stores the last suggestion; ``another`` proposes a distinct new
    one; ``manual`` stores `manual_text` unmodified. ``accept``/``manual``
    advance to the next field (or to ``RESUMEN`` when the title was the last);
    ``another`` keeps the conversation on ``title`` with the new suggestion.

    `company_context` is the current company-context document injected in the
    assistant calls of this action (RF-22); when empty the prompt carries the
    no-context notice and the assistant still answers (case 24).
    """
    payload = _own(store, conversation_id, user_id)
    if action not in TITLE_ACTIONS:
        raise DomainError(
            "INVALID_TITLE_ACTION",
            f"Acción de título no válida: «{action}» (solo {', '.join(TITLE_ACTIONS)}).",
            status_code=400,
        )
    conversation = Conversation.from_payload(payload)
    if conversation.state != "ACTIVA":
        raise DomainError(
            "CONVERSATION_NOT_ACTIVE",
            "La conversación ya no está en curso; no se puede actuar sobre su título.",
            status_code=409,
        )
    if conversation.currentField != "title":
        raise DomainError(
            "TURN_NOT_ON_TITLE",
            "La conversación no está en el turno de título; responde primero la "
            "pregunta en curso.",
            status_code=409,
        )

    if action == "another":
        # Keep the turn on `title`; the new suggestion replaces the displayed one.
        return {
            "conversationId": conversation_id,
            "state": "ACTIVA",
            "assistant": rules.build_question(current_field="title")
            | propose_title(store, assistant, conversation_id=conversation_id,
                            company_context=company_context),
        }

    if action == "accept":
        if not conversation.titleSuggestions:
            raise DomainError(
                "NO_TITLE_TO_ACCEPT",
                "Aún no hay una sugerencia de título que aceptar.",
                status_code=409,
            )
        chosen = conversation.titleSuggestions[-1]
    else:  # manual: stored unmodified (RF-4)
        if manual_text is None or not _WHITESPACE.sub(" ", manual_text).strip():
            raise DomainError(
                "MANUAL_TITLE_REQUIRED", "Escribe el título que prefieres.", status_code=400
            )
        chosen = manual_text

    store.set_field(conversation_id, "title", chosen)
    conversation.capturedFields["title"] = chosen

    # `accept`/`manual` close the title: the turn advances to the next pending
    # field (or to the editable summary, RF-6). `land_turn` generates the IA
    # options for the landing field (D7 replacement). Imported lazily so the
    # `turn_assist` <-> `suggest_title` reference stays acyclic at import time.
    from features.capture.use_cases.turn_assist import land_turn

    next_field = rules.next_pending_field(conversation.order, conversation.capturedFields)
    if next_field is None:
        # The title closed the 6 fields: straight to the editable summary (RF-6).
        conversation.state = "RESUMEN"
        conversation.currentField = None
        store.save_conversation(conversation)
        return {
            "conversationId": conversation_id,
            "state": "RESUMEN",
            "summary": conversation.to_summary(),
        }

    turn = land_turn(store, assistant, conversation, company_context=company_context)
    return {
        "conversationId": conversation_id,
        "state": "ACTIVA",
        "assistant": turn,
    }
