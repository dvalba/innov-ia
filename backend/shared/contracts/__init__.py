"""Shared contracts between features (Constitution §3.2 / §4.2)."""

from shared.contracts.idea_ledger import (
    IDEA_FIELDS,
    ORIGIN_ASISTIDA,
    ORIGIN_MANUAL,
    STATE_EN_DESARROLLO,
    STATE_SOLICITANDO_PUBLICACION,
    STATE_VALIDADA_PUBLICA,
    IdeaLedger,
)

__all__ = [
    "IDEA_FIELDS",
    "ORIGIN_ASISTIDA",
    "ORIGIN_MANUAL",
    "STATE_EN_DESARROLLO",
    "STATE_SOLICITANDO_PUBLICACION",
    "STATE_VALIDADA_PUBLICA",
    "IdeaLedger",
]
