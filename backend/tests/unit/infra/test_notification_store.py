"""Notification store tests (T-032, RF-18, plan D1).

The `NotificationStore` persists `Notification` payloads through a `JsonStore`
(its in-memory twin here). It is per user and tracks read/unread. The four —
and only four — RF-18 events are the representable types.
"""

import pytest

from features.notifications.domain.notification import EVENT_TYPES, Notification, NotificationError
from features.notifications.infrastructure.notification_store import NotificationStore
from shared.exceptions.handlers import DomainError
from tests.conftest import InMemoryStore


def _store() -> NotificationStore:
    return NotificationStore(InMemoryStore())


# -- creation -------------------------------------------------------------------


def test_add_creates_an_unread_notification() -> None:
    store = _store()
    record = store.add(user_id="u_ana", event_type="IDEA_PUBLISHED", idea_id="idea_1",
                       message="Tu idea fue publicada.")
    assert record["userId"] == "u_ana"
    assert record["type"] == "IDEA_PUBLISHED"
    assert record["ideaId"] == "idea_1"
    assert record["message"] == "Tu idea fue publicada."
    assert record["read"] is False
    assert record["id"].startswith("notif_")
    assert record["createdAt"]


def test_add_generates_unique_ids() -> None:
    store = _store()
    first = store.add(user_id="u_ana", event_type="IDEA_PUBLISHED", idea_id="idea_1", message="a")
    second = store.add(user_id="u_ana", event_type="IDEA_PUBLISHED", idea_id="idea_1", message="a")
    assert first["id"] != second["id"]


@pytest.mark.parametrize("event_type", EVENT_TYPES)
def test_all_four_events_are_storable(event_type: str) -> None:
    store = _store()
    record = store.add(user_id="u_ana", event_type=event_type, idea_id="idea_1", message="m")
    assert record["type"] == event_type


@pytest.mark.parametrize("event_type", ["IDEA_ARCHIVED", "LOGIN", "", "IDEA_NEW"])
def test_a_fifth_event_type_is_rejected(event_type: str) -> None:
    store = _store()
    with pytest.raises(NotificationError):
        store.add(user_id="u_ana", event_type=event_type, idea_id="idea_1", message="m")


def test_add_rejects_a_missing_user_and_idea() -> None:
    store = _store()
    with pytest.raises(NotificationError):
        store.add(user_id="", event_type="IDEA_PUBLISHED", idea_id="idea_1", message="m")
    with pytest.raises(NotificationError):
        store.add(user_id="u_ana", event_type="IDEA_PUBLISHED", idea_id="", message="m")


# -- listing per user -----------------------------------------------------------


def test_list_for_user_returns_only_that_user_newest_first() -> None:
    store = _store()
    a1 = store.add(user_id="u_ana", event_type="IDEA_PUBLISHED", idea_id="idea_1",
                   message="a1", )
    b1 = store.add(user_id="u_beto", event_type="IDEA_REQUESTED", idea_id="idea_2", message="b1")
    a2 = store.add(user_id="u_ana", event_type="IDEA_REJECTED", idea_id="idea_1", message="a2")

    listed = store.list_for_user("u_ana")
    assert [record["id"] for record in listed] == [a2["id"], a1["id"]]
    assert all(record["userId"] == "u_ana" for record in listed)
    # Beto's notification never leaks into Ana's listing.
    assert b1["id"] not in [record["id"] for record in listed]


def test_list_for_user_empty_when_no_user() -> None:
    store = _store()
    store.add(user_id="u_ana", event_type="IDEA_PUBLISHED", idea_id="idea_1", message="a")
    assert store.list_for_user("u_beto") == []


# -- unread counter -------------------------------------------------------------


def test_unread_count_counts_only_unread() -> None:
    store = _store()
    a1 = store.add(user_id="u_ana", event_type="IDEA_PUBLISHED", idea_id="idea_1", message="a1")
    store.add(user_id="u_ana", event_type="IDEA_REQUESTED", idea_id="idea_2", message="a2")
    store.add(user_id="u_beto", event_type="IDEA_PUBLISHED", idea_id="idea_3", message="b1")

    assert store.unread_count("u_ana") == 2
    assert store.unread_count("u_beto") == 1

    store.mark_read(user_id="u_ana", notification_id=a1["id"])
    assert store.unread_count("u_ana") == 1
    # The other user's count is unaffected.
    assert store.unread_count("u_beto") == 1


# -- mark read ------------------------------------------------------------------


def test_mark_read_is_idempotent_and_persistent() -> None:
    store = _store()
    created = store.add(user_id="u_ana", event_type="IDEA_PUBLISHED", idea_id="idea_1", message="a")
    marked = store.mark_read(user_id="u_ana", notification_id=created["id"])
    assert marked["read"] is True
    assert store.get(created["id"])["read"] is True
    again = store.mark_read(user_id="u_ana", notification_id=created["id"])
    assert again["read"] is True


def test_mark_read_403_for_a_non_recipient() -> None:
    store = _store()
    created = store.add(user_id="u_ana", event_type="IDEA_PUBLISHED", idea_id="idea_1", message="a")
    with pytest.raises(DomainError) as excinfo:
        store.mark_read(user_id="u_beto", notification_id=created["id"])
    assert excinfo.value.status_code == 403
    assert excinfo.value.code == "NOT_NOTIFICATION_OWNER"
    # The notification is left unread.
    assert store.get(created["id"])["read"] is False


def test_mark_read_404_for_an_unknown_notification() -> None:
    store = _store()
    with pytest.raises(DomainError) as excinfo:
        store.mark_read(user_id="u_ana", notification_id="notif_nope")
    assert excinfo.value.status_code == 404
    assert excinfo.value.code == "NOTIFICATION_NOT_FOUND"


# -- payload round-trip ---------------------------------------------------------


def test_payload_round_trip_is_stable() -> None:
    store = _store()
    record = store.add(user_id="u_ana", event_type="IDEA_REFINED", idea_id="idea_9", message="x")
    rehydrated = Notification.from_payload(record).to_payload()
    assert rehydrated == record
