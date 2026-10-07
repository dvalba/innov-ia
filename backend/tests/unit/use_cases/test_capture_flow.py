"""Capture use-case flow tests (T-027/028/029, RF-2..RF-7).

Cover the use cases of the conversational engine:
  - `start_conversation` (T-027): resume the single ``ACTIVA`` (RF-2, case 8),
    start with greeting + first question + fixed chips (RF-2/RF-5), and the
    manual-form signal without the assistant (RF-7, case 1) — the proponent
    field is prefilled from the account (spec §5.2);
  - `process_message` (T-028): a free narrative may complete several fields at
    once and the completed ones are never re-asked (RF-3); a chip is the field's
    complete answer (RF-5); an insufficient answer triggers a clarification
    without advancing; skipping captures; completing the 7 -> ``RESUMEN`` (RF-6);
    an in-flight assistant failure surfaces the pre-filled manual fallback
    (RF-7, case 2, RNF-10);
  - `suggest_title` (T-029): a proactive title suggestion (RF-4), an "another"
    alternative distinct from the previous ones, and a manual text stored
    unmodified.
"""

from __future__ import annotations

import json

import pytest

from features.capture.domain import capture_rules as rules
from features.capture.infrastructure.conversation_store import ConversationStore
from features.capture.use_cases import activate_manual as manual_uc
from features.capture.use_cases import finish_capture as finish_uc
from features.capture.use_cases import process_message as msg_uc
from features.capture.use_cases import start_conversation as start_uc
from features.capture.use_cases import suggest_title as title_uc
from features.ideas.infrastructure.idea_store import IdeaStore
from shared.exceptions.handlers import AssistantUnavailable, DomainError, ValidationFailed
from tests.conftest import InMemoryDirectory, InMemoryStore, OllamaMock

PROPOSER = "u_ana"


def _directory() -> InMemoryDirectory:
    directory = InMemoryDirectory()
    directory.create(
        {
            "id": PROPOSER,
            "username": "ana",
            "name": "Ana Torres",
            "area": "Compras",
            "contact": "ana@corp.com",
            "roles": ["proponente"],
            "active": True,
            "shouldChangePassword": False,
        }
    )
    return directory


def _store() -> ConversationStore:
    return ConversationStore(InMemoryStore())


class _Extractor:
    """Programmable assistant for the extraction/titling turns.

    `extract` is the mapping returned by the extraction prompt; `title` the
    suggestion returned by the title prompt. Both can be re-programmed per step
    so one instance can drive a whole conversation in a test.
    """

    def __init__(self, extract: dict | None = None, title: str = "Título sugerido", available: bool = True):
        self.extract: dict = extract if extract is not None else {}
        self.title = title
        self.available = available
        self.prompts: list[str] = []

    def ping(self) -> bool:
        return self.available

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if "JSON esperado: {\"title" in prompt:  # the title-suggestion prompt
            return json.dumps({"title": self.title}, ensure_ascii=False)
        if "Campos pendientes" in prompt:  # the extraction prompt
            return json.dumps(self.extract, ensure_ascii=False)
        return json.dumps({}, ensure_ascii=False)


def _assistant_for(
    captured: dict[str, str],
) -> _Extractor:
    """An extractor that returns the given captured fields for whatever is asked."""
    return _Extractor(extract={k: v for k, v in captured.items()})


# ---------------------------------------------------------------------------
# T-027: start / resume
# ---------------------------------------------------------------------------


def test_start_without_assistant_returns_the_manual_signal() -> None:
    store = _store()
    assistant = OllamaMock(available=False)
    result = start_uc.start_conversation(store, assistant, _directory(), user_id=PROPOSER)
    assert result["mode"] == "manual"
    assert result["resumed"] is False
    assert result["conversation"] is None
    assert result["assistant"] is None
    # No orphan conversation is persisted (RF-7, case 1).
    assert store.list() == []
    # The prefilled proponent travels with the manual form (RNF-10, §5.2).
    proponent = json.loads(result["manual"]["capturedFields"]["proponent"])
    assert proponent["name"] == "Ana Torres"


