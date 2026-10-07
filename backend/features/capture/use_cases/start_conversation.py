"""Start / resume a capture conversation use case (T-027, RF-2, spec §5.2, case 8).

Orchestration of `POST /capture/start` (plan §3.3 step 1 and §4.1
`INICIAR_CONVERSACION`):

  - a user may only have ONE active capture conversation (RF-2, case 8): when the
    user already has an ``ACTIVA`` conversation it is resumed, never a second one
    is created;
  - when the assistant is available, a new conversation is created prefilled with
    the proponent data from the account (spec §5.2 common regimen) and the opening
    turn (greeting + first question + the field's fixed chips) is returned (RF-2);
  - when the assistant is unavailable, no orphan conversation is created and a
    manual-form signal is returned so the client deploys the contingency form
    (RF-7, case 1), already prefilled so nothing is lost (RNF-10).

The use case only orchestrates: the rules live in `capture_rules` (order, chips,
prefill turn) and the persistence (no-loss, active lookup) in
`ConversationStore`.
"""

import json
import uuid

from features.capture.domain import capture_rules as rules
from features.capture.domain.conversation import Conversation
from features.capture.infrastructure.conversation_store import ConversationStore
from shared.contracts.assistant_client import AssistantClient
from shared.contracts.user_directory import UserDirectory

# RF-7, case 1: the clear contingency notice shown when the assistant is down.
MANUAL_NOTICE = "El asistente no está disponible; completa el formulario manual."


def _proponent_prefill(directory: UserDirectory, user_id: str) -> dict[str, str]:
    """Preloads the proponent field with the account data (spec §5.2).

    Stored as a JSON string like every structured field (plan §2.2); the summary
    (G08) parses it back into the object.
    """
    user = directory.get(user_id)
    if user is None:
        return {}
    proponent = {
        "name": user.get("name", ""),
        "area": user.get("area", ""),
        "contact": user.get("contact", ""),
    }
    return {"proponent": json.dumps(proponent, ensure_ascii=False)}


def _assistant_turn(conversation: Conversation, *, greet: bool) -> dict:
    """The assistant turn for the conversation's current field.

    `currentField` is `None` once the 7 fields are complete (the summary turn is
    built by the finish flow, G08); a blank turn is returned for safety.
    """
    current = conversation.currentField
    if current is None:
        return {"text": "", "currentField": None, "quickOptions": []}
    turn = rules.build_question(current_field=current)
    if greet:
        turn["text"] = f"{rules.GREETING_TEXT}\n\n{turn['text']}"
    return turn


def start_conversation(
    store: ConversationStore,
    assistant: AssistantClient,
    directory: UserDirectory,
    *,
    user_id: str,
) -> dict:
    """Starts (or resumes) the user's capture conversation and returns the outcome.

    Returns:
      - when the user already has an ``ACTIVA`` conversation (RF-2, case 8):
        `{"mode": "assistant", "resumed": True, "conversation": <payload>,
        "assistant": <turn for its currentField>, "manual": None}`;
      - when a new ``ACTIVA`` is created (assistant available):
        `{"mode": "assistant", "resumed": False, "conversation": <payload>,
        "assistant": <greeting + first question + chips>, "manual": None}`;
      - without the assistant (RF-7, case 1):
        `{"mode": "manual", "resumed": False, "conversation": None,
        "assistant": None, "manual": {"notice": <contingency notice>,
        "capturedFields": <proponent prefill>}}` — no conversation is persisted.
    """
    existing = store.list_active(user_id)
    if existing:
        payload = existing[0]
        conversation = Conversation.from_payload(payload)
        return {
            "mode": "assistant",
            "resumed": True,
            "conversation": payload,
            "assistant": _assistant_turn(conversation, greet=False),
            "manual": None,
        }

    prefill = _proponent_prefill(directory, user_id)

    if not assistant.ping():
        return {
            "mode": "manual",
            "resumed": False,
            "conversation": None,
            "assistant": None,
            "manual": {"notice": MANUAL_NOTICE, "capturedFields": dict(prefill)},
        }

    candidate = "c_" + uuid.uuid4().hex[:8]
    while store.get(candidate) is not None:
        candidate = "c_" + uuid.uuid4().hex[:8]
    conversation = rules.new_conversation(
        conversation_id=candidate, user_id=user_id, prefill=prefill
    )
    payload = store.create(conversation)
    return {
        "mode": "assistant",
        "resumed": False,
        "conversation": payload,
        "assistant": _assistant_turn(conversation, greet=True),
        "manual": None,
    }
