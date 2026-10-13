"""Per-turn capture assistance (D7 replacement; RF-5 + free-text compaction).

`generate_turn_assist` is the single IA call made when the conversation lands
on a new field. It asks the model — grounded on the organization profile — for
BOTH at once:
  - the quick options to offer on the turn in the course, and
  - the improved, concise version of the free-text fields already captured.

It NEVER raises: an unavailable assistant (the ping/generate failure), an
uninterpretable reply or a malformed payload all degrade to `([], {})`, so the
capture flow simply continues without chips and without compaction (the flow
must never break because of the assistance, RF-7 spirit). The result is
validated and sanitised so the stored conversation can trust it.
"""

from typing import Any

from features.assistant.domain.prompts import turn_options_prompt
from features.assistant.domain.refinement import extract_json_object
from features.capture.domain import capture_rules as rules
from features.capture.domain.capture_rules import CHIP_ELIGIBLE_FIELDS, COMPACTABLE_FIELDS
from features.capture.domain.conversation import Conversation
from features.capture.infrastructure.conversation_store import ConversationStore
from features.capture.use_cases.suggest_title import propose_title
from shared.contracts.assistant_client import AssistantClient
from shared.exceptions.handlers import AssistantUnavailable

# Maximum number of quick options offered per turn (short, tappable list).
MAX_OPTIONS = 5
# Maximum length of a single option (keeps the chips tappable and short).
MAX_OPTION_LEN = 90


def _clean_options(raw: Any) -> list[str]:
    """Normalises the model's `options` list: unique, non-blank, short strings."""
    if not isinstance(raw, list):
        return []
    seen: set[str] = set()
    options: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            continue
        option = " ".join(item.split())[:MAX_OPTION_LEN].strip()
        if not option or option in seen:
            continue
        seen.add(option)
        options.append(option)
        if len(options) >= MAX_OPTIONS:
            break
    return options


def _clean_compact(raw: Any, captured: dict[str, Any]) -> dict[str, str]:
    """Normalises the model's `compact` mapping.

    Only a capturable free-text field that the model returned WITH actual text
    survives. The two structured fields and the title are never produced here
    (the prompt never shows them), so this is a pure filter/sanitize step.
    """
    if not isinstance(raw, dict):
        return {}
    compact: dict[str, str] = {}
    for key, value in raw.items():
        if key not in COMPACTABLE_FIELDS:
            continue
        if key not in captured:
            continue
        if not isinstance(value, str):
            continue
        text = " ".join(value.split()).strip()
        if text:
            compact[str(key)] = text
    return compact


def generate_turn_assist(
    assistant: AssistantClient,
    *,
    current_field: str,
    captured: dict[str, Any],
    org_profile: dict | None,
) -> tuple[list[str], dict[str, str]]:
    """Runs the turn assistance and returns `(options, compact)`.

    `options` are valid only when the field in the course accepts chips;
    `compact` are the improved free-text fields to apply to the conversation.
    Never raises (see module docstring).

    Only the free-text fields the assistant may compact are shown to the model:
    the two structured fields (`proponent`, `estimatedResources`) travel in
    `captured` as JSON strings and `title` is handled by RF-4, so none of them
    may ever reach the prompt (their shape is code-owned).
    """
    free_captured = {
        key: str(value)
        for key, value in captured.items()
        if key in COMPACTABLE_FIELDS and isinstance(value, str) and str(value).strip()
    }
    want_options = current_field in CHIP_ELIGIBLE_FIELDS
    want_compact = bool(free_captured)
    if not want_options and not want_compact:
        return [], {}
    try:
        raw = assistant.generate(
            turn_options_prompt(current_field=current_field,
                                captured=free_captured, org=org_profile)
        )
    except AssistantUnavailable:
        return [], {}
    data = extract_json_object(raw)
    if not isinstance(data, dict):
        return [], {}
    options = _clean_options(data.get("options")) if want_options else []
    compact = _clean_compact(data.get("compact"), free_captured) if want_compact else {}
    return options, compact


def land_turn(
    store: ConversationStore,
    assistant: AssistantClient,
    conversation: Conversation,
    *,
    org_profile: dict | None = None,
) -> dict | None:
    """Advances the conversation to the next pending field and builds its turn.

    The in-memory `conversation` (fields already applied by the caller) is
    advanced and persisted in ONE write (RNF-10: no partial state), together
    with the per-turn options the assistant generated for the new field and
    the improved free-text fields (compaction). Returns:

      - `None` when the 7 fields close (the conversation is saved as
        ``RESUMEN``; the caller builds the editable summary, RF-6);
      - the assistant turn dict (``text``/``currentField``/``quickOptions``/
        ``titleSuggestion``) otherwise.

    Raises `AssistantUnavailable` ONLY when the turn lands on ``title`` and the
    proactive proposal cannot be produced (RF-4/RF-7); the caller marks the
    conversation ``CONTINGENCIA`` with the captured fields as fallback.
    """
    next_field = rules.next_pending_field(conversation.order, conversation.capturedFields)
    if next_field is None:
        conversation.currentField = None
        conversation.state = "RESUMEN"
        store.save_conversation(conversation)
        return None

    conversation.currentField = next_field
    if next_field == "title":
        # The title turn carries the suggestion (RF-4); it never offers chips.
        conversation.offeredField = "title"
        conversation.offeredOptions = []
        store.save_conversation(conversation)
        suggestion = propose_title(store, assistant, conversation_id=conversation.id)
        return {
            "text": rules.QUESTION_BY_FIELD.get("title", ""),
            "currentField": "title",
            "quickOptions": [],
            "titleSuggestion": suggestion.get("titleSuggestion"),
        }

    options, compact = generate_turn_assist(
        assistant,
        current_field=next_field,
        captured=conversation.capturedFields,
        org_profile=org_profile,
    )
    for key, value in compact.items():
        conversation.set_field(key, value)
    conversation.offeredField = next_field
    conversation.offeredOptions = list(options)
    store.save_conversation(conversation)
    return build_turn(conversation)


def build_turn(conversation: Conversation) -> dict:
    """The reply turn for the conversation's current field, as stored.

    Rebuilds the turn from the PERSISTED conversation: the quick options travel
    back exactly as `land_turn` offered them for the field in the course (the
    only chips a later click may reference, RF-5 / D7 replacement), and a
    ``title`` turn re-shows its last suggestion (RF-4: the suggestion was
    persisted by `propose_title` on landing).
    """
    current = conversation.currentField
    if current is None:  # the 7 fields are complete (summary is built by finish)
        return {}
    turn = rules.build_question(
        current_field=current,
        quick_options=conversation.offered_options(current),
    )
    if current == "title":
        last = conversation.titleSuggestions[-1] if conversation.titleSuggestions else None
        from features.capture.use_cases.suggest_title import TITLE_ACTIONS

        turn["titleSuggestion"] = (
            {"text": last, "actions": list(TITLE_ACTIONS)} if last is not None else None
        )
    return {
        "text": turn["text"],
        "currentField": current,
        "quickOptions": list(turn["quickOptions"]),
        "titleSuggestion": turn.get("titleSuggestion"),
    }