def test_start_with_assistant_creates_and_greets_field_one() -> None:
    store = _store()
    result = start_uc.start_conversation(store, OllamaMock(), _directory(), user_id=PROPOSER)
    assert result["mode"] == "assistant"
    assert result["resumed"] is False
    payload = result["conversation"]
    assert payload["state"] == "ACTIVA"
    assert payload["userId"] == PROPOSER
    # The proponent field is prefilled from the account (spec §5.2): not asked
    # freely, confirmed/corrected in the summary (G08).
    assert "proponent" in payload["capturedFields"]
    # The first question is `description` (RF-3 order) with its fixed chips (RF-5).
    turn = result["assistant"]
    assert turn["currentField"] == "description"
    assert rules.GREETING_TEXT in turn["text"]
    assert turn["quickOptions"] == list(rules.CHIPS_BY_FIELD["description"])


def test_start_resumes_an_existing_active_conversation() -> None:
    store = _store()
    first = start_uc.start_conversation(store, OllamaMock(), _directory(), user_id=PROPOSER)
    first_id = first["conversation"]["id"]
    # Answer the first field to move the turn forward, so the resume is visible.
    _answer_field(store, first_id, "description", "Una idea cualquiera.")
    second = start_uc.start_conversation(store, OllamaMock(), _directory(), user_id=PROPOSER)
    assert second["resumed"] is True
    assert second["conversation"]["id"] == first_id
    assert second["conversation"]["currentField"] == "title"
    # Still exactly one conversation exists (RF-2, case 8).
    assert len(store.list()) == 1
    # A resumed turn has no greeting (the conversation is already open).
    assert rules.GREETING_TEXT not in second["assistant"]["text"]


def test_another_user_starts_his_own_conversation() -> None:
    store = _store()
    directory = _directory()
    directory.create({"id": "u_beto", "username": "beto", "name": "Beto", "roles": ["proponente"], "active": True})
    a = start_uc.start_conversation(store, OllamaMock(), directory, user_id="u_ana")
    b = start_uc.start_conversation(store, OllamaMock(), directory, user_id="u_beto")
    assert a["conversation"]["id"] != b["conversation"]["id"]
    assert len(store.list()) == 2


def _answer_field(store: ConversationStore, conversation_id: str, field: str, text: str) -> None:
    store.set_field(conversation_id, field, text)
    remaining = rules.next_pending_field(tuple(rules.FIELD_ORDER), store.get(conversation_id)["capturedFields"])
    store.set_current_field(conversation_id, remaining)


# ---------------------------------------------------------------------------
# Test helpers for the message-processing tests
# ---------------------------------------------------------------------------


def open_conv(extract=None, title="Título sugerido"):
    """Starts a real conversation and returns (store, conversation_id)."""
    store = _store()
    result = start_uc.start_conversation(store, _Extractor(extract=extract, title=title), _directory(), user_id=PROPOSER)
    assert result["mode"] == "assistant"
    return store, result["conversation"]["id"]


def _captured(captured: dict[str, str], current: str) -> tuple[ConversationStore, str]:
    """A persisted conversation whose given fields are captured, turn on `current`.

    `current` is always the next unfilled field for the given `captured` set, so
    the test data stays consistent with the RF-3 order.
    """
    store = _store()
    conv = rules.new_conversation(conversation_id="c_t", user_id=PROPOSER)
    conv.capturedFields = dict(captured)
    conv.currentField = current
    store.create(conv)
    return store, "c_t"


# ---------------------------------------------------------------------------
# T-028: process_message
# ---------------------------------------------------------------------------


