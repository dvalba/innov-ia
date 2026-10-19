"""Adjust the deadline of a debate, per idea (RF-24, RNF-11).

Only the **administrator** may adjust the deadline of a debate, advancing or
extending it, even on a closed debate (RF-24). Re-opening a closed debate is
adjusting its date to a future one. Every adjustment is audited with who/when/
before/after (`deadlineHistory`, RNF-11). The debate record is not tied to the
idea state: a `VALIDADA_PUBLICA` idea always keeps its debate.
"""

from features.debate.domain.debate import DebateError
from features.debate.infrastructure.debate_store import DebateStore
from shared.contracts.roles import ROLE_ADMIN
from shared.exceptions.handlers import DomainError, Forbidden


def adjust_deadline(
    store: DebateStore,
    *,
    idea_id: str,
    new_deadline: str,
    now: str,
    user_id: str,
    user_name: str = "",
    user_roles: tuple[str, ...] = (),
) -> dict:
    """Adjusts the deadline of the debate of `idea_id` (admin only, audited).

    Raises `DomainError` (404) when the idea has no debate, `Forbidden` (403)
    when the caller is not an administrator, and `DebateError` (400) when the
    new date is not a valid ISO date. A future date (after `now`) re-opens a
    closed debate; a non-future date keeps or makes it closed. The adjustment
    is appended to the audit history.
    """
    if ROLE_ADMIN not in tuple(user_roles or ()):
        raise Forbidden(
            code="ROLE_NOT_ALLOWED",
            message="Solo un administrador puede ajustar la fecha límite de un debate.",
        )
    debate = store.get_debate(idea_id)
    if debate is None:
        raise DomainError("DEBATE_NOT_FOUND", "La idea aún no tiene debate abierto.", status_code=404)
    try:
        debate.adjust_deadline(new_deadline, now=now, by_user=user_id, by_name=user_name)
    except DebateError:
        raise
    return store.set(debate)
