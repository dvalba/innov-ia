"""Notifications domain: the in-app `Notification` entity (T-032, RF-18, schema §2.7).

Pure domain: no FastAPI/Pydantic (decision D8). Only the eight events of RF-18
are representable — the original four (`IDEA_REFINED`, `IDEA_PUBLISHED`,
`IDEA_REJECTED`, `IDEA_REQUESTED`), the three added by v2.2 (`IDEA_ACCEPTED`,
`IDEA_ARCHIVED`, `IDEA_REEVALUATED`) and `IDEA_CALIBRATION_PENDING` (T-083) —
and any other type is rejected (spec: "se notifican estos eventos y solo estos").
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from shared.exceptions.handlers import DomainError

# The in-app events (RF-18, schema §2.7 `type` enum): the original four, the
# three final-decision events of v2.2 (T-082) and the calibration-pending one
# (T-083, RF-18/RF-20): the eight RF-18 events and only them.
EVENT_TYPES: tuple[str, ...] = (
    "IDEA_REFINED",
    "IDEA_PUBLISHED",
    "IDEA_REJECTED",
    "IDEA_REQUESTED",
    "IDEA_ACCEPTED",
    "IDEA_ARCHIVED",
    "IDEA_REEVALUATED",
    "IDEA_CALIBRATION_PENDING",
)


class NotificationError(DomainError):
    """The notification is malformed (400)."""

    def __init__(self, message: str) -> None:
        super().__init__("NOTIFICATION_INVALID", message, status_code=400)


def new_id() -> str:
    """A unique, opaque notification id."""
    return "notif_" + uuid.uuid4().hex[:12]


@dataclass
class Notification:
    """An in-app event, delivered to a single `user_id` (schema §2.7).

    `type` is constrained to the eight RF-18 events; `idea_id` points at the
    object the notification refers to (direct access, RF-12/RF-18); `read`
    tracks the read/unread state (unread counter); `created_at` is set on
    construction when not provided.
    """

    user_id: str
    type: str
    idea_id: str
    message: str
    read: bool = False
    id: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        if self.type not in EVENT_TYPES:
            raise NotificationError(
                f"Tipo de evento de notificación no válido: «{self.type}» "
                f"(solo {', '.join(EVENT_TYPES)})."
            )
        if not self.user_id or not str(self.user_id).strip():
            raise NotificationError("La notificación requiere un destinatario (userId).")
        if not self.idea_id or not str(self.idea_id).strip():
            raise NotificationError("La notificación requiere el identificador de la idea (ideaId).")
        if not self.id:
            self.id = new_id()
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_payload(self) -> dict:
        """Serializes the entity to the canonical payload (schema §2.7, camelCase)."""
        return {
            "id": self.id,
            "userId": self.user_id,
            "type": self.type,
            "ideaId": self.idea_id,
            "message": self.message,
            "read": self.read,
            "createdAt": self.created_at,
        }

    @classmethod
    def from_payload(cls, payload: dict) -> "Notification":
        """Rebuilds the entity from a stored payload (canonical round-trip)."""
        try:
            return cls(
                id=payload["id"],
                user_id=payload["userId"],
                type=payload["type"],
                idea_id=payload["ideaId"],
                message=payload.get("message", ""),
                read=payload.get("read", False),
                created_at=payload.get("createdAt", ""),
            )
        except KeyError as missing:
            raise NotificationError(
                f"El registro de notificación está incompleto; falta «{missing.args[0]}»."
            ) from missing
