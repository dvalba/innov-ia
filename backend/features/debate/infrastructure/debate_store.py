"""Debate feature infrastructure: the JSON debate store (RF-24, RF-25).

`DebateStore` persists one record per published idea in `backend/data/debate.json`
through `JsonStore`, keyed by idea id. Each record couples the debate thread
(`messages`, `deadline`, `closed`, `summary`, ...) with the AI evaluation
(`evaluation`), because both are attributes of the same `VALIDADA_PUBLICA`
idea (D12 — the idea itself is never edited). Writes are atomic (the store
contract) and records are normalized on read: a stored payload is rebuilt
through `Debate.from_payload(...).to_payload()`, so the in-memory copy is
always the canonical shape (RNF-9).
"""

from collections.abc import Sequence

from features.debate.domain.debate import Debate, DebateMessage
from shared.utils.persistence import JsonStore


class DebateStore:
    """JSON-backed store of the published-idea debates (one record per idea)."""

    def __init__(self, store: JsonStore) -> None:
        self._store = store

    def get(self, idea_id: str) -> dict | None:
        """The normalized debate record of the idea, or `None`."""
        debate = self.get_debate(idea_id)
        return debate.to_payload() if debate is not None else None

    def get_debate(self, idea_id: str) -> Debate | None:
        """The `Debate` entity of the idea, or `None` when it was not opened."""
        raw = self._store.load().get(str(idea_id))
        if raw is None:
            return None
        return Debate.from_payload(raw)

    def has(self, idea_id: str) -> bool:
        """`True` when the idea already has a debate record."""
        return str(idea_id) in self._store.load()

    def create(self, debate: Debate) -> dict:
        """Registers the debate the first time (idempotent: an existing record
        is left untouched, so a replayed publication never duplicates it)."""
        idea_id = debate.ideaId

        def apply(data: dict) -> dict:
            if idea_id in data:
                return data
            return {**data, idea_id: debate.to_payload()}

        self._store.update(apply)
        return self.get(idea_id)  # type: ignore[return-value]

    def set(self, debate: Debate) -> dict:
        """Replaces the whole record of the idea (messages, closure, summary,
        evaluation). Raises `DebateError` semantics through `update` on failure."""
        idea_id = debate.ideaId

        def apply(data: dict) -> dict:
            return {**data, idea_id: debate.to_payload()}

        self._store.update(apply)
        return self.get(idea_id)  # type: ignore[return-value]

    def list(self) -> list[dict]:
        """Every debate record (normalized), ordered by deadline oldest first."""
        data = self._store.load()
        records = [Debate.from_payload(payload).to_payload() for payload in data.values()]
        records.sort(key=lambda record: (record.get("deadline") or "", record.get("ideaId") or ""))
        return records

    def list_open(self) -> Sequence[dict]:
        """The debates that still carry a pending `@asistant` request (retry)."""
        return [
            record
            for record in self.list()
            if (record.get("pendingAssistant") or None) is not None
        ]

    def messages_of(self, idea_id: str) -> Sequence[DebateMessage]:
        """The messages of the debate, oldest first (creation order)."""
        debate = self.get_debate(idea_id)
        return list(debate.messages) if debate is not None else []
