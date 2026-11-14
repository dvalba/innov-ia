"""Abandon the capture conversation use case (T-087, RF-2, case 7, v2.3).

Orchestration of `POST /capture/abandon` (plan D22): the proponent explicitly
abandons the capture — the conversation ends as `TERMINADA` WITHOUT saving
anything (case 7: no draft, no partial record) and the limit of one capture
conversation at a time (RF-2) is freed.

The abandonment applies to any unfinished conversation (`ACTIVA`, `RESUMEN`
or `CONTINGENCIA`) and is idempotent: abandoning a `TERMINADA` conversation
returns the same outcome without rewriting it. It only ever touches the
caller's own conversation (403 otherwise, 404 when missing).
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
            "Solo el propietario puede abandonar su conversación de captura.",
            status_code=403,
        )
    return payload


def abandon_conversation(
    store: ConversationStore, *, conversation_id: str, user_id: str
) -> dict:
    """Ends the conversation as `TERMINADA` without saving anything (case 7).

    From `ACTIVA`, `RESUMEN` or `CONTINGENCIA` the state is set (compare-and-set,
    RNF-9) and nothing else is touched; from `TERMINADA` the call is a no-op
    (idempotent). The captured fields are left in the store untouched: they are
    simply never confirmed into an idea (there is no draft to clean up).
    """
    payload = _own(store, conversation_id, user_id)
    if payload["state"] != "TERMINADA":
        store.set_state(conversation_id, "TERMINADA", current_state=payload["state"])
    return {"conversationId": conversation_id, "state": "TERMINADA"}
