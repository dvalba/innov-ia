"""Conversation store tests (T-026, RF-2/RF-7, RNF-10, RNF-9).

Covers the persistence guarantees of `ConversationStore`:
  - the one-``ACTIVA``-per-user rule (RF-2, case 8): a second active
    conversation for the same user is refused;
  - no loss of captured fields (RNF-10, RF-7): partial captures survive a
    re-read, a new field never drops the existing ones, and only an explicit
    `set_field` ever replaces a value;
  - compare-and-set state changes (RNF-9, case 11): the transition is applied
    only when the conversation is still in the expected state;
  - the title-suggestion list persists (RF-4, G07 "another" loop).
"""

import pathlib

import pytest

from features.capture.domain import capture_rules as rules
from features.capture.domain.conversation import Conversation
from features.capture.infrastructure.conversation_store import ConversationStore
from shared.exceptions.handlers import DomainError
from shared.utils.persistence import JsonStore


@pytest.fixture()
def store(tmp_path: pathlib.Path) -> ConversationStore:
    return ConversationStore(JsonStore(tmp_path / "conversations.json"))


def _reopened_store(tmp_path: pathlib.Path) -> ConversationStore:
    """A brand-new store over the same file: stands in for a re-read (RNF-10)."""
    return ConversationStore(JsonStore(tmp_path / "conversations.json"))


def new_active(
    conversation_id: str = "conv_1",
    user_id: str = "u_ana",
    prefill: dict[str, str] | None = None,
) -> Conversation:
    return rules.new_conversation(
        conversation_id=conversation_id, user_id=user_id, prefill=prefill
    )


def test_create_get_round_trip(store: ConversationStore) -> None:
    payload = store.create(new_active())
    assert payload["state"] == "ACTIVA"
    assert payload["currentField"] == "description"
    assert payload["capturedFields"] == {}
    assert payload["order"] == list(rules.FIELD_ORDER)
    assert store.get("conv_1") == payload
    assert store.get("conv_nadie") is None


def test_one_active_conversation_per_user(store: ConversationStore) -> None:
    store.create(new_active(user_id="u_ana"))
    with pytest.raises(DomainError) as error:
        store.create(new_active(conversation_id="conv_2", user_id="u_ana"))
    assert error.value.status_code == 409
    assert error.value.code == "ACTIVE_CONVERSATION_EXISTS"
    # A second user may start its own conversation (RF-2 limits per user).
    assert store.create(new_active(conversation_id="conv_3", user_id="u_beto"))["userId"] == "u_beto"


def test_a_terminated_conversation_does_not_block_a_new_one(store: ConversationStore) -> None:
    store.create(new_active(user_id="u_ana"))
    store.set_state("conv_1", "TERMINADA", current_state="ACTIVA")
    payload = store.create(new_active(conversation_id="conv_2", user_id="u_ana"))
    assert payload["state"] == "ACTIVA"
    assert store.list_active("u_ana") == [payload]


def test_list_active_and_list_by_user(store: ConversationStore) -> None:
    a = store.create(new_active(user_id="u_ana"))
    store.create(new_active(conversation_id="conv_2", user_id="u_beto"))
    store.set_state("conv_2", "TERMINADA", current_state="ACTIVA")
    assert store.list_active("u_ana") == [a]
    assert store.list_active("u_beto") == []
    assert [p["id"] for p in store.list_by_user("u_ana")] == ["conv_1"]
    assert len(store.list()) == 2


def test_partial_fields_survive_a_re_read(tmp_path: pathlib.Path) -> None:
    """RNF-10: a failure can never erase what the user already captured."""
    store = ConversationStore(JsonStore(tmp_path / "conversations.json"))
    store.create(new_active())
    store.set_field("conv_1", "description", "Digitalizar la validación de proveedores.")
    store.add_field("conv_1", "problem", "Tres revisiones manuales.")

    reopened = _reopened_store(tmp_path)  # fresh instance, same file
    payload = reopened.get("conv_1")
    assert payload is not None
    assert payload["capturedFields"]["description"] == "Digitalizar la validación de proveedores."
    assert payload["capturedFields"]["problem"] == "Tres revisiones manuales."
    assert payload["state"] == "ACTIVA"


def test_add_field_never_drops_an_existing_capture(store: ConversationStore) -> None:
    store.create(new_active())
    store.set_field("conv_1", "description", "lo ya capturado")
    store.add_field("conv_1", "title", "un título")
    store.add_field("conv_1", "description", "un intento de sobreescribir")
    payload = store.get("conv_1")
    assert payload["capturedFields"]["description"] == "lo ya capturado"
    assert payload["capturedFields"]["title"] == "un título"


def test_set_field_replaces_the_stored_value(store: ConversationStore) -> None:
    store.create(new_active(prefill={"proponent": "prellenado"}))
    store.set_field("conv_1", "proponent", "corrección libre")
    assert store.get("conv_1")["capturedFields"]["proponent"] == "corrección libre"


def test_unknown_conversation_is_404(store: ConversationStore) -> None:
    for call in (
        lambda: store.set_field("conv_nadie", "title", "x"),
        lambda: store.add_field("conv_nadie", "title", "x"),
        lambda: store.set_state("conv_nadie", "RESUMEN", current_state="ACTIVA"),
        lambda: store.add_title_suggestion("conv_nadie", "t"),
        lambda: store.set_current_field("conv_nadie", "title"),
    ):
        with pytest.raises(DomainError) as error:
            call()
        assert error.value.status_code == 404
        assert error.value.code == "CONVERSATION_NOT_FOUND"


def test_set_state_is_compare_and_set(tmp_path: pathlib.Path) -> None:
    store = ConversationStore(JsonStore(tmp_path / "conv.json"))
    store.create(new_active())

    store.set_state("conv_1", "RESUMEN", current_state="ACTIVA")
    assert store.get("conv_1")["state"] == "RESUMEN"

    # RNF-9: the same transition replayed from the old state is discarded.
    with pytest.raises(DomainError) as error:
        store.set_state("conv_1", "TERMINADA", current_state="ACTIVA")
    assert error.value.status_code == 409
    assert error.value.code == "STALE_CONVERSATION_STATE"
    assert store.get("conv_1")["state"] == "RESUMEN"

    # The transition applied from the current state always wins.
    store.set_state("conv_1", "TERMINADA", current_state="RESUMEN")
    assert store.get("conv_1")["state"] == "TERMINADA"


def test_set_state_rejects_an_unknown_state(store: ConversationStore) -> None:
    store.create(new_active())
    with pytest.raises(DomainError) as error:
        store.set_state("conv_1", "OTRO_ESTADO", current_state="ACTIVA")
    assert error.value.status_code == 400
    assert store.get("conv_1")["state"] == "ACTIVA"


def test_title_suggestions_accumulate_and_deduplicate(store: ConversationStore) -> None:
    store.create(new_active())
    store.add_title_suggestion("conv_1", "Título A")
    store.add_title_suggestion("conv_1", "Título A")  # the loop never repeats (RF-4)
    store.add_title_suggestion("conv_1", "Título B")
    assert store.get("conv_1")["titleSuggestions"] == ["Título A", "Título B"]


def test_new_active_with_prefill_keeps_the_preloaded_fields() -> None:
    conversation = new_active(prefill={"proponent": "Ana (Compras)"})
    assert conversation.currentField == "description"
    assert conversation.capturedFields["proponent"] == "Ana (Compras)"
