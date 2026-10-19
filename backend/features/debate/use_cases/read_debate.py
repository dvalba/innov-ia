"""Read a published-idea debate (RF-24, RF-25).

Reading is where the time-driven rules run (plan §4.7 `LEER_DEBATE`): the first
read after the deadline closes the debate exactly once and generates the
summary (when there were messages), and a pending `@asistant` request is
retried when the assistant is back (case 20). The read is read-only for the
participant view: it never mutates the thread except through those automatic
rules.

The idea fields (for the AI prompts) and the company context are read by the
caller at read time (RF-22: the document in force then is the one injected);
they are passed in so this use case stays pure and feature-isolated.
"""

from collections.abc import Callable
from datetime import datetime

from features.debate.infrastructure.debate_store import DebateStore
from features.debate.use_cases.assist import process_pending_assistant
from features.debate.use_cases.close_debate import close_debate
from shared.contracts.assistant_client import AssistantClient


def read_debate(
    store: DebateStore,
    *,
    idea_id: str,
    summary: Callable[[list], str | None] | None,
    assistant: AssistantClient | None,
    idea_fields: dict | None,
    company_context: dict | None,
    now: str | None = None,
) -> dict:
    """Returns the debate payload after applying the read-time rules.

    A debate with no record is a 404 (the idea was not published / the debate
    was not opened). When the deadline was reached the debate closes once and
    the summary is generated (or kept pending), and a pending `@asistant`
    request is retried. The returned payload carries the messages ordered by
    creation, the deadline, the closed flag and the summary (RF-24).
    """
    if store.get_debate(idea_id) is None:
        from shared.exceptions.handlers import DomainError

        raise DomainError("DEBATE_NOT_FOUND", "La idea aún no tiene debate abierto.", status_code=404)
    moment = now or datetime.now().isoformat()
    close_debate(store, idea_id=idea_id, now=moment, summarize=summary)
    debate = store.get_debate(idea_id)
    assert debate is not None  # just closed, it always exists from here on
    # The pending `@asistant` retry only runs while the debate is open: a closed
    # debate no longer admits messages (RF-24, case 18).
    if not debate.closed:
        process_pending_assistant(
            debate,
            idea_id=idea_id,
            assistant=assistant,
            idea_fields=idea_fields,
            company_context=company_context,
            now=moment,
        )
    return store.set(debate)
