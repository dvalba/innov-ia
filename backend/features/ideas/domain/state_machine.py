"""Idea state machine (T-018, RF-10/RF-15/RF-16, RNF-8/RNF-9, plan §4.6).

The exact transition table of plan §4.6:

    EN_DESARROLLO:           { request-publication: SOLICITANDO_PUBLICACION },
    SOLICITANDO_PUBLICACION: { approve: VALIDADA_PUBLICA, reject: EN_DESARROLLO },
    VALIDADA_PUBLICA:        {}                                  # terminal (MVP)

Only these transitions exist (RNF-9): any other (state, action) pair is a
`DomainError` 409, so simultaneous actions over one idea discard the lost
one without leaving an inconsistent state (case 11). The pure rules here also
apply the audit trail (RNF-8) and the rejection comment (RF-16, case 13).
"""

from datetime import datetime

from features.ideas.domain.idea import Idea
from shared.exceptions.handlers import DomainError

# The legal transition table, verbatim from plan §4.6.
TRANSITIONS: dict[str, dict[str, str]] = {
    "EN_DESARROLLO": {"request-publication": "SOLICITANDO_PUBLICACION"},
    "SOLICITANDO_PUBLICACION": {"approve": "VALIDADA_PUBLICA", "reject": "EN_DESARROLLO"},
    "VALIDADA_PUBLICA": {},
}

# The known actions of the table (anything else is rejected too).
ACTIONS: tuple[str, ...] = ("request-publication", "approve", "reject")


class InvalidTransition(DomainError):
    """A (state, action) pair outside the table: 409 (RNF-9)."""

    def __init__(self, state: str, action: str) -> None:
        super().__init__(
            "INVALID_TRANSITION",
            f"La acción «{action}» no está permitida para una idea en estado {state}.",
            status_code=409,
        )


def _target(state: str, action: str) -> str:
    table = TRANSITIONS.get(state)
    if table is None or action not in table:
        raise InvalidTransition(state, action)
    return table[action]


def transicionar(
    idea: Idea,
    action: str,
    *,
    by_user: str,
    by_name: str = "",
    now: str | None = None,
    comment: str | None = None,
    apply: bool = True,
) -> Idea:
    """Applies `action` to `idea` and returns the updated idea (RNF-8 trail).

    - `request-publication` is the only way to reach SOLICITANDO_PUBLICACION
      (RF-10) and fixes `requestDate`.
    - `approve` reaches VALIDADA_PUBLICA and records who/when, including
      the self-validation case 9 (RNF-8).
    - `reject` goes back to EN_DESARROLLO and attaches the mandatory comment
      with the identity of the issuer (RF-16, RNF-8, case 13).
    - `apply=False` returns a copy; the original is left untouched.
    """
    now = now or datetime.now().isoformat()
    target = _target(idea.state, action)
    result = idea if apply else Idea.from_payload(idea.to_payload())
    result.state = target
    if action == "request-publication":
        result.requestDate = now
    elif action == "approve":
        result.publishedBy = by_user
        result.publishedAt = now
    else:  # action == "reject"
        if comment is None or not comment.strip():
            raise DomainError("REJECTION_COMMENT_REQUIRED",
                              "El rechazo de una idea requiere un comentario (RF-16, caso 13).",
                              status_code=400)
        result.rejectionNote = {
            "by": by_user,
            "byName": by_name,
            "comment": comment.strip(),
            "at": now,
        }
    return result