def test_narrative_assigns_few_fields_and_moves_to_the_title_turn() -> None:
    store, cid = open_conv()
    assistant = _Extractor(
        extract={
            "description": "Reducir los tiempos de compra con un flujo digital.",
            "problem": "Retrasos en la operación actual",
        }
    )
    result = msg_uc.process_message(
        store, assistant, conversation_id=cid, user_id=PROPOSER,
        message="Quisiera reducir los tiempos de compra con un flujo digital; hay retrasos.",
    )
    # Both fragments were assigned; `problem` (not in course) was captured and
    # will never be re-asked (RF-3).
    payload = store.get(cid)
    assert payload["capturedFields"]["description"].startswith("Reducir los tiempos")
    assert payload["capturedFields"]["problem"] == "Retrasos en la operación actual"
    # The turn lands on `title` and carries the first suggestion (RF-4).
    turn = result["assistant"]
    assert turn["currentField"] == "title"
    assert turn["titleSuggestion"]["text"] == "Título sugerido"
    assert set(turn["titleSuggestion"]["actions"]) == {"accept", "another", "manual"}
    # The next pending field is `problem`... no: `problem` was captured, so the
    # order continues after the title (no re-asking of the captured field, RF-3).
    assert store.get(cid)["currentField"] == "title"


def test_a_chip_is_the_complete_answer_of_the_field() -> None:
    store, cid = _captured({"description": "d", "title": "t"}, "problem")
    assistant = _Extractor()
    chip = list(rules.CHIPS_BY_FIELD["problem"])[0]
    result = msg_uc.process_message(
        store, assistant, conversation_id=cid, user_id=PROPOSER, quick_option=chip
    )
    # The chip text IS the field's value, verbatim (RF-5).
    assert store.get(cid)["capturedFields"]["problem"] == chip
    # The next question is `expectedBenefit` with its fixed chips; the IA was
    # not needed for a chip turn.
    turn = result["assistant"]
    assert turn["currentField"] == "expectedBenefit"
    assert turn["quickOptions"] == list(rules.CHIPS_BY_FIELD["expectedBenefit"])
    assert assistant.prompts == []


def test_a_chip_that_does_not_match_the_field_is_not_accepted() -> None:
    store, cid = _captured({"description": "d", "title": "t"}, "problem")
    with pytest.raises(DomainError) as error:
        msg_uc.process_message(
            store, _Extractor(), conversation_id=cid, user_id=PROPOSER,
            quick_option=list(rules.CHIPS_BY_FIELD["expectedBenefit"])[0],
        )
    assert error.value.status_code == 400
    assert store.get(cid)["capturedFields"].get("problem") is None


def test_an_insufficient_answer_triggers_clarification_without_advancing() -> None:
    store, cid = _captured({}, "description")
    assistant = _Extractor(extract={"description": rules.CLARIFY_FLAG})
    result = msg_uc.process_message(
        store, assistant, conversation_id=cid, user_id=PROPOSER, message="mmm"
    )
    assert result["assistant"]["needsClarification"] is True
    assert result["assistant"]["currentField"] == "description"
    # The marker is never stored as a captured value (RNF-10, RF-3).
    assert store.get(cid)["capturedFields"] == {}
    assert store.get(cid)["currentField"] == "description"
    assert store.get(cid)["state"] == "ACTIVA"


def test_seven_fields_close_the_conversation_into_the_summary() -> None:
    store, cid = _captured(
        {
            "description": "d",
            "title": "t",
            "problem": "p",
            "expectedBenefit": "b",
            "strategicAlignment": "s",
            "estimatedResources": "r",
        },
        "proponent",
    )
    assistant = _Extractor(extract={"proponent": "Ana Torres (Compras), ana@x.com"})
    result = msg_uc.process_message(
        store, assistant, conversation_id=cid, user_id=PROPOSER,
        message="Soy Ana Torres de Compras, ana@x.com",
    )
    assert result["state"] == "RESUMEN"
    assert store.get(cid)["state"] == "RESUMEN"
    summary = result["summary"]
    assert len(summary) == 7
    assert summary["title"] == "t"
    assert summary["proponent"] == "Ana Torres (Compras), ana@x.com"
    # A further message in RESUMEN only re-shows the editable summary (RF-6).
    again = msg_uc.process_message(
        store, _Extractor(), conversation_id=cid, user_id=PROPOSER, message="ok"
    )
    assert again["state"] == "RESUMEN"


