"""List public catalog use case (T-022, RF-20, RNF-7; T-083, RF-20/D16/D21).

The public catalog is organized in four zones (RF-20): En proceso
(`VALIDADA_PUBLICA`), Aceptadas, Rechazadas y Archivadas — each a projection of
one idea state (D21: derived from `state`, never stored). A zone is read as a
compact list (D16: title, publication date and description only); the 6 fields,
the debate and the evaluation live in the detail view (RF-23). Read-only, no
proponent contact data (RNF-7).

The shape depends on the requested zone:
  - `zone=None`  -> `{"zones": {name: [items]}}` (all four zones);
  - `zone=<name>` -> `{"zone": name, "items": [items]}` (one zone).
An unknown zone is a 422 (`CATALOG_ZONE_INVALID`, D21).
"""

from features.ideas.domain.catalog_zones import catalog_payloads
from features.ideas.infrastructure.idea_store import IdeaStore


def list_public(ledger: IdeaStore, zone: str | None = None) -> dict:
    """Returns the public catalog for one zone, or all zones (RF-20).

    With `zone=None` the four zones are returned as a map; with a known `zone`
    that zone's compact items are returned. The compact item holds `id`,
    `title`, `publishedAt` and `description` only (D16).
    """
    zones = catalog_payloads(ledger, zone)
    if zone is None:
        return {"zones": zones}
    return {"zone": zone, "items": zones[zone]}
