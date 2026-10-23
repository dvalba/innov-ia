"""Debate feature tests (T-072, RF-24, RNF-11).

Covers the published-idea debate domain: the deadline opening (publication +
30 days), the definitive "close once" rule (case 18), the admin per-idea
deadline adjustment with its audit trail (RNF-11), the `@asistant` token
detection (RF-25), the message rule (only while open), and the JSON store
(idempotent creation, normalized reads, persistence). Uses real `JsonStore`
over `tmp_path`; use-case errors (404/409/403/400) are exercised directly.
"""

import pathlib

import pytest

from features.debate.domain.debate import (
    ASSISTANT_AUTHOR,
    ASSISTANT_TOKEN,
    DEBATE_DAYS,
    Debate,
    DebateError,
    DebateMessage,
    assistant_request,
    deadline_after_days,
)
from features.debate.infrastructure.debate_store import DebateStore
from features.debate.use_cases.adjust_deadline import adjust_deadline
from features.debate.use_cases.close_debate import close_debate
from features.debate.use_cases.open_debate import open_debate
from features.debate.use_cases.post_message import post_message
from shared.exceptions.handlers import DomainError, Forbidden
from shared.utils.persistence import JsonStore

PUBLISHED_AT = "2026-06-01T00:00:00"
DEADLINE = deadline_after_days(PUBLISHED_AT)


@pytest.fixture()
def store(tmp_path: pathlib.Path) -> DebateStore:
    return DebateStore(JsonStore(tmp_path / "debate.json"))


def _message(idea_id: str = "idea_1", author_id: str = "u1", author_name: str = "Ana",
             text: str = "¿Cómo ves esta idea?", now: str = "2026-06-02T00:00:00",
             linked_message_id: str | None = None, is_assistant: bool = False) -> DebateMessage:
    return DebateMessage(
        id="debate_msg_0001",
        ideaId=idea_id,
        authorId=author_id,
        authorName=author_name,
        text=text,
        createdAt=now,
        linkedMessageId=linked_message_id,
        isAssistant=is_assistant,
    )


def _debate(idea_id: str = "idea_1", deadline: str = DEADLINE, **overrides: object) -> Debate:
    base = {"id": "debate_" + idea_id, "ideaId": idea_id, "deadline": deadline}
    base.update(overrides)
    return Debate.from_payload(base)  # type: ignore[arg-type]


# -- domain: deadline and closure -------------------------------------------------


def test_deadline_is_published_plus_thirty_days() -> None:
    assert DEBATE_DAYS == 30
    assert deadline_after_days(PUBLISHED_AT) == "2026-07-01T00:00:00"
    assert deadline_after_days("2026-02-28T12:00:00") == "2026-03-30T12:00:00"  # leap year


def test_debate_open_before_and_closed_at_the_deadline() -> None:
    debate = _debate()
    assert debate.is_open("2026-06-30T23:59:59")
    assert not debate.is_open("2026-07-01T00:00:00")
    assert debate.is_past_deadline("2026-07-01T00:00:00")
    assert not debate.is_past_deadline("2026-06-30T23:59:59")


def test_close_is_definitive_and_happens_once() -> None:
    debate = _debate()
    debate.close("2026-07-02T00:00:00", by_user=None)
    assert debate.closed and not debate.open
    assert debate.closedAt == "2026-07-02T00:00:00"
    debate.close("2026-07-03T00:00:00")  # a second close is a no-op
    assert debate.closedAt == "2026-07-02T00:00:00"
    assert not debate.is_open("2026-07-03T00:00:00")  # stays closed


def test_adjust_deadline_to_the_future_reopens_the_debate(store: DebateStore) -> None:
    store.create(_debate(closed=True, closedAt="2026-07-02T00:00:00"))
    record = store.get_debate("idea_1")
    assert record is not None
    record.adjust_deadline("2026-08-15T00:00:00", now="2026-07-05T00:00:00",
                           by_user="u_admin", by_name="Admin")
    assert not record.closed and record.is_open("2026-08-01T00:00:00")


def test_adjust_deadline_to_the_past_keeps_the_debate_closed() -> None:
    debate = _debate()
    debate.adjust_deadline("2026-07-01T00:00:00", now="2026-07-05T00:00:00", by_user="u_admin")
    assert debate.closed and debate.closedAt == "2026-07-05T00:00:00"


