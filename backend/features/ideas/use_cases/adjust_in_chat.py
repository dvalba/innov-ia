"""Adjust in chat use case (T-024, RF-13, plan §4.5 `AJUSTAR_EN_CHAT`).

Reopens the assistant's conversation over an existing idea (pre-contextualized
with the idea's current fields — it is not a new capture, RF-2). The
conversational loop itself lives in the `capture` feature (G08) via its
shared contract; this use case only resolves the entry: with the assistant
available it returns the pre-contextualized payload the conversation starts
from (`newCapture=False`), and without it (the ping fails) it offers the
manual editing fallback with the idea's 7 fields (RF-9).

The resulting changes are applied later as `IdeaVersion`s with
`requestedBy=adjustment` (status PENDIENTE), exactly like the improvement —
never automatically (RF-13).
"""

from features.ideas.infrastructure.idea_store import IdeaStore
from shared.contracts.assistant_client import AssistantClient
from shared.contracts.idea_ledger import IDEA_FIELDS, STATE_EN_DESARROLLO
from shared.exceptions.handlers import DomainError


def adjust_in_chat(
    ledger: IdeaStore,
    assistant: AssistantClient,
    *,
    idea_id: str,
    owner_id: str,
) -> dict:
    """Opens the adjustment over the idea and returns the entry payload.

    Guards: unknown idea -> 404; not the owner -> 403 (RNF-7); state other
    than EN_DESARROLLO -> 409 (the adjustment offers versions to decide, RF-13).

    Returns:
      - without the IA: `{"mode": "manual", "ideaId", "fields"}` (RF-9, the
        idea's current 7 fields pre-fill the manual editing);
      - with the IA: `{"mode": "chat", "ideaId", "fields", "newCapture": False}`
        — the conversation is pre-contextualized on the idea (RF-2).
    """
    payload = ledger.get(idea_id)
    if payload is None:
        raise DomainError("IDEA_NOT_FOUND", "La idea no existe.", status_code=404)
    if payload["ownerId"] != owner_id:
        raise DomainError(
            "NOT_IDEA_OWNER",
            "Solo el propietario de la idea puede ajustarla (RNF-7).",
            status_code=403,
        )
    if payload["state"] != STATE_EN_DESARROLLO:
        raise DomainError(
            "IDEA_NOT_ADJUSTABLE",
            f"La idea está en estado {payload['state']}; solo se ajusta en EN_DESARROLLO (RF-13).",
            status_code=409,
        )
    fields = {key: payload[key] for key in IDEA_FIELDS}
    if not assistant.ping():
        return {"mode": "manual", "ideaId": idea_id, "fields": fields}
    return {"mode": "chat", "ideaId": idea_id, "fields": fields, "newCapture": False}
