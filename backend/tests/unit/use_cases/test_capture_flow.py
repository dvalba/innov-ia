"""Capture use-case flow tests (T-027/028/029, RF-2..RF-7).

Cover the use cases of the conversational engine:
   - `start_conversation` (T-027/T-087): resume the single ``ACTIVA`` (RF-2,
     case 8) — with priority over the ``RESUMEN`` ones (v2.3), which are
     resumed with their editable summary (RF-2/RF-6) —, start with greeting +
     first question (RF-2/RF-5), and the manual-form signal without the
     assistant (RF-7, case 1) — the proponent field is prefilled from the
     account (spec §5.2);
  - `process_message` (T-028): a free narrative may complete several fields at
    once and the completed ones are never re-asked (RF-3); a chip is the
    field's complete answer and is only valid when it was offered on the turn
    (RF-5, D7: the assistant generates the per-turn options); an insufficient
    answer triggers a clarification
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

from features.assistant.domain.prompts import FIELD_LABELS
from features.capture.domain import capture_rules as rules
from features.capture.infrastructure.conversation_store import ConversationStore
from features.capture.use_cases import abandon_conversation as abandon_uc
from features.capture.use_cases import activate_manual as manual_uc
from features.capture.use_cases import finish_capture as finish_uc
from features.capture.use_cases import process_message as msg_uc
from features.capture.use_cases import start_conversation as start_uc
from features.capture.use_cases import suggest_title as title_uc
from features.ideas.infrastructure.idea_store import IdeaStore
from shared.exceptions.handlers import AssistantUnavailable, DomainError, ValidationFailed
from tests.conftest import (
    InMemoryDirectory,
    InMemoryStore,
    OllamaMock,
    options_for_label,
    turn_options_json,
)

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
    suggestion returned by the title prompt; `compact` the free-text
    recompaction returned by the per-turn options prompt. All can be
    re-programmed per step so one instance can drive a whole conversation in
    a test. The turn-options prompt is answered with deterministic, label-keyed
    options (see `tests.conftest.turn_options_json`) so chips stay predictable.
    """

    def __init__(
        self,
        extract: dict | None = None,
        title: str = "Título sugerido",
        available: bool = True,
        compact: dict | None = None,
    ):
        self.extract: dict = extract if extract is not None else {}
        self.title = title
        self.available = available
        self.compact: dict = compact if compact is not None else {}
        self.prompts: list[str] = []

    def ping(self) -> bool:
        return self.available

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if 'JSON esperado: {"options' in prompt:  # the per-turn options prompt
            return turn_options_json(prompt, compact=self.compact)
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
    # The first question is `description` (RF-3 order); the opening turn offers
    # no chips — the field is a free narrative (RF-5, D7: chips are generated
    # per turn by the assistant, and only for chip-eligible fields on landing).
    turn = result["assistant"]
    assert turn["currentField"] == "description"
    assert rules.GREETING_TEXT in turn["text"]
    assert turn["quickOptions"] == []


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
    the test data stays consistent with the RF-3 order. The turn also records
    the per-turn options offered while pointing at `current` (D7 replacement):
    a chip is only valid against the options actually offered for the field in
    the course, and chip-eligible fields get the mock's deterministic options.
    """
    store = _store()
    conv = rules.new_conversation(conversation_id="c_t", user_id=PROPOSER)
    conv.capturedFields = dict(captured)
    conv.currentField = current
    if current in rules.CHIP_ELIGIBLE_FIELDS:
        conv.offeredField = current
        conv.offeredOptions = options_for_label(FIELD_LABELS[current])
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
    chip = options_for_label(FIELD_LABELS["problem"])[0]  # offered on the turn
    result = msg_uc.process_message(
        store, assistant, conversation_id=cid, user_id=PROPOSER, quick_option=chip
    )
    # The chip text IS the field's value, verbatim (RF-5).
    assert store.get(cid)["capturedFields"]["problem"] == chip
    # The next question is `expectedBenefit` with the options the assistant
    # generated for it on landing (RF-5, D7 replacement).
    turn = result["assistant"]
    assert turn["currentField"] == "expectedBenefit"
    assert turn["quickOptions"] == options_for_label(FIELD_LABELS["expectedBenefit"])
    # The chip itself needs no IA call; the ONE call is the landing options.
    assert len(assistant.prompts) == 1
    assert 'JSON esperado: {"options' in assistant.prompts[0]


def test_a_chip_that_does_not_match_the_field_is_not_accepted() -> None:
    store, cid = _captured({"description": "d", "title": "t"}, "problem")
    with pytest.raises(DomainError) as error:
        # A well-formed option, but not one offered for the field in the course:
        # only actually-offered options are valid (RF-5, D7 replacement).
        msg_uc.process_message(
            store, _Extractor(), conversation_id=cid, user_id=PROPOSER,
            quick_option=options_for_label(FIELD_LABELS["expectedBenefit"])[0],
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


def test_an_unusable_narrative_is_a_clarification_with_a_manual_escape() -> None:
    """A narrative from which the assistant captures nothing re-asks the field
    as a clarification (`needsClarification`, RF-3) so the client can offer the
    manual-form escape (RF-7, RNF-10) instead of an endless loop."""
    store, cid = _captured({}, "description")
    assistant = _Extractor(extract={})  # no field captured at all
    result = msg_uc.process_message(
        store, assistant, conversation_id=cid, user_id=PROPOSER, message="mmm"
    )
    assert result["assistant"]["needsClarification"] is True
    assert result["assistant"]["currentField"] == "description"
    # Nothing is persisted and the conversation stays in flight (no advance).
    assert store.get(cid)["capturedFields"] == {}
    assert store.get(cid)["state"] == "ACTIVA"


def test_six_fields_close_the_conversation_into_the_summary() -> None:
    store, cid = _captured(
        {
            "description": "d",
            "title": "t",
            "problem": "p",
            "expectedBenefit": "b",
            "strategicAlignment": "s",
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
    assert len(summary) == 6
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


def test_a_message_to_a_legacy_v2_conversation_keeps_working() -> None:
    """The production 500 (RF-6, 6 campos): a conversation persisted under the
    old 7-field capture still carries `estimatedResources` in `order`; a new
    message used to crash in the extraction prompt (KeyError on the removed
    field's label). The rebuild migrates the record silently (D11) so the
    field is skipped and the conversation keeps running to the summary."""
    from features.capture.domain.conversation import Conversation

    legacy = Conversation(
        id="c_legacy",
        userId=PROPOSER,
        order=(
            "description",
            "title",
            "problem",
            "estimatedResources",
            "expectedBenefit",
            "strategicAlignment",
            "proponent",
        ),
    )
    legacy.capturedFields = {
        "description": "Digitalizar la validación de proveedores.",
        "title": "Optimización del proceso de proveedores",
        "estimatedResources": "2 desarrolladores y 3 sprints.",
        "proponent": _proponent_json(),
    }
    legacy.currentField = "estimatedResources"  # the turn was on the removed field
    store = _store()
    store.create(legacy)

    assistant = _Extractor(
        extract={
            "problem": "Tres revisiones manuales que duplican esfuerzo.",
            "expectedBenefit": "Ahorro de 120 horas mensuales.",
        }
    )
    # Without the migration this raises KeyError → HTTP 500 (prompts.py).
    result = msg_uc.process_message(
        store, assistant, conversation_id="c_legacy", user_id=PROPOSER,
        message="El problema son las revisiones manuales; ahorraremos 120 horas al mes.",
    )
    assert result["state"] == "ACTIVA"
    # The removed field never reaches the assistant (neither asked nor labelled).
    for prompt in assistant.prompts:
        assert "estimatedResources" not in prompt
        assert "Recursos" not in prompt
    # The turn advanced to the next real pending field.
    assert result["assistant"]["currentField"] == "strategicAlignment"
    # The migration persists: the stored order is the 6-field one.
    stored = store.get("c_legacy")
    assert "estimatedResources" not in stored["order"]
    assert stored["currentField"] == "strategicAlignment"


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
    # The suggested title is stored as-is and the turn moves on (RF-3 order),
    # carrying the options the assistant generated for `problem` on landing.
    assert store.get(cid)["capturedFields"]["title"] == "Título A"
    assert result["assistant"]["currentField"] == "problem"
    assert result["assistant"]["quickOptions"] == options_for_label(FIELD_LABELS["problem"])


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
    """The 6 fields complete: texts + the structured field as a JSON string."""
    summary = {
        "description": "Reducir los tiempos de compra con un flujo digital.",
        "title": "Flujo digital de compras",
        "problem": "Retrasos en la operación de compras.",
        "expectedBenefit": "Comprar antes y a mejor precio.",
        "strategicAlignment": "Eficiencia operativa y ahorro.",
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


# ---------------------------------------------------------------------------
# T-087 (v2.3): RESUMEN resume + explicit abandonment
# ---------------------------------------------------------------------------


def test_start_resumes_a_summary_conversation_with_its_summary() -> None:
    """v2.3: without an ACTIVA, `start` resumes the RESUMEN with its editable
    summary — the captured fields are never lost (RF-2/RF-6, decision D22)."""
    store, cid = _resumen(_complete_summary())
    result = start_uc.start_conversation(store, OllamaMock(), _directory(), user_id=PROPOSER)
    assert result["mode"] == "assistant"
    assert result["resumed"] is True
    assert result["conversation"]["id"] == cid
    assert result["state"] == "RESUMEN"
    # No new turn is started: the client deploys the editable summary directly.
    assert result["assistant"] is None
    assert result["manual"] is None
    # The summary is the editable one (RF-6): the structured field is parsed
    # back into its object, the rest kept as text (plan §2.2).
    summary = result["summary"]
    assert summary["title"] == _complete_summary()["title"]
    assert isinstance(summary["proponent"], dict)
    assert summary["proponent"]["name"] == "Ana Torres"
    # No conversation is created: the RESUMEN is the one resumed.
    assert [p["id"] for p in store.list()] == [cid]


def test_start_prefers_active_over_summary() -> None:
    """v2.3: an ACTIVA conversation always wins the resume (case 8); the
    RESUMEN stays untouched for later."""
    store = _store()
    active = rules.new_conversation(conversation_id="c_act", user_id=PROPOSER)
    active.capturedFields = {"description": "lo capturado"}
    active.currentField = "title"
    store.create(active)
    resumen = rules.new_conversation(conversation_id="c_res", user_id=PROPOSER)
    resumen.capturedFields = dict(_complete_summary())
    resumen.currentField = None
    resumen.state = "RESUMEN"
    store.create(resumen)
    active_id, resumen_id = "c_act", "c_res"
    result = start_uc.start_conversation(store, OllamaMock(), _directory(), user_id=PROPOSER)
    assert result["resumed"] is True
    assert result["conversation"]["id"] == active_id
    assert result["state"] == "ACTIVA"
    assert result["summary"] is None
    # The resume still shows the turn (the ACTIVA contract is invariant).
    assert result["assistant"]["currentField"] == "title"
    # The RESUMEN is not consumed by the resume.
    assert store.get(resumen_id)["state"] == "RESUMEN"
    # After the ACTIVA ends, the RESUMEN becomes the resume candidate.
    store.set_state(active_id, "TERMINADA", current_state="ACTIVA")
    second = start_uc.start_conversation(store, OllamaMock(), _directory(), user_id=PROPOSER)
    assert second["resumed"] is True
    assert second["conversation"]["id"] == resumen_id
    assert second["state"] == "RESUMEN"
    assert second["summary"]["title"] == _complete_summary()["title"]


def test_start_outcomes_carry_state_and_summary_fields() -> None:
    """v2.3: every start outcome carries coherent `state`/`summary` so the
    client can route (ACTIVA chat vs RESUMEN summary vs manual form)."""
    store = _store()
    result = start_uc.start_conversation(store, OllamaMock(), _directory(), user_id=PROPOSER)
    assert result["state"] == "ACTIVA"
    assert result["summary"] is None
    store2 = _store()
    result2 = start_uc.start_conversation(store2, OllamaMock(available=False), _directory(),
                                          user_id=PROPOSER)
    assert result2["mode"] == "manual"
    assert result2["state"] is None
    assert result2["summary"] is None


def test_abandon_from_active_finishes_the_conversation() -> None:
    """Case 7 (v2.3): abandoning an in-flight conversation ends it without
    saving anything and frees the one-conversation limit (RF-2)."""
    store, cid = _captured({"description": "lo capturado"}, "title")
    result = abandon_uc.abandon_conversation(store, conversation_id=cid, user_id=PROPOSER)
    assert result == {"conversationId": cid, "state": "TERMINADA"}
    assert store.get(cid)["state"] == "TERMINADA"
    # The limit is freed: a new capture can start (the guard no longer blocks).
    again = start_uc.start_conversation(store, OllamaMock(), _directory(), user_id=PROPOSER)
    assert again["resumed"] is False
    assert again["conversation"]["id"] != cid


def test_abandon_from_summary_finishes_the_conversation() -> None:
    store, cid = _resumen(_complete_summary())
    result = abandon_uc.abandon_conversation(store, conversation_id=cid, user_id=PROPOSER)
    assert result == {"conversationId": cid, "state": "TERMINADA"}
    assert store.get(cid)["state"] == "TERMINADA"
    # A TERMINADA conversation is never resumed by `start`.
    result2 = start_uc.start_conversation(store, OllamaMock(), _directory(), user_id=PROPOSER)
    assert result2["resumed"] is False
    assert result2["conversation"]["id"] != cid


def test_abandon_from_contingency_finishes_the_conversation() -> None:
    store, cid = _resumen(_complete_summary(), state="CONTINGENCIA")
    result = abandon_uc.abandon_conversation(store, conversation_id=cid, user_id=PROPOSER)
    assert result == {"conversationId": cid, "state": "TERMINADA"}
    assert store.get(cid)["state"] == "TERMINADA"


def test_abandon_of_a_finished_conversation_is_idempotent() -> None:
    """v2.3: abandoning a TERMINADA conversation is a no-op with the same
    outcome (it cannot be abandoned twice nor resurrected)."""
    store, cid = _resumen(_complete_summary(), state="TERMINADA")
    before = store.get(cid)
    result = abandon_uc.abandon_conversation(store, conversation_id=cid, user_id=PROPOSER)
    assert result == {"conversationId": cid, "state": "TERMINADA"}
    assert store.get(cid) == before  # nothing rewritten


def test_abandon_requires_ownership() -> None:
    store, cid = _captured({"description": "lo capturado"}, "title")
    with pytest.raises(DomainError) as error:
        abandon_uc.abandon_conversation(store, conversation_id=cid, user_id="u_otro")
    assert error.value.status_code == 403
    assert store.get(cid)["state"] == "ACTIVA"  # the foreign call changed nothing


def test_abandon_of_a_missing_conversation_404() -> None:
    store = _store()
    with pytest.raises(DomainError) as error:
        abandon_uc.abandon_conversation(store, conversation_id="c_inexistente", user_id=PROPOSER)
    assert error.value.status_code == 404
