"""Open the debate of a published idea (RF-24, v2.4).

When (and only when) an idea reaches `VALIDADA_PUBLICA`, the platform opens
its debate thread with a deadline of `publication date + debateDays` (RF-24),
where `debateDays` is the **global** administrator setting in force at that
moment (v2.4, decision D23: it was a fixed 30, now it is configured — see
`debate_rules`). The deadline is fixed at opening and is never recomputed
afterwards: changing the configuration only affects the debates opened from
then on (no migration of the stored deadlines).

The debate is an *attribute* of the idea (D12): the idea is not modified, the
thread lives in the debate store, keyed by idea id.

This is the single creation entry point, injected from the composition root
as an emitter bound to the publish use case (`approve_idea`), so `ideas`
never imports `debate`. It is idempotent: replaying the publication for the
same idea never creates a second debate.
"""

from features.debate.domain.debate import Debate
from features.debate.domain.debate_rules import DEBATE_DAYS_DEFAULT, deadline_after_days
from features.debate.infrastructure.debate_days_store import DebateDaysStore
from features.debate.infrastructure.debate_store import DebateStore
from shared.exceptions.handlers import DomainError


def open_debate(
    store: DebateStore,
    days_store: DebateDaysStore,
    *,
    idea_id: str,
    published_at: str,
    now: str,
) -> dict:
    """Opens the debate of the just-published idea and returns its payload.

    `published_at` is the idea's publication timestamp; the deadline is
    `published_at + the global debate-days setting in force` (RF-24, v2.4:
    fixed at opening, never recomputed afterwards). When the administrator
    has not saved a value yet, the default (30 days) applies. If the idea
    does not expose a publication date (it was not really published) the
    creation is a `DomainError` (400). If a debate already exists for the
    idea it is left untouched (idempotent).
    """
    if not str(published_at or "").strip():
        raise DomainError(
            "DEBATE_PUBLICATION_REQUIRED",
            "No se puede abrir el debate de una idea sin fecha de publicación.",
            status_code=400,
        )
    if store.has(idea_id):
        return store.get(idea_id)  # type: ignore[return-value]
    record = days_store.get()
    days = record.get("debateDays") if record else None
    if not isinstance(days, int) or isinstance(days, bool):
        days = DEBATE_DAYS_DEFAULT
    debate = Debate(
        id="debate_" + str(idea_id),
        ideaId=str(idea_id),
        deadline=deadline_after_days(published_at, days),
        open=True,
        closed=False,
    )
    return store.create(debate)
