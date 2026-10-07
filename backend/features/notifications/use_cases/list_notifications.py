"""List / count notifications use case (T-033, RF-18).

Read side of the notification center: the recipient's list (newest first)
plus the unread counter that feeds the bell (T-055).
"""

from features.notifications.infrastructure.notification_store import NotificationStore


def list_notifications(store: NotificationStore, *, user_id: str) -> dict:
    """Returns `{"notifications": [...], "unread": int}` for `user_id`."""
    notifications = store.list_for_user(user_id)
    return {"notifications": notifications, "unread": store.unread_count(user_id)}
