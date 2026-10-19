"""Capture rules and `Conversation` domain tests (T-025, RF-2/RF-3/RF-5).

Covers the conversational contracts of the capture feature:
  - the exact RF-3 field order and the skip of already-captured fields;
  - the per-turn quick options: which fields may be offered chips, which may
    be compacted, and the question builder that carries the offered options
    (RF-5, D7 replacement: the assistant generates them, no fixed catalog);
  - the narrative assignment of one message to several fields (RF-3);
  - the clarification flag for an insufficient answer (no advance, RF-3);
  - the completeness check that triggers the summary (RF-6, G08);
  - the `Conversation` entity: states and the RNF-10 no-loss of captured
    fields (a field is set once and never re-captured).
"""

import pytest

from features.capture.domain import capture_rules as rules
from features.capture.domain.conversation import ChatMessage, Conversation

ALL_FIELDS: dict[str, str] = {
    "description": "Digitalizar la validación de proveedores.",
    "title": "Optimización del proceso de proveedores",
    "problem": "Tres revisiones manuales que duplican esfuerzo.",
    "expectedBenefit": "Ahorro de 120 horas mensuales.",
    "strategicAlignment": "Agilizar la cadena de suministro.",
    "proponent": "Ana Torres (Compras)",
}


def _conversation(prefill: dict[str, str] | None = None) -> Conversation:
    return rules.new_conversation(
        conversation_id="conv_1", user_id="u_ana", prefill=prefill
    )


# -- the RF-3 exact order -----------------------------------------------------


def test_field_order_is_the_spec_sequence() -> None:
    assert rules.FIELD_ORDER == (
        "description",
        "title",
        "problem",
        "expectedBenefit",
        "strategicAlignment",
        "proponent",
    )


def test_new_conversation_starts_at_the_first_field() -> None:
    conversation = _conversation()
    assert conversation.state == "ACTIVA"
    assert conversation.currentField == "description"
    assert conversation.order == rules.FIELD_ORDER


def test_next_pending_field_walks_the_order_skipping_captured() -> None:
    assert rules.next_pending_field(rules.FIELD_ORDER, {}) == "description"
    assert (
        rules.next_pending_field(rules.FIELD_ORDER, {"description": "x"}) == "title"
    )
    captured = dict(ALL_FIELDS)
    del captured["strategicAlignment"]
    assert rules.next_pending_field(rules.FIELD_ORDER, captured) == "strategicAlignment"
    assert rules.next_pending_field(rules.FIELD_ORDER, ALL_FIELDS) is None


def test_blank_field_is_not_captured() -> None:
    assert rules.next_pending_field(rules.FIELD_ORDER, {"description": "   "}) == "description"


# -- per-turn quick options (RF-5, D7 replacement) ----------------------------


def test_eligible_and_compactable_fields_cover_the_right_sets() -> None:
    # The free opening narrative and the title (RF-4 flow) never get chips.
    assert "description" not in rules.CHIP_ELIGIBLE_FIELDS
    assert "title" not in rules.CHIP_ELIGIBLE_FIELDS
    # The structured field and the title are never compacted.
    for field_name in ("title", "proponent"):
        assert field_name not in rules.COMPACTABLE_FIELDS
    # Every chip-eligible field is free-text and compactable, except the
    # structured proponent confirmation.
    assert {"problem", "expectedBenefit", "strategicAlignment"} <= rules.COMPACTABLE_FIELDS
    assert set(rules.FIELD_ORDER) >= rules.CHIP_ELIGIBLE_FIELDS


def test_build_question_offers_no_options_by_default() -> None:
    question = rules.build_question(current_field="problem")
    assert question["currentField"] == "problem"
    assert question["text"] == rules.QUESTION_BY_FIELD["problem"]
    assert question["quickOptions"] == []


def test_build_question_carries_the_options_offered_for_the_turn() -> None:
    options = ["Opción A", "Opción B"]
    question = rules.build_question(current_field="problem", quick_options=options)
    assert question["quickOptions"] == options


def test_every_asked_field_has_a_question() -> None:
    for field_name in rules.FIELD_ORDER:
        assert rules.QUESTION_BY_FIELD[field_name].strip()


# -- narrative assignment (RF-3) ----------------------------------------------


def test_narrative_assigns_several_fields_at_once() -> None:
    conversation = _conversation()
    extract = {
        "description": "Digitalizar la validación de proveedores.",
        "problem": "Tres revisiones manuales que duplican esfuerzo.",
    }
    apply = rules.apply_capture(conversation.capturedFields, extract, conversation.currentField)
    advance = rules.next_pending_field(conversation.order, conversation.capturedFields)
    assert apply is None
    assert advance == "title"  # description and problem were completed together
    # Both fields keep their text: no re-ask (RF-3), no loss.
    assert conversation.capturedFields["problem"] == extract["problem"]
    assert conversation.capturedFields["description"] == extract["description"]


