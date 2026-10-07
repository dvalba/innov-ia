"""Notifications router (T-033, RF-18, plan §3.1).

Endpoints, all guarded to an active session (any role, 401 without):
  GET  /notifications             -> 200 {"notifications": [...], "unread": int}
  POST /notifications/{id}/read   -> 200 updated payload (only the recipient;
                                      404 unknown, 403 non-recipient)

The emission of the four events is bound in the composition root
(`app/deps`) via injected emitters, so this router never creates a
notification itself. User-facing messages are in Spanish (RNF-4).
"""

from fastapi import APIRouter

from app.deps import NotificationStoreDep, SessionDep
from features.notifications.use_cases.list_notifications import list_notifications
from features.notifications.use_cases.mark_read import mark_read

notifications_router = APIRouter(prefix="/notifications", tags=["notifications"])


@notifications_router.get("")
def read_notifications_endpoint(session: SessionDep, store: NotificationStoreDep) -> dict:
    """Lists the session's notifications (newest first) and the unread counter."""
    return list_notifications(store, user_id=session.user_id)


@notifications_router.post("/{notification_id}/read")
def mark_read_endpoint(notification_id: str, session: SessionDep,
                       store: NotificationStoreDep) -> dict:
    """Marks a notification read; only the recipient (404 unknown, 403 otherwise)."""
    return mark_read(store, user_id=session.user_id, notification_id=notification_id)