def test_a_mid_conversation_ia_failure_falls_back_to_the_manual_form() -> None:
    store, cid = _captured({"description": "lo capturado"}, "title")
    with pytest.raises(AssistantUnavailable) as error:
        msg_uc.process_message(
            store, OllamaMock(available=False), conversation_id=cid, user_id=PROPOSER,
            message="mi idea",
        )
    # 503 with the captured fields: the client pre-fills the manual form
    # (RF-7 case 2, RNF-10: nothing is lost, nothing is dropped).
    assert error.value.code == "ASSISTANT_UNAVAILABLE"
    assert error.value.fallback["capturedFields"]["description"] == "lo capturado"
    assert store.get(cid)["state"] == "CONTINGENCIA"
    # The conversation stays unusable by chat until activated (G08 handles it).
    with pytest.raises(AssistantUnavailable):
        msg_uc.process_message(
            store, OllamaMock(available=True), conversation_id=cid, user_id=PROPOSER,
            message="otra vez",
        )


def test_an_uninterpretable_reply_also_falls_back() -> None:
    store, cid = _captured({}, "description")
    assistant = OllamaMock(available=True)
    assistant.respond = lambda prompt: "esto no es JSON"
    with pytest.raises(AssistantUnavailable) as error:
        msg_uc.process_message(
            store, assistant, conversation_id=cid, user_id=PROPOSER, message="mi idea"
        )
    assert error.value.code == "ASSISTANT_UNAVAILABLE"
    assert store.get(cid)["state"] == "CONTINGENCIA"


def test_an_empty_message_is_rejected() -> None:
    store, cid = open_conv()
    with pytest.raises(DomainError) as error:
        msg_uc.process_message(
            store, _Extractor(), conversation_id=cid, user_id=PROPOSER
        )
    assert error.value.status_code == 400


def test_only_the_owner_can_message_a_conversation() -> None:
    store, cid = open_conv()
    with pytest.raises(DomainError) as error:
        msg_uc.process_message(
            store, _Extractor(), conversation_id=cid, user_id="u_otro", message="hola"
        )
    assert error.value.status_code == 403


# ---------------------------------------------------------------------------
# T-029: suggest_title
# ---------------------------------------------------------------------------


def test_another_generates_a_distinct_suggestion_and_keeps_the_turn() -> None:
    store, cid = open_conv()
    assistant = _Extractor(extract={"description": "Reducir costes."}, title="Título A")
    first = msg_uc.process_message(
        store, assistant, conversation_id=cid, user_id=PROPOSER, message="mi texto"
    )
    assert first["assistant"]["titleSuggestion"]["text"] == "Título A"
    assistant.title = "Título B"  # the model is asked again for a different one
    second = title_uc.suggest_title(
        store, assistant, conversation_id=cid, user_id=PROPOSER, action="another"
    )
    assert second["state"] == "ACTIVA"
    assert second["assistant"]["currentField"] == "title"
    assert second["assistant"]["titleSuggestion"]["text"] == "Título B"
    # Both attempts are persisted (the loop remembers them, RF-4).
    assert store.get(cid)["titleSuggestions"] == ["Título A", "Título B"]


def test_an_other_when_the_model_repeats_is_bounded() -> None:
    from features.capture.use_cases.suggest_title import MAX_TITLE_ATTEMPTS

    store, cid = open_conv()
    assistant = _Extractor(extract={"description": "Reducir costes."}, title="Mismo")
    msg_uc.process_message(
        store, assistant, conversation_id=cid, user_id=PROPOSER, message="mi texto"
    )
    before = len(assistant.prompts)
    # The model stubbornly repeats the same candidate: the "another" action
    # must stop after a bounded number of retries (no infinite loop, RF-4).
    result = title_uc.suggest_title(
        store, assistant, conversation_id=cid, user_id=PROPOSER, action="another"
    )
    assert result["assistant"]["titleSuggestion"] is not None
    assert len(assistant.prompts) - before <= MAX_TITLE_ATTEMPTS


