"""Mark-read notification use case (T-033, RF-18).

A notification may only be marked read by its own recipient (403 otherwise);
an unknown id is a 404.
"""

from features.notifications.infrastructure.notification_store import NotificationStore


def mark_read(store: NotificationStore, *, user_id: str, notification_id: str) -> dict:
    """Marks a notification as read and returns the updated payload."""
    return store.mark_read(user_id=user_id, notification_id=notification_id)
