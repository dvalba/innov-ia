"""Create-notification use case (T-033, RF-18).

Creates the in-app notifications for the four RF-18 events and performs the
`IDEA_REQUESTED` fanout to every specialist. Emission is bound in the
composition root (`app/deps`), so this feature is the only place that knows
how to create a notification; `ideas`/`assistant` never import it. The 6-field
`ideaId` gives the recipient direct access to the object (RF-12/RF-18).
"""

from features.notifications.infrastructure.notification_store import NotificationStore
from shared.contracts.roles import list_specialists


def message_for(event_type: str, idea_id: str) -> str:
    """The Spanish message (RNF-4) for each of the four RF-18 events."""
    if event_type == "IDEA_REFINED":
        return f"La IA refinó tu idea ({idea_id})."
    if event_type == "IDEA_PUBLISHED":
        return f"Tu idea ({idea_id}) fue publicada."
    if event_type == "IDEA_REJECTED":
        return f"Tu idea ({idea_id}) fue rechazada."
    if event_type == "IDEA_REQUESTED":
        return f"El proponente solicitó publicar la idea {idea_id}."
    raise ValueError(f"Evento de notificación desconocido: {event_type!r}")


def create_notification(
    store: NotificationStore, *, user_id: str, event_type: str, idea_id: str,
    message: str | None = None,
) -> dict:
    """Creates and returns a single (unread) notification for `user_id`.

    `event_type` must be one of the four RF-18 events; anything else raises
    (spec: "estos eventos y solo estos"). When `message` is omitted the
    canonical Spanish wording for the event is used.
    """
    return store.add(
        user_id=user_id,
        event_type=event_type,
        idea_id=idea_id,
        message=message if message is not None else message_for(event_type, idea_id),
    )


def fanout_requested(
    store: NotificationStore, directory, *, idea_id: str, message: str | None = None,
) -> list[dict]:
    """Fans `IDEA_REQUESTED` out to every active specialist (RF-18).

    Returns the list of created notifications (one per specialist, empty when
    no specialist exists). Active accounts only: a deactivated specialist never
    receives a notification but keeps their history.
    """
    created: list[dict] = []
    for specialist_id in list_specialists(directory):
        created.append(
            create_notification(store, user_id=specialist_id, event_type="IDEA_REQUESTED",
                                idea_id=idea_id, message=message)
        )
    return created