def test_a_later_field_is_not_reasked() -> None:
    # `description` is captured, so `title` is in the course; a narrative that
    # also mentions `problem` fills it without re-asking (RF-3).
    conversation = _conversation(prefill={"description": "x", "problem": "El retroceso."})
    rules.apply_capture(conversation.capturedFields, {"title": "Mi título"}, "title")
    advance = rules.next_pending_field(conversation.order, conversation.capturedFields)
    assert advance == "expectedBenefit"


def test_existing_capture_is_never_overwritten_by_the_extraction() -> None:
    # `title` is in the course; the extraction only fills the missing fields
    # and never touches a captured one (RNF-10).
    conversation = _conversation(prefill={"description": "x", "problem": "El original"})
    rules.apply_capture(conversation.capturedFields, {"title": "T", "problem": "El repetido"}, "title")
    assert conversation.capturedFields["problem"] == "El original"
    assert conversation.capturedFields["title"] == "T"


def test_the_field_in_the_course_takes_the_new_value() -> None:
    conversation = _conversation()
    rules.apply_capture(
        conversation.capturedFields, {"description": "respuesta libre completa"}, "description"
    )
    assert conversation.capturedFields["description"] == "respuesta libre completa"


# -- clarification (RF-3) -----------------------------------------------------


def test_needs_clarification_when_a_fragment_is_insufficient() -> None:
    assert rules.needs_clarification({"description": rules.CLARIFY_FLAG})
    assert not rules.needs_clarification({"description": "un texto válido"})
    assert rules.needs_clarification({"description": "ok", "problem": rules.CLARIFY_FLAG})


def test_clarification_does_not_advance() -> None:
    conversation = _conversation()
    extract = {"description": rules.CLARIFY_FLAG}
    assert rules.needs_clarification(extract)
    # The UC keeps the fragment out of the conversation: the turn repeats.
    advance = rules.next_pending_field(conversation.order, conversation.capturedFields)
    assert advance == "description"


# -- completeness (RF-6 trigger) ----------------------------------------------


def test_is_complete_only_when_the_seven_fields_are_captured() -> None:
    incomplete = {name: value for name, value in ALL_FIELDS.items() if name != "title"}
    assert not rules.is_complete(rules.FIELD_ORDER, incomplete)
    assert rules.is_complete(rules.FIELD_ORDER, ALL_FIELDS)


# -- `Conversation` entity (states, RNF-10) -----------------------------------


def test_state_must_be_a_known_conversation_state() -> None:
    with pytest.raises(ValueError):
        Conversation(id="c", userId="u", state="OTRO_ESTADO")
    for state in ("ACTIVA", "RESUMEN", "TERMINADA", "CONTINGENCIA"):
        assert Conversation(id="c", userId="u", state=state).state == state


def test_conversation_requires_an_id_and_user() -> None:
    with pytest.raises(ValueError):
        Conversation(id="", userId="u")
    with pytest.raises(ValueError):
        Conversation(id="c", userId="")


def test_payload_round_trip_keeps_every_captured_field() -> None:
    conversation = _conversation()
    conversation.add_field("description", "Digitalizar los proveedores.")
    conversation.add_field("problem", "Tres revisiones manuales.")
    rebuilt = Conversation.from_payload(conversation.to_payload())
    assert rebuilt.capturedFields == conversation.capturedFields
    assert rebuilt.currentField == conversation.currentField
    assert rebuilt.order == conversation.order
    assert rebuilt.state == conversation.state


def test_add_field_never_overwrites_an_existing_capture() -> None:
    conversation = _conversation()
    conversation.add_field("description", "la primera")
    conversation.add_field("description", "la segunda")
    assert conversation.capturedFields["description"] == "la primera"


def test_set_field_replaces_a_prefilled_value() -> None:
    conversation = _conversation(prefill={"proponent": "Ana (Compras)"})
    conversation.set_field("proponent", "Ana T. (Compras, ana@x.local)")
    assert conversation.capturedFields["proponent"] == "Ana T. (Compras, ana@x.local)"


def test_has_field_requires_a_non_blank_value() -> None:
    conversation = _conversation()
    assert not conversation.has_field("description")
    conversation.set_field("description", "   ")
    assert not conversation.has_field("description")
    conversation.set_field("description", "un texto")
    assert conversation.has_field("description")


def test_structured_field_parses_json_back_to_its_object() -> None:
    conversation = _conversation()
    conversation.set_field(
        "proponent", '{"name": "Ana", "area": "Compras", "contact": "ana@x.local"}'
    )
    assert conversation.field_object("proponent") == {
        "name": "Ana",
        "area": "Compras",
        "contact": "ana@x.local",
    }


def test_structured_field_rejects_non_structured_keys() -> None:
    conversation = _conversation()
    with pytest.raises(ValueError):
        conversation.field_object("description")


def test_chat_message_requires_a_role_and_a_conversation() -> None:
    with pytest.raises(ValueError):
        ChatMessage(conversationId="c", role="machine")
    with pytest.raises(ValueError):
        ChatMessage(conversationId="", role="user")