def test_adjust_deadline_audits_who_when_and_the_change() -> None:
    debate = _debate()
    debate.adjust_deadline("2026-07-10T00:00:00", now="2026-06-20T00:00:00",
                           by_user="u_admin", by_name="Admin")
    debate.adjust_deadline("2026-08-10T00:00:00", now="2026-07-12T00:00:00",
                           by_user="u_admin2", by_name="Admin 2")
    assert [entry["before"] for entry in debate.deadlineHistory] == [DEADLINE, "2026-07-10T00:00:00"]
    assert [entry["after"] for entry in debate.deadlineHistory] == ["2026-07-10T00:00:00", "2026-08-10T00:00:00"]
    assert [entry["by"] for entry in debate.deadlineHistory] == ["u_admin", "u_admin2"]
    assert [entry["at"] for entry in debate.deadlineHistory] == ["2026-06-20T00:00:00", "2026-07-12T00:00:00"]


# -- the @asistant token (RF-25, case 19) ------------------------------------------


def test_assistant_request_detects_only_a_lead_token() -> None:
    assert assistant_request("@asistant ¿lo ves factible?") == "¿lo ves factible?"
    assert assistant_request("@asistant") == ""  # still an invocation (case 19)
    assert assistant_request("hola @asistant") is None
    assert assistant_request("  @asistant dime tu opinión") == "dime tu opinión"
    assert assistant_request("normal message") is None
    assert ASSISTANT_TOKEN == "@asistant"
    assert ASSISTANT_AUTHOR == "Asistente (IA)"


def test_debate_message_round_trips_and_flags_the_assistant() -> None:
    message = _message(is_assistant=True, author_name=ASSISTANT_AUTHOR)
    rebuilt = DebateMessage.from_payload(message.to_payload())
    assert rebuilt.to_payload() == message.to_payload()
    assert rebuilt.isAssistant and rebuilt.authorName == "Asistente (IA)"


def test_a_debate_message_with_blank_text_is_rejected() -> None:
    with pytest.raises(DebateError):
        _message(text="   ")
    with pytest.raises(DebateError):
        _message(now="")
    with pytest.raises(DebateError):
        Debate(id="debate_x", ideaId="", deadline=DEADLINE)
    with pytest.raises(DebateError):
        Debate(id="debate_x", ideaId="idea_1", deadline="no-es-fecha")


def test_debate_payload_round_trips_messages(store: DebateStore) -> None:
    debate = _debate()
    debate.add_message(_message())
    record = store.set(debate)
    assert store.get("idea_1") == record
    assert len(store.get_debate("idea_1").messages) == 1  # type: ignore[union-attr]


# -- store ------------------------------------------------------------------------


def test_store_create_is_idempotent_per_idea(store: DebateStore) -> None:
    store.create(_debate())
    first = store.get("idea_1")
    store.create(_debate(deadline="2026-08-01T00:00:00"))  # a replayed publication
    assert store.get("idea_1") == first  # the original record is left intact
    assert store.has("idea_1") and store.get("idea_2") is None


def test_store_reads_are_persisted_and_normalized(store: DebateStore, tmp_path: pathlib.Path) -> None:
    record = store.create(_debate())
    reloaded = DebateStore(JsonStore(tmp_path / "debate.json")).get("idea_1")
    assert reloaded == record  # reloaded from disk, normalized (open true, closed false)
    assert reloaded["open"] is True and reloaded["closed"] is False
    payload = store.get("idea_1")
    payload["deadline"] = "2026-08-01T00:00:00"  # a read is insulated from storage
    assert store.get("idea_1")["deadline"] == DEADLINE


def test_store_list_orders_by_deadline_and_flags_pending_assistant(store: DebateStore) -> None:
    store.create(_debate("idea_1", deadline="2026-07-01T00:00:00",
                         pendingAssistant={"request": "x", "messageId": "m1"}))
    store.create(_debate("idea_2", deadline="2026-07-02T00:00:00"))
    assert [record["ideaId"] for record in store.list()] == ["idea_1", "idea_2"]
    assert [record["ideaId"] for record in store.list_open()] == ["idea_1"]


def test_store_messages_of_the_debate_ordered(store: DebateStore) -> None:
    debate = _debate()
    debate.add_message(_message(text="primero", now="2026-06-02T00:00:00"))
    debate.add_message(_message(text="segundo", now="2026-06-03T00:00:00"))
    store.set(debate)
    assert [message.text for message in store.messages_of("idea_1")] == ["primero", "segundo"]
    assert store.messages_of("idea_2") == []


# -- use cases -------------------------------------------------------------------