def test_accept_stores_the_last_suggestion_and_advances() -> None:
    store, cid = open_conv()
    assistant = _Extractor(extract={"description": "Reducir costes."}, title="Título A")
    msg_uc.process_message(
        store, assistant, conversation_id=cid, user_id=PROPOSER, message="mi texto"
    )
    result = title_uc.suggest_title(
        store, assistant, conversation_id=cid, user_id=PROPOSER, action="accept"
    )
    # The suggested title is stored as-is and the turn moves on (RF-3 order).
    assert store.get(cid)["capturedFields"]["title"] == "Título A"
    assert result["assistant"]["currentField"] == "problem"
    assert result["assistant"]["quickOptions"] == list(rules.CHIPS_BY_FIELD["problem"])


def test_manual_title_is_stored_unmodified_and_advances() -> None:
    store, cid = open_conv()
    assistant = _Extractor(extract={"description": "Reducir costes."}, title="Título A")
    msg_uc.process_message(
        store, assistant, conversation_id=cid, user_id=PROPOSER, message="mi texto"
    )
    result = title_uc.suggest_title(
        store, assistant, conversation_id=cid, user_id=PROPOSER,
        action="manual", manual_text="Mi idea de títulos con mayúsculas.",
    )
    # RF-4: the user's text is used unmodified.
    assert store.get(cid)["capturedFields"]["title"] == "Mi idea de títulos con mayúsculas."
    assert result["assistant"]["currentField"] == "problem"


def test_an_accept_without_a_suggestion_is_rejected() -> None:
    store, cid = _captured({"description": "d"}, "title")
    store.set_title_suggestions(cid, [])
    with pytest.raises(DomainError) as error:
        title_uc.suggest_title(
            store, _Extractor(), conversation_id=cid, user_id=PROPOSER, action="accept"
        )
    assert error.value.status_code == 409


def test_title_actions_require_the_title_turn_an_active_conversation() -> None:
    store, cid = _captured({}, "description")
    with pytest.raises(DomainError) as error:
        title_uc.suggest_title(
            store, _Extractor(), conversation_id=cid, user_id=PROPOSER,
            action="manual", manual_text="T",
        )
    assert error.value.status_code == 409  # the turn is on `description`
    with pytest.raises(DomainError) as error:
        title_uc.suggest_title(
            store, _Extractor(), conversation_id=cid, user_id="u_otro",
            action="accept",
        )
    assert error.value.status_code == 403


# ---------------------------------------------------------------------------
# T-030: finish_capture + activate_manual
# ---------------------------------------------------------------------------


def _ledger() -> IdeaStore:
    return IdeaStore(InMemoryStore(), InMemoryStore())


def _proponent_json(**overrides: str) -> str:
    data = {"name": "Ana Torres", "area": "Compras", "contact": "ana@corp.com", **overrides}
    return json.dumps(data, ensure_ascii=False)


def _resumen(
    captured: dict[str, str],
    state: str = "RESUMEN",
) -> tuple[ConversationStore, str]:
    """A conversation with the given captured fields in `state` (default RESUMEN)."""
    store = _store()
    conv = rules.new_conversation(conversation_id="c_f", user_id=PROPOSER)
    conv.capturedFields = dict(captured)
    conv.currentField = None
    conv.state = state
    store.create(conv)
    return store, "c_f"


def _complete_summary(**overrides: str) -> dict:
    """The 7 fields complete: texts + the two structured fields as JSON strings."""
    summary = {
        "description": "Reducir los tiempos de compra con un flujo digital.",
        "title": "Flujo digital de compras",
        "problem": "Retrasos en la operación de compras.",
        "expectedBenefit": "Comprar antes y a mejor precio.",
        "strategicAlignment": "Eficiencia operativa y ahorro.",
        "estimatedResources": json.dumps(
            {"time": "3 meses", "people": "2", "budget": "100000"}, ensure_ascii=False
        ),
        "proponent": _proponent_json(**overrides),
    }
    return summary


