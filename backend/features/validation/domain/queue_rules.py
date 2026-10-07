"""Validation queue visibility rules (T-034, RF-14).

Domain rule for what the specialist sees in the review queue: only ideas in
`SOLICITANDO_PUBLICACION`, and the proponent is reduced to name + area — the
contact data is never exposed (spec: "visibilidad sin datos de contacto").
Operates on shared ledger payloads only: the `validation` feature never
imports another feature.
"""

from shared.contracts.idea_ledger import IDEA_FIELDS, STATE_SOLICITANDO_PUBLICACION

# The only state visible in the review queue (RF-14).
QUEUE_STATE = STATE_SOLICITANDO_PUBLICACION


def queue_entry(payload: dict) -> dict:
    """Projects a SOLICITANDO_PUBLICACION payload into one queue entry.

    Holds `id`, `origin`, `requestDate` and the 7 fields (`fields`), with the
    `proponent` reduced to `name`/`area` (no `contact`). Anything beyond the
    7 fields (ownerId, state, contact, ...) is never exposed (RF-14).
    """
    raw_proponent = payload.get("proponent", {})
    proponent = {"name": raw_proponent.get("name", ""), "area": raw_proponent.get("area", "")}
    fields = {key: payload[key] for key in IDEA_FIELDS}
    fields["proponent"] = proponent
    return {
        "id": payload["id"],
        "origin": payload.get("origin", ""),
        "requestDate": payload.get("requestDate"),
        "fields": fields,
    }
