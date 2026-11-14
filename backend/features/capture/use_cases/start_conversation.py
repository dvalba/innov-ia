"""Start / resume a capture conversation use case (T-027, RF-2, spec §5.2, case 8).

Orchestration of `POST /capture/start` (plan §3.3 step 1 and §4.1
`INICIAR_CONVERSACION`):

   - a user may only have ONE capture conversation in the cycle (RF-2, case 8,
     v2.3): when the user already has an ``ACTIVA`` conversation it is resumed
     first, and if there is none but a ``RESUMEN`` one, the most recent one is
     resumed WITH its editable summary (`to_summary`) so the captured fields
     are never lost; no second conversation is created;
  - when the assistant is available, a new conversation is created prefilled with
    the proponent data from the account (spec §5.2 common regimen) and the opening
    turn (greeting + first question) is returned (RF-2). The opening field never
    accepts quick options: the per-turn IA call that generates them happens on
    the first message (`process_message`), not on the opening (D7 replacement);
  - when the assistant is unavailable, no orphan conversation is created and a
    manual-form signal is returned so the client deploys the contingency form
    (RF-7, case 1), already prefilled so nothing is lost (RNF-10).

The use case only orchestrates: the rules live in `capture_rules` (order,
per-turn options, prefill turn) and the persistence (no-loss, active lookup) in
`ConversationStore`.
"""

import json
import uuid

from features.capture.domain import capture_rules as rules
from features.capture.domain.conversation import Conversation
from features.capture.infrastructure.conversation_store import ConversationStore
from features.capture.use_cases.turn_assist import build_turn
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
    name = str(user.get("name", "")).strip()
    area = str(user.get("area", "")).strip()
    contact = str(user.get("contact", "")).strip()
    # Only prefill when the account proponent is COMPLETE (spec §5.2: the user
    # can correct or complete it). A non-blank partial prefill would make
    # `next_pending_field` skip the proponent question entirely, leaving the
    # user unable to complete the missing part in chat (it would fail the
    # 6-field validation at finish, RNF-5).
    if not (name and area and contact):
        return {}
    proponent = {"name": name, "area": area, "contact": contact}
    return {"proponent": json.dumps(proponent, ensure_ascii=False)}


def _assistant_turn(conversation: Conversation, *, greet: bool) -> dict:
    """The assistant turn for the conversation's current field.

    `currentField` is `None` once the 6 fields are complete (the summary turn is
    built by the finish flow, G08); a blank turn is returned for safety.

    The quick options travel back exactly as they were OFFERED and persisted for
    the field in the course (RF-5 / D7 replacement): a resumed conversation re-
    shows the options its turn already had, and a new conversation (opening on
    `description`) offers none — the first per-turn IA call happens on the first
    message (`process_message`), not on the opening.
    """
    current = conversation.currentField
    if current is None:
        return {"text": "", "currentField": None, "quickOptions": [], "titleSuggestion": None}
    turn = build_turn(conversation)
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

    Every outcome carries `state` (the conversation state: ``ACTIVA``/``RESUMEN``,
    or `None` without a conversation) and `summary` (the editable summary when
    the resumed conversation is in ``RESUMEN``, else `None`).

    Returns:
      - when the user already has an ``ACTIVA`` conversation (RF-2, case 8):
        `{"mode": "assistant", "resumed": True, "conversation": <payload>,
        "assistant": <turn for its currentField>, "state": "ACTIVA",
        "summary": None, "manual": None}`;
      - when there is no ``ACTIVA`` but the user has ``RESUMEN`` conversations
        (v2.3): the most recent one is resumed with its editable summary and no
        new turn is started:
        `{"mode": "assistant", "resumed": True, "conversation": <payload>,
        "assistant": None, "state": "RESUMEN", "summary": <to_summary()>,
        "manual": None}`;
      - when a new ``ACTIVA`` is created (assistant available):
        `{"mode": "assistant", "resumed": False, "conversation": <payload>,
        "assistant": <greeting + first question + chips>, "state": "ACTIVA",
        "summary": None, "manual": None}`;
      - without the assistant (RF-7, case 1):
        `{"mode": "manual", "resumed": False, "conversation": None,
        "assistant": None, "state": None, "summary": None,
        "manual": {"notice": <contingency notice>,
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
            "state": "ACTIVA",
            "summary": None,
            "manual": None,
        }

    # v2.3: without an ACTIVA, resume the most recent RESUMEN with its editable
    # summary — the captured fields are never lost (RF-2/RF-6, decision D22).
    in_progress = [
        payload for payload in store.list_in_progress(user_id)
        if payload["state"] == "RESUMEN"
    ]
    if in_progress:
        payload = max(in_progress, key=lambda item: item.get("createdAt", ""))
        conversation = Conversation.from_payload(payload)
        return {
            "mode": "assistant",
            "resumed": True,
            "conversation": payload,
            "assistant": None,
            "state": "RESUMEN",
            "summary": conversation.to_summary(),
            "manual": None,
        }

    prefill = _proponent_prefill(directory, user_id)

    if not assistant.ping():
        return {
            "mode": "manual",
            "resumed": False,
            "conversation": None,
            "assistant": None,
            "state": None,
            "summary": None,
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
        "state": "ACTIVA",
        "summary": None,
        "manual": None,
    }