def test_open_debate_when_the_idea_is_published(store: DebateStore) -> None:
    record = open_debate(store, idea_id="idea_1", published_at=PUBLISHED_AT, now=PUBLISHED_AT)
    assert record["deadline"] == DEADLINE
    assert record["open"] is True and record["closed"] is False
    assert record["messages"] == [] and record["summary"] is None


def test_open_debate_without_a_publication_date_is_rejected(store: DebateStore) -> None:
    with pytest.raises(DomainError) as error:
        open_debate(store, idea_id="idea_1", published_at="", now=PUBLISHED_AT)
    assert error.value.status_code == 400
    assert not store.has("idea_1")


def test_post_message_requires_an_open_debate(store: DebateStore) -> None:
    with pytest.raises(DomainError) as error:
        post_message(store, idea_id="nope", author_id="u1", author_name="A",
                     text="hola", now=PUBLISHED_AT)
    assert error.value.status_code == 404

    store.create(_debate())
    record = post_message(store, idea_id="idea_1", author_id="u1", author_name="A",
                          text="hola", now="2026-06-02T00:00:00")
    assert len(record["messages"]) == 1
    assert record["messages"][0]["authorId"] == "u1"
    assert record["messages"][0]["createdAt"] == "2026-06-02T00:00:00"

    store.set(_debate(closed=True, closedAt="2026-07-02T00:00:00"))
    with pytest.raises(DomainError) as error:
        post_message(store, idea_id="idea_1", author_id="u2", author_name="B",
                     text="adiós", now="2026-07-03T00:00:00")  # case 18
    assert error.value.status_code == 409


def test_close_debate_closes_once_and_only_generates_a_summary_with_messages(
    store: DebateStore,
) -> None:
    store.create(_debate())  # no messages yet
    record = close_debate(store, idea_id="idea_1", now="2026-07-05T00:00:00")
    assert record["closed"] is True  # closed at the deadline
    assert record["summary"] is None  # case 21: no messages, no summary

    # the same debate with messages and a working summarizer
    debate = _debate()
    debate.add_message(_message(text="hay un punto clave", now="2026-06-02T00:00:00"))
    store.set(debate)
    summarized = close_debate(
        store,
        idea_id="idea_1",
        now="2026-07-05T00:00:00",
        summarize=lambda messages: "El punto clave fue discutido y apoyado." if messages else None,
    )
    assert summarized["closed"] is True
    assert summarized["summary"] == "El punto clave fue discutido y apoyado."
    assert summarized["summaryAt"] == "2026-07-05T00:00:00"

    # closing again is a no-op: the summary is not regenerated
    again = close_debate(store, idea_id="idea_1", now="2026-07-05T00:00:00",
                         summarize=lambda messages: "otro resumen")
    assert again["summary"] == "El punto clave fue discutido y apoyado."


def test_close_debate_before_the_deadline_is_a_noop(store: DebateStore) -> None:
    store.create(_debate())
    record = close_debate(store, idea_id="idea_1", now="2026-06-15T00:00:00")
    assert record["closed"] is False
    with pytest.raises(DomainError):
        close_debate(store, idea_id="nope", now="2026-07-05T00:00:00")  # 404


def test_adjust_deadline_requires_the_admin_role(store: DebateStore) -> None:
    store.create(_debate())
    record = adjust_deadline(
        store, idea_id="idea_1", new_deadline="2026-08-01T00:00:00",
        now="2026-07-05T00:00:00", user_id="u_admin", user_name="Admin",
        user_roles=("admin",),
    )
    assert record["deadline"] == "2026-08-01T00:00:00"
    assert record["closed"] is False  # a future date re-opens it
    assert record["deadlineHistory"][0]["by"] == "u_admin"

    with pytest.raises(Forbidden):
        adjust_deadline(
            store, idea_id="idea_1", new_deadline="2026-08-01T00:00:00",
            now="2026-07-05T00:00:00", user_id="u_pro", user_roles=("proponente",),
        )
    with pytest.raises(Forbidden):
        adjust_deadline(
            store, idea_id="idea_1", new_deadline="2026-08-01T00:00:00",
            now="2026-07-05T00:00:00", user_id="u_spec", user_roles=("especialista",),
        )
    with pytest.raises(DomainError):
        adjust_deadline(
            store, idea_id="nope", new_deadline="2026-08-01T00:00:00",
            now="2026-07-05T00:00:00", user_id="u_admin", user_roles=("admin",),
        )
    with pytest.raises(DebateError):
        adjust_deadline(
            store, idea_id="idea_1", new_deadline="no-fecha",
            now="2026-07-05T00:00:00", user_id="u_admin", user_roles=("admin",),
        )