def test_finish_registers_the_idea_and_closes_the_conversation() -> None:
    store, cid = _resumen(_complete_summary())
    ledger = _ledger()
    result = finish_uc.finish_capture(
        store, ledger, conversation_id=cid, user_id=PROPOSER, captured={}
    )
    # The idea is created in EN_DESARROLLO with origin asistida (RF-6), the
    # structured fields parsed back into their objects (plan §2.2, RNF-5).
    assert result["id"].startswith("idea_")
    assert result["state"] == "EN_DESARROLLO"
    assert result["origin"] == "asistida"
    assert result["ownerId"] == PROPOSER
    assert result["proponent"]["name"] == "Ana Torres"
    assert result["estimatedResources"]["budget"] == "100000"
    assert result["conversationId"] == cid
    # The conversation is closed as TERMINADA (one per user, RF-2).
    assert store.get(cid)["state"] == "TERMINADA"
    assert [p["id"] for p in ledger.list_by_origin("asistida", "EN_DESARROLLO")] == [result["id"]]


def test_finish_with_a_missing_field_rejects_and_keeps_the_summary() -> None:
    summary = _complete_summary()
    del summary["title"]
    store, cid = _resumen(summary)
    ledger = _ledger()
    # The stored summary is itself incomplete: without a confirmed payload the
    # finish is a ValidationFailed (422) and nothing is registered (RNF-5).
    with pytest.raises(ValidationFailed) as error:
        finish_uc.finish_capture(
            store, ledger, conversation_id=cid, user_id=PROPOSER, captured={}
        )
    assert "title" in error.value.details["fields"]
    assert ledger.list() == []
    assert store.get(cid)["state"] == "RESUMEN"


def test_a_malformed_contact_rejects_the_finish() -> None:
    store, cid = _resumen(_complete_summary())
    ledger = _ledger()
    # The proponent contact is part of RNF-5 (case 12): an empty contact
    # blocks the registration even though the 7 fields are present.
    with pytest.raises(ValidationFailed) as error:
        finish_uc.finish_capture(
            store,
            ledger,
            conversation_id=cid,
            user_id=PROPOSER,
            captured={"proponent": _proponent_json(contact="")},
        )
    assert "proponent" in error.value.details["fields"]
    assert ledger.list() == []
    assert store.get(cid)["state"] == "RESUMEN"


def test_the_confirmed_summary_wins_over_the_stored_values() -> None:
    store, cid = _resumen(_complete_summary(title="Título original"))
    ledger = _ledger()
    result = finish_uc.finish_capture(
        store, ledger, conversation_id=cid, user_id=PROPOSER,
        captured={"title": "Título corregido por el proponente"},
    )
    # The confirmed (edited) value overrides the capture (the summary is editable).
    assert result["title"] == "Título corregido por el proponente"
    # The rest of the summary is kept untouched.
    assert result["description"] == _complete_summary()["description"]


def test_finish_from_any_other_state_is_refused_and_leaves_nothing() -> None:
    """Case 7: without a confirmed summary (state != RESUMEN), even a perfect
    payload registers no idea and changes nothing."""
    for state in ("ACTIVA", "TERMINADA", "CONTINGENCIA"):
        store, cid = _resumen(_complete_summary(), state=state)
        ledger = _ledger()
        with pytest.raises(DomainError) as error:
            finish_uc.finish_capture(
                store, ledger, conversation_id=cid, user_id=PROPOSER,
                captured=_complete_summary(),
            )
        assert error.value.status_code == 409
        assert ledger.list() == []  # no draft, no partial record
        assert store.get(cid)["state"] == state


def test_no_draft_saved_when_no_finish_happens() -> None:
    """Case 7 (no draft): abandoning the capture before confirming leaves no
    idea and the conversation exactly as it was."""
    store, cid = _resumen(_complete_summary())
    ledger = _ledger()
    # No finish call at all: the ledger stays empty.
    assert ledger.list() == []
    assert store.get(cid)["state"] == "RESUMEN"
    # And a conversation still in flight (ACTIVA) is equally untouchable.
    store2, cid2 = _resumen({"description": "d", "title": "t"}, state="ACTIVA")
    store2.set_current_field(cid2, "problem")
    with pytest.raises(DomainError) as error:
        finish_uc.finish_capture(
            store2, _ledger(), conversation_id=cid2, user_id=PROPOSER,
            captured=_complete_summary(),
        )
    assert error.value.status_code == 409
    assert store2.get(cid2)["state"] == "ACTIVA"


