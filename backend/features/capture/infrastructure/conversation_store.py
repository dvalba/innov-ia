"""Capture infrastructure: `ConversationStore` (T-026, RF-2/RF-7, RNF-10).

`ConversationStore` persists `Conversation` payloads (schema plan §2.4) through
a `JsonStore` file (decision D1). It only stores: the conversational rules
live in the domain (`capture_rules`) and the flows in the use cases (T-027+).

Guarantees:
  - one ``ACTIVA`` conversation per user (RF-2, case 8): the store exposes the
    active lookup the guard relies on, and refuses to create a second one for
    a user who already has one;
  - no loss of captured fields (RNF-10): updating the captured fields only
    adds new keys, never dropping or blanking the ones already stored — a
    failed IA must never erase what the user already said (RF-7);
  - state changes are compare-and-set (RNF-9): marking ``CONTINGENCIA``/
    ``TERMINADA`` only applies when the conversation is still in the state the
    action was computed from, so a concurrent action is discarded (case 11).
"""

import copy
from collections.abc import Sequence

from features.capture.domain.conversation import CONVERSATION_STATES, Conversation
from shared.exceptions.handlers import DomainError
from shared.utils.persistence import JsonStore


class ConversationStore:
    """JSON-backed store of capture conversations (schema plan §2.4).

    Records are keyed by id in a single `JsonStore`. All reads return deep
    copies, mirroring `IdeaStore`/`UserStore`.
    """

    def __init__(self, conversations: JsonStore) -> None:
        self._conversations = conversations

    # -- basic access ----------------------------------------------------------

    def get(self, conversation_id: str) -> dict | None:
        payload = self._conversations.load().get(conversation_id)
        return copy.deepcopy(payload) if payload is not None else None

    def list(self) -> list[dict]:
        return [copy.deepcopy(payload) for payload in self._conversations.load().values()]

    def list_by_user(self, user_id: str) -> Sequence[dict]:
        return [payload for payload in self.list() if payload["userId"] == user_id]

    def list_active(self, user_id: str) -> Sequence[dict]:
        """The user's ``ACTIVA`` conversations (RF-2: there should be at most one)."""
        return [payload for payload in self.list_by_user(user_id) if payload["state"] == "ACTIVA"]

    def list_in_progress(self, user_id: str) -> Sequence[dict]:
        """The user's conversations still inside the capture cycle (RF-2, v2.3):
        ``ACTIVA`` or ``RESUMEN`` — the ones a `start` can resume."""
        return [
            payload
            for payload in self.list_by_user(user_id)
            if payload["state"] in ("ACTIVA", "RESUMEN")
        ]

    # -- creation ----------------------------------------------------------------

    def create(self, conversation: Conversation) -> dict:
        """Persists a new conversation, enforcing the one-``ACTIVA``-per-user rule (RF-2)."""
        if conversation.state == "ACTIVA" and self.list_active(conversation.userId):
            raise DomainError(
                "ACTIVE_CONVERSATION_EXISTS",
                "Ya existe una conversación de captura activa; retomarla en lugar de "
                "crear otra (RF-2, caso 8).",
                status_code=409,
            )
        if self.get(conversation.id) is not None:
            raise DomainError(
                "CONVERSATION_EXISTS", "Ya existe una conversación con ese identificador.",
                status_code=409,
            )
        self._conversations.update(lambda data: {**data, conversation.id: conversation.to_payload()})
        return self.get(conversation.id)  # type: ignore[return-value]

    # -- captured fields (RNF-10) --------------------------------------------------

    def add_field(self, conversation_id: str, key: str, value: str) -> dict:
        """Registers a captured field without ever overwriting an existing one (RNF-10)."""
        return self.update_record(conversation_id, lambda payload: self._apply_field(payload, key, value, True))

    def set_field(self, conversation_id: str, key: str, value: str) -> dict:
        """Replaces a field's value (a free/corrected answer overrides the prefill)."""
        return self.update_record(conversation_id, lambda payload: self._apply_field(payload, key, value, False))

    @staticmethod
    def _apply_field(payload: dict, key: str, value: str, only_missing: bool) -> dict:
        conversation = Conversation.from_payload(payload)
        if only_missing:
            conversation.add_field(key, value)
        else:
            conversation.set_field(key, value)
        return conversation.to_payload()

    def save_conversation(self, conversation: Conversation) -> dict:
        """Persists the whole entity (fields + turn + state) in one read-modify-
        write, so a use case can advance the conversation atomically (404 if missing).

        Because the conversation is always rebuilt from the stored payload first,
        re-saving it can never drop a previously captured field (RNF-10).
        """
        payload = conversation.to_payload()

        def apply(data: dict) -> dict:
            if conversation.id not in data:
                raise DomainError(
                    "CONVERSATION_NOT_FOUND", "La conversación no existe.", status_code=404
                )
            return {**data, conversation.id: payload}

        self._conversations.update(apply)
        return self.get(conversation.id)  # type: ignore[return-value]

    # -- the turn ------------------------------------------------------------------

    def set_current_field(self, conversation_id: str, field_name: str | None) -> dict:
        def apply(payload: dict) -> dict:
            conversation = Conversation.from_payload(payload)
            conversation.currentField = field_name
            return conversation.to_payload()

        return self.update_record(conversation_id, apply)

    def set_offered_options(self, conversation_id: str, field_name: str | None,
                            options: Sequence[str]) -> dict:
        """Records the options the assistant offered while pointing at
        `field_name` (RF-5, D7 replacement). A later chip click is only valid
        against the recorded options of the field in the course."""

        def apply(payload: dict) -> dict:
            conversation = Conversation.from_payload(payload)
            conversation.offeredField = field_name
            conversation.offeredOptions = list(options)
            return conversation.to_payload()

        return self.update_record(conversation_id, apply)

    # -- title suggestions (RF-4) ----------------------------------------------------

    def add_title_suggestion(self, conversation_id: str, text: str) -> dict:
        """Appends a suggested title (the "another" loop remembers them, RF-4)."""
        return self.update_record(conversation_id, lambda payload: self._add_suggestion(payload, text))

    def set_title_suggestions(self, conversation_id: str, texts: Sequence[str]) -> dict:
        def apply(payload: dict) -> dict:
            conversation = Conversation.from_payload(payload)
            conversation.titleSuggestions = list(texts)
            return conversation.to_payload()

        return self.update_record(conversation_id, apply)

    @staticmethod
    def _add_suggestion(payload: dict, text: str) -> dict:
        conversation = Conversation.from_payload(payload)
        if text not in conversation.titleSuggestions:
            conversation.titleSuggestions.append(text)
        return conversation.to_payload()

    # -- state transitions (RNF-9 compare-and-set) ----------------------------------

    def set_state(self, conversation_id: str, new_state: str, current_state: str | None = None) -> dict:
        """Marks the conversation `new_state`, only from `current_state` (or any state).

        When `current_state` is given, a conversation that has already moved is
        discarded (RNF-9, case 11): the state was changed concurrently.
        """
        if new_state not in CONVERSATION_STATES:
            raise DomainError(
                "INVALID_CONVERSATION_STATE",
                f"Estado de conversación no válido: «{new_state}».",
                status_code=400,
            )

        def apply(payload: dict) -> dict:
            if current_state is not None and payload["state"] != current_state:
                raise DomainError(
                    "STALE_CONVERSATION_STATE",
                    f"La conversación pasó de {current_state} a {payload['state']}; "
                    "la acción se descarta (RNF-9).",
                    status_code=409,
                )
            conversation = Conversation.from_payload(payload)
            conversation.state = new_state
            return conversation.to_payload()

        return self.update_record(conversation_id, apply)

    # -- plumbing -------------------------------------------------------------

    def update_record(self, conversation_id: str, mutator) -> dict:
        def apply(data: dict) -> dict:
            payload = data.get(conversation_id)
            if payload is None:
                raise DomainError(
                    "CONVERSATION_NOT_FOUND", "La conversación no existe.", status_code=404
                )
            return {**data, conversation_id: mutator(payload)}

        self._conversations.update(apply)
        return self.get(conversation_id)  # type: ignore[return-value]
