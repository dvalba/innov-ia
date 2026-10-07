"""Notifications infrastructure: JSON-backed notification store (T-032, RF-18).

`NotificationStore` persists `Notification` payloads through a single
`JsonStore` file. Records are keyed by their `id`; listing and the unread
counter are scoped per `user_id`, and a notification may only be marked read
by its own recipient. Mirrors the atomic-write guarantees of the other
`JsonStore` stores (plan D1).
"""

import copy

from features.notifications.domain.notification import Notification
from shared.exceptions.handlers import DomainError
from shared.utils.persistence import JsonStore


class NotificationStore:
    """JSON-backed in-app notification store (per user, read/unread)."""

    def __init__(self, raw: JsonStore) -> None:
        self._raw = raw

    def add(self, *, user_id: str, event_type: str, idea_id: str, message: str) -> dict:
        """Creates and persists an (unread) notification and returns its payload.

        The event `type` is validated by the domain: a fifth type is rejected
        (RF-18). The id is unique.
        """
        notification = Notification(user_id=user_id, type=event_type, idea_id=idea_id,
                                    message=message)
        record = notification.to_payload()

        def apply(data: dict) -> dict:
            if record["id"] in data:
                raise DomainError(
                    "NOTIFICATION_EXISTS",
                    "Ya existe una notificación con ese identificador.",
                    status_code=409,
                )
            return {**data, record["id"]: record}

        self._raw.update(apply)
        return copy.deepcopy(record)

    def get(self, notification_id: str) -> dict | None:
        """Returns the notification payload by id, or `None` if unknown."""
        record = self._raw.load().get(notification_id)
        return copy.deepcopy(record) if record is not None else None

    def list_for_user(self, user_id: str) -> list[dict]:
        """The notifications of `user_id`, newest first."""
        records = [
            record
            for record in self._raw.load().values()
            if record.get("userId") == user_id
        ]
        records = [copy.deepcopy(record) for record in records]
        records.sort(key=lambda record: (record.get("createdAt", ""), record.get("id", "")),
                     reverse=True)
        return records

    def unread_count(self, user_id: str) -> int:
        """The number of `user_id`'s unread notifications (the bell counter)."""
        return sum(1 for record in self.list_for_user(user_id) if not record.get("read", False))

    def mark_read(self, *, user_id: str, notification_id: str) -> dict:
        """Marks a notification as read; returns the updated payload.

        404 when unknown; 403 when the caller is not the recipient (a notification
        may only be read by its own recipient, RF-18).
        """
        record = self._raw.load().get(notification_id)
        if record is None:
            raise DomainError(
                "NOTIFICATION_NOT_FOUND",
                "La notificación no existe.",
                status_code=404,
            )
        if record.get("userId") != user_id:
            raise DomainError(
                "NOT_NOTIFICATION_OWNER",
                "Solo el destinatario puede marcar la notificación como leída (RF-18).",
                status_code=403,
            )

        def apply(data: dict) -> dict:
            return {**data, notification_id: {**record, "read": True}}

        self._raw.update(apply)
        return copy.deepcopy({**record, "read": True})
