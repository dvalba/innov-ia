"""Shared contracts between features (Constitution §3.2 / §4.2)."""

from shared.contracts.assistant_client import AssistantClient
from shared.contracts.idea_ledger import (
    IDEA_FIELDS,
    ORIGIN_ASISTIDA,
    ORIGIN_MANUAL,
    STATE_EN_DESARROLLO,
    STATE_SOLICITANDO_PUBLICACION,
    STATE_VALIDADA_PUBLICA,
    IdeaLedger,
)
from shared.contracts.roles import (
    KNOWN_ROLES,
    ROLE_ADMIN,
    ROLE_PROPOSER,
    ROLE_SPECIALIST,
    list_specialists,
)
from shared.contracts.user_directory import UserDirectory

__all__ = [
    "AssistantClient",
    "IDEA_FIELDS",
    "ORIGIN_ASISTIDA",
    "ORIGIN_MANUAL",
    "STATE_EN_DESARROLLO",
    "STATE_SOLICITANDO_PUBLICACION",
    "STATE_VALIDADA_PUBLICA",
    "IdeaLedger",
    "KNOWN_ROLES",
    "ROLE_ADMIN",
    "ROLE_PROPOSER",
    "ROLE_SPECIALIST",
    "list_specialists",
    "UserDirectory",
]
