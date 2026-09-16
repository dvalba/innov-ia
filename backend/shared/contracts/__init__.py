"""Contratos compartidos entre features (Constitucion §3.2 / §4.2)."""

from shared.contracts.idea_ledger import (
    CAMPOS_DE_LA_IDEA,
    ESTADO_EN_DESARROLLO,
    ESTADO_SOLICITANDO_PUBLICACION,
    ESTADO_VALIDADA_PUBLICA,
    ORIGEN_ASISTIDA,
    ORIGEN_MANUAL,
    IdeaLedger,
)

__all__ = [
    "CAMPOS_DE_LA_IDEA",
    "ESTADO_EN_DESARROLLO",
    "ESTADO_SOLICITANDO_PUBLICACION",
    "ESTADO_VALIDADA_PUBLICA",
    "ORIGEN_ASISTIDA",
    "ORIGEN_MANUAL",
    "IdeaLedger",
]
