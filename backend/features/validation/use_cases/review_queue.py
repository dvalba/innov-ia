"""Review-queue use case (T-034, RF-14).

Read side of the specialist validation surface: the queue of ideas waiting to
be published. Consumes ideas only through the shared `IdeaLedger` contract,
so the `validation` feature never imports another feature for this listing.
"""

from features.validation.domain.queue_rules import QUEUE_STATE, queue_entry
from shared.contracts.idea_ledger import IdeaLedger


def review_queue(ledger: IdeaLedger) -> list[dict]:
    """Lists the review queue: every idea in SOLICITANDO_PUBLICACION (RF-14).

    Each entry uses the queue visibility of `queue_rules` (the 7 fields with
    the proponent reduced to name/area, no contact) plus `id`, `origin` and
    `requestDate`. Ordered by request date (oldest first), then by id.
    """
    entries = [queue_entry(payload) for payload in ledger.list_by_state(QUEUE_STATE)]
    entries.sort(key=lambda entry: (entry.get("requestDate") or "", entry["id"]))
    return entries
