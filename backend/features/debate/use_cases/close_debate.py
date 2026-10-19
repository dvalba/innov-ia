"""Close a debate at its deadline, generating the summary (RF-24, cases 18/21).

The closure rule (RF-24): when the deadline is reached, the debate closes
*definitively and only once* — no new messages and the UI shows the summary.
The first read (or write) after the deadline closes it; afterwards it stays
closed. The summary is the AI's recap of the main points of the conversation,
generated **only when the debate had at least one message** (case 21: no
messages, no summary — the UI says "there was no debate").

The AI call is injected as `summarize` (bound to the prompt + company context
in T-073, RF-22): `close_debate` owns the *rule* (close once, only with
messages, retryable summary) and stays pure. When the assistant is down
(`summarize` returns `None`), the closure still happens and the summary
stays `None` (pending) until the next interaction (case 21 / RF-1). The retry
also runs on an *already closed* debate whose summary is still missing (case
20/21): every read (or write) gives it one more chance.
"""

from collections.abc import Callable

from features.debate.infrastructure.debate_store import DebateStore
from shared.exceptions.handlers import DomainError


def _try_summary(debate, now: str, summarize: Callable[[list], str | None] | None) -> None:
    """Generates the missing summary once, when the debate had messages (case 21)."""
    if debate.summary or not debate.messages or summarize is None:
        return
    text = summarize([message.to_payload() for message in debate.messages])
    if text:
        debate.set_summary(text, now)


def close_debate(
    store: DebateStore,
    *,
    idea_id: str,
    now: str,
    summarize: Callable[[list], str | None] | None = None,
) -> dict:
    """Closes the debate if its deadline has been reached, once, and stores the
    AI summary when the debate had messages.

    Returns the updated debate payload. A debate with no record is a 404.
    The closure is idempotent: closing an already-closed debate is a no-op
    (RF-24), and a debate still open (`now < deadline`) is returned unchanged.
    The summary is generated only the first time the debate closes and only
    when there is at least one message; a `None` summary (assistant down) is
    kept pending and retried at every later read (or write) until it lands
    (case 21 / RF-1).
    """
    debate = store.get_debate(idea_id)
    if debate is None:
        raise DomainError("DEBATE_NOT_FOUND", "La idea aún no tiene debate abierto.", status_code=404)
    if not debate.closed:
        if not debate.is_past_deadline(now):
            return store.get(idea_id)  # type: ignore[return-value]
        debate.close(now)
    _try_summary(debate, now, summarize)
    return store.set(debate)
