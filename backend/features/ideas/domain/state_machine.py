"""Idea state machine (T-018, T-079, RF-10/RF-15/RF-16/RF-27/RF-29, RNF-8/RNF-9).

The exact transition table of plan §4.6 (v2.2, spec §5.10):

    EN_DESARROLLO:           { request-publication: SOLICITANDO_PUBLICACION },
    SOLICITANDO_PUBLICACION: { approve: VALIDADA_PUBLICA, reject: EN_DESARROLLO },
    VALIDADA_PUBLICA:        { decide-accepted: ACEPTADA,
                               decide-archived: ARCHIVADA,
                               decide-rejected: RECHAZADA },
    ARCHIVADA:               { reevaluate: VALIDADA_PUBLICA },
    ACEPTADA:                {},   # terminal (MVP)
    RECHAZADA:               {}    # terminal (MVP; sin reevaluación, §8.7)

Only these transitions exist (RNF-9): any other (state, action) pair is a
`DomainError` 409, so simultaneous actions over one idea discard the lost
one without leaving an inconsistent state (case 11). The pure rules here also
apply the audit trail (RNF-8), the rejection comment (RF-16, case 13) and the
final decision: the `decide-*` actions write `idea.decision` (outcome, reason,
score, decidedBy, decidedByName, decidedAt, RF-27/RNF-8) and `reevaluate`
clears it to `None` while the idea goes back to the calibration queue (RF-29,
case 30, keeping the closed debate and the AI evaluation).
"""

from datetime import datetime

from features.ideas.domain.idea import Idea
from shared.exceptions.handlers import DomainError

# The legal transition table, verbatim from plan §4.6.
TRANSITIONS: dict[str, dict[str, str]] = {
    "EN_DESARROLLO": {"request-publication": "SOLICITANDO_PUBLICACION"},
    "SOLICITANDO_PUBLICACION": {"approve": "VALIDADA_PUBLICA", "reject": "EN_DESARROLLO"},
    "VALIDADA_PUBLICA": {
        "decide-accepted": "ACEPTADA",
        "decide-archived": "ARCHIVADA",
        "decide-rejected": "RECHAZADA",
    },
    "ARCHIVADA": {"reevaluate": "VALIDADA_PUBLICA"},
    "ACEPTADA": {},
    "RECHAZADA": {},
}

# The known actions of the table (anything else is rejected too).
ACTIONS: tuple[str, ...] = (
    "request-publication",
    "approve",
    "reject",
    "decide-accepted",
    "decide-archived",
    "decide-rejected",
    "reevaluate",
)

# The final-decision actions (calibration stage, RF-27); the target state is
# the `outcome` recorded in `idea.decision`.
DECIDE_ACTIONS: frozenset[str] = frozenset(
    {"decide-accepted", "decide-archived", "decide-rejected"}
)


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
    reason: str | None = None,
    score: float | None = None,
    apply: bool = True,
) -> Idea:
    """Applies `action` to `idea` and returns the updated idea (RNF-8 trail).

    - `request-publication` is the only way to reach SOLICITANDO_PUBLICACION
      (RF-10) and fixes `requestDate`.
    - `approve` reaches VALIDADA_PUBLICA and records who/when, including
      the self-validation case 9 (RNF-8).
    - `reject` goes back to EN_DESARROLLO and attaches the mandatory comment
      with the identity of the issuer (RF-16, RNF-8, case 13).
    - `decide-accepted`/`decide-archived`/`decide-rejected` (RF-27) leave
      VALIDADA_PUBLICA for the final state and record `idea.decision` with the
      `outcome` (the target state), the `reason` (mandatory for
      ARCHIVADA/RECHAZADA, optional for ACEPTADA), the `score` (average of the
      5 criteria, RNF-8) and who/when decided.
    - `reevaluate` (RF-29, case 30) sends an ARCHIVADA idea back to
      VALIDADA_PUBLICA (calibration queue) and clears `idea.decision` to
      `None`, keeping the closed debate and the AI evaluation.
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
    elif action == "reject":
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
    elif action in DECIDE_ACTIONS:
        result.decision = {
            "outcome": target,
            "reason": reason.strip() if reason and reason.strip() else None,
            "score": score,
            "decidedBy": by_user,
            "decidedByName": by_name,
            "decidedAt": now,
        }
    else:  # action == "reevaluate"
        result.decision = None
    return result