def test_finish_requires_the_conversation_to_exist_and_be_owned() -> None:
    ledger = _ledger()
    with pytest.raises(DomainError) as error:
        finish_uc.finish_capture(
            _store(), ledger, conversation_id="c_inexistente", user_id=PROPOSER
        )
    assert error.value.status_code == 404
    store, cid = _resumen(_complete_summary())
    with pytest.raises(DomainError) as error:
        finish_uc.finish_capture(
            store, ledger, conversation_id=cid, user_id="u_otro"
        )
    assert error.value.status_code == 403
    assert store.get(cid)["state"] == "RESUMEN"


def test_finish_from_contingency_rejects_even_a_complete_payload() -> None:
    # A contingency conversation never confirmed its summary: the only path
    # forward for its data is the manual form (RF-7), not the assisted finish.
    store, cid = _resumen(_complete_summary(), state="CONTINGENCIA")
    with pytest.raises(DomainError) as error:
        finish_uc.finish_capture(
            store, _ledger(), conversation_id=cid, user_id=PROPOSER,
            captured=_complete_summary(),
        )
    assert error.value.status_code == 409


# -- activate_manual ---------------------------------------------------------


def test_activate_manual_from_active_marks_contingency_and_prefills() -> None:
    store, cid = _captured({"description": "lo capturado"}, "title")
    result = manual_uc.activate_manual(store, conversation_id=cid, user_id=PROPOSER)
    assert result["state"] == "CONTINGENCIA"
    # The captured fields travel raw (RNF-10: nothing lost) so the manual form
    # pre-fills with what the user already said.
    assert result["capturedFields"]["description"] == "lo capturado"
    assert store.get(cid)["state"] == "CONTINGENCIA"


def test_activate_manual_from_resumen_marks_contingency() -> None:
    store, cid = _resumen(_complete_summary())
    result = manual_uc.activate_manual(store, conversation_id=cid, user_id=PROPOSER)
    assert result["state"] == "CONTINGENCIA"
    assert result["capturedFields"]["title"] == _complete_summary()["title"]
    assert store.get(cid)["state"] == "CONTINGENCIA"


def test_activate_manual_is_idempotent_when_already_contingency() -> None:
    store, cid = _resumen(_complete_summary(), state="CONTINGENCIA")
    before = store.get(cid)
    result = manual_uc.activate_manual(store, conversation_id=cid, user_id=PROPOSER)
    assert result["state"] == "CONTINGENCIA"
    assert result["capturedFields"] == before["capturedFields"]
    assert store.get(cid) == before  # nothing rewritten


def test_activate_manual_requires_an_unfinished_owned_conversation() -> None:
    store, cid = _resumen(_complete_summary(), state="TERMINADA")
    with pytest.raises(DomainError) as error:
        manual_uc.activate_manual(store, conversation_id=cid, user_id=PROPOSER)
    assert error.value.status_code == 409  # the idea was already registered
    with pytest.raises(DomainError) as error:
        manual_uc.activate_manual(store, conversation_id="c_inexistente", user_id=PROPOSER)
    assert error.value.status_code == 404
    with pytest.raises(DomainError) as error:
        manual_uc.activate_manual(store, conversation_id=cid, user_id="u_otro")
    assert error.value.status_code == 403
    assert store.get(cid)["state"] == "TERMINADA"


def test_partial_fields_are_kept_when_activating_manual() -> None:
    partial = {
        "description": "una idea a medias",
        "problem": "retrasos",
        "proponent": _proponent_json(),
    }
    store, cid = _captured(partial, "title")
    result = manual_uc.activate_manual(store, conversation_id=cid, user_id=PROPOSER)
    # The partial capture is pre-filled as stored: structured fields are the
    # JSON strings, exactly like the 503 fallback (RNF-10).
    assert set(result["capturedFields"]) == set(partial)
    assert result["capturedFields"]["proponent"] == partial["proponent"]
    assert store.get(cid)["capturedFields"] == partial
