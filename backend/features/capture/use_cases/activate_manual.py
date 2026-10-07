"""Activate the manual contingency form use case (T-030, RF-7 case 2, RNF-10).

Orchestration of `POST /capture/activate-manual`: moves the user's capture
conversation to `CONTINGENCIA` and returns its `capturedFields` so the
client can deploy the manual form already pre-filled — nothing captured is
lost (RNF-10).

The activation is a no-op when the conversation is already in
`CONTINGENCIA` (idempotent: the same pre-filled payload is returned, the
state is not rewritten). A `TERMINADA` conversation can no longer be
diverted to the form (409): the idea was already registered.

`capturedFields` travel as stored (the structured fields are JSON strings,
plan §2.2): the same raw shape the 503 fallback of `process_message`
already hands to the client, so the manual form receives one and only one
representation.
"""

from features.capture.infrastructure.conversation_store import ConversationStore
from shared.exceptions.handlers import DomainError


def _own(store: ConversationStore, conversation_id: str, user_id: str) -> dict:
    payload = store.get(conversation_id)
    if payload is None:
        raise DomainError("CONVERSATION_NOT_FOUND", "La conversación no existe.", status_code=404)
    if payload["userId"] != user_id:
        raise DomainError(
            "NOT_CONVERSATION_OWNER",
            "Solo el propietario puede activar el formulario manual de su conversación.",
            status_code=403,
        )
    return payload


def activate_manual(
    store: ConversationStore, *, conversation_id: str, user_id: str
) -> dict:
    """Marks the conversation `CONTINGENCIA` (from `ACTIVA` or `RESUMEN`) and
    returns its captured fields as the pre-filled payload of the manual form.
    """
    payload = _own(store, conversation_id, user_id)
    if payload["state"] == "TERMINADA":
        raise DomainError(
            "CONVERSATION_FINISHED",
            "La conversación ya finalizó; la idea quedó registrada.",
            status_code=409,
        )
    if payload["state"] != "CONTINGENCIA":
        store.set_state(conversation_id, "CONTINGENCIA", current_state=payload["state"])
        payload = store.get(conversation_id)
    return {
        "conversationId": conversation_id,
        "state": "CONTINGENCIA",
        "capturedFields": payload["capturedFields"],
    }
