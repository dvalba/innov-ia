"""Review-queue use case (T-034, RF-14; T-082, RF-14 v2.2).

Read side of the specialist validation surface: the two-stage queue (RF-14,
v2.2). Consumes ideas only through the shared `IdeaLedger` contract, so the
`validation` feature never imports another feature for this listing. The
calibration stage additionally needs a debate-closure predicate, injected by
the caller (the `validation` feature does not import `debate`).
"""

from collections.abc import Callable

from features.validation.domain.queue_rules import (
    CALIBRATION_STATE,
    QUEUE_STATE,
    STAGE_CALIBRACION,
    STAGE_PUBLICACION,
    in_calibration,
    queue_entry,
    validate_stage,
)
from shared.contracts.idea_ledger import IdeaLedger


def review_queue(ledger: IdeaLedger) -> list[dict]:
    """Lists the publication queue: every idea in SOLICITANDO_PUBLICACION (RF-14).

    Each entry uses the queue visibility of `queue_rules` (the 6 fields with
    the proponent reduced to name/area, no contact) plus `id`, `origin` and
    `requestDate`. Ordered by request date (oldest first), then by id.
    """
    entries = [queue_entry(payload) for payload in ledger.list_by_state(QUEUE_STATE)]
    entries.sort(key=lambda entry: (entry.get("requestDate") or "", entry["id"]))
    return entries


def calibration_queue(
    ledger: IdeaLedger, is_debate_closed: Callable[[str], bool]
) -> list[dict]:
    """Lists the calibration queue (RF-14 v2.2).

    Ideas in `VALIDADA_PUBLICA` whose debate is closed, whose evaluation is not
    `PENDING`, and which carry no decision yet. Ordered by request date (oldest
    first), then by id.
    """
    entries = [
        queue_entry(payload)
        for payload in ledger.list_by_state(CALIBRATION_STATE)
        if in_calibration(payload, is_debate_closed)
    ]
    entries.sort(key=lambda entry: (entry.get("requestDate") or "", entry["id"]))
    return entries


def queue(
    ledger: IdeaLedger,
    stage: str | None,
    is_debate_closed: Callable[[str], bool],
) -> list[dict]:
    """Dispatches the queue by stage (v2.2): `None` = both, publication first.

    `stage` is validated (422 `QUEUE_STAGE_INVALID` when not one of the two
    known values).
    """
    stage = validate_stage(stage)
    if stage == STAGE_PUBLICACION:
        return review_queue(ledger)
    if stage == STAGE_CALIBRACION:
        return calibration_queue(ledger, is_debate_closed)
    # stage is None: both, publication first.
    return review_queue(ledger) + calibration_queue(ledger, is_debate_closed)
