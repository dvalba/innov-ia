"""Capture domain: the `Conversation` entity (T-025, RF-2, plan §2.4).

Pure domain (Constitution §4.2): no FastAPI/Pydantic. The entity mirrors the
JSON schema `Conversation` of plan §2.4: a capture conversation collects the 7
idea fields progressively (RF-3) and owns the current turn (`currentField`).

`capturedFields` maps field name -> text. The two structured fields
(`proponent`, `estimatedResources`, plan §2.2 objects) are stored as JSON
strings: the capture flow only ever carries text, and the final summary
(G08/T-030) parses them back into objects before registering the idea
(RNF-5).
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

CONVERSATION_STATES: tuple[str, ...] = ("ACTIVA", "RESUMEN", "TERMINADA", "CONTINGENCIA")

# RF-3: the exact order of the progressive questions. Owed here (not in
# `capture_rules`) so the entity can default to it without importing the
# behaviour module back (which would close a circular import).
FIELD_ORDER: tuple[str, ...] = (
    "description",
    "title",
    "problem",
    "expectedBenefit",
    "strategicAlignment",
    "estimatedResources",
    "proponent",
)

# The two idea fields whose value is a structured object (plan §2.2); in
# `capturedFields` they are JSON strings.
STRUCTURED_FIELDS: tuple[str, ...] = ("proponent", "estimatedResources")

CHAT_ROLES: tuple[str, ...] = ("user", "assistant", "system")


@dataclass
class ChatMessage:
    """One message of a capture conversation (plan §2.3 `ChatMessage`).

    An `assistant` turn carries `currentField` (the field in the course),
    `quickOptions` (the field's fixed chip catalog, RF-5) and, when the turn
    proposes a title (RF-4), a `titleSuggestion` with its actions.
    """

    id: str = ""
    conversationId: str = ""
    role: str = ""
    text: str = ""
    currentField: str | None = None
    quickOptions: list = field(default_factory=list)
    titleSuggestion: dict | None = None
    needsClarification: bool = False
    createdAt: str = ""

    def __post_init__(self) -> None:
        if not self.id or not str(self.id).strip():
            self.id = f"msg_{uuid.uuid4().hex[:8]}"
        if self.role not in CHAT_ROLES:
            raise ValueError(f"Rol de mensaje no válido: «{self.role}» (solo {'/'.join(CHAT_ROLES)}).")
        if not self.conversationId or not str(self.conversationId).strip():
            raise ValueError("El mensaje de chat requiere una conversación.")
        if not self.createdAt:
            self.createdAt = datetime.now().isoformat()

    def to_payload(self) -> dict:
        """Serializes the message to the canonical payload (plan §2.3)."""
        return {
            "id": self.id,
            "conversationId": self.conversationId,
            "role": self.role,
            "text": self.text,
            "currentField": self.currentField,
            "quickOptions": list(self.quickOptions),
            "titleSuggestion": self.titleSuggestion,
            "needsClarification": self.needsClarification,
            "createdAt": self.createdAt,
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "ChatMessage":
        return cls(
            id=payload["id"],
            conversationId=payload["conversationId"],
            role=payload["role"],
            text=payload.get("text", ""),
            currentField=payload.get("currentField"),
            quickOptions=list(payload.get("quickOptions", [])),
            titleSuggestion=payload.get("titleSuggestion"),
            needsClarification=payload.get("needsClarification", False),
            createdAt=payload.get("createdAt", ""),
        )


@dataclass
class Conversation:
    """A capture session: one per active proponent (RF-2, limit of 1)."""

    id: str
    userId: str
    state: str = "ACTIVA"
    capturedFields: dict = field(default_factory=dict)
    currentField: str | None = None
    order: tuple[str, ...] = ()
    titleSuggestions: list = field(default_factory=list)
    createdAt: str = ""

    def __post_init__(self) -> None:
        if not self.id or not str(self.id).strip():
            raise ValueError("La conversación de captura requiere un identificador.")
        if not self.userId or not str(self.userId).strip():
            raise ValueError("La conversación de captura requiere un usuario (RF-2).")
        if self.state not in CONVERSATION_STATES:
            raise ValueError(
                f"Estado de conversación no válido: «{self.state}» "
                f"(solo {'/'.join(CONVERSATION_STATES)})."
            )
        if not self.order:
            self.order = tuple(FIELD_ORDER)
        if not self.createdAt:
            self.createdAt = datetime.now().isoformat()

    # -- payload round-trip (camelCase, schema §2.4) --------------------------

    def to_payload(self) -> dict:
        """Serializes the entity to the canonical payload (plan §2.4)."""
        return {
            "id": self.id,
            "userId": self.userId,
            "state": self.state,
            "capturedFields": dict(self.capturedFields),
            "currentField": self.currentField,
            "order": list(self.order),
            "titleSuggestions": list(self.titleSuggestions),
            "createdAt": self.createdAt,
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "Conversation":
        """Rebuilds the entity from a stored payload (deep-copy semantics)."""
        try:
            return cls(
                id=payload["id"],
                userId=payload["userId"],
                state=payload["state"],
                capturedFields=dict(payload.get("capturedFields", {})),
                currentField=payload.get("currentField"),
                order=tuple(payload.get("order", ())),
                titleSuggestions=list(payload.get("titleSuggestions", [])),
                createdAt=payload.get("createdAt", ""),
            )
        except KeyError as missing:
            raise ValueError(
                f"El registro de conversación está incompleto; falta «{missing.args[0]}»."
            ) from missing

    # -- the captured fields (RNF-10: never lost) -----------------------------

    def _validate_key(self, key: str) -> None:
        if not isinstance(key, str) or not key.strip():
            raise ValueError("El nombre de campo es inválido.")

    def add_field(self, key: str, value: str) -> None:
        """Registers a captured field without ever overwriting an existing one
        (RNF-10: no information loss, RF-3: a field is asked only once)."""
        self._validate_key(key)
        if key in self.capturedFields:
            return
        self.capturedFields[key] = str(value)

    def set_field(self, key: str, value: str) -> None:
        """Replaces a field's value (a free correction overrides the prefill)."""
        self._validate_key(key)
        self.capturedFields[key] = str(value)

    def has_field(self, key: str) -> bool:
        """A field is captured only with a non-blank value."""
        self._validate_key(key)
        return self.capturedFields.get(key, "").strip() != ""

    def field_text(self, key: str) -> str | None:
        """Returns the captured text for `key`, or `None` when not captured."""
        self._validate_key(key)
        text = self.capturedFields.get(key)
        if text is None or not str(text).strip():
            return None
        return str(text)

    def field_object(self, key: str) -> Any:
        """Parses a structured field (`proponent`, `estimatedResources`) back
        into its object (plan §2.2); the summary/finish (G08) uses it to build
        the idea's 7 fields (RNF-5)."""
        if key not in STRUCTURED_FIELDS:
            raise ValueError(f"«{key}» no es un campo estructurado.")
        text = self.field_text(key)
        if text is None:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    def to_summary(self) -> dict:
        """The editable summary (RF-6): all captured fields, with the structured
        ones (`proponent`, `estimatedResources`) parsed back into their objects
        (plan §2.2) and the rest kept as text."""
        summary: dict[str, Any] = dict(self.capturedFields)
        for key in STRUCTURED_FIELDS:
            if key in summary:
                parsed = self.field_object(key)
                if parsed is not None:
                    summary[key] = parsed
        return summary
