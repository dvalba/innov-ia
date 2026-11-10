"""Public catalog zones (T-083, RF-20, D16, D21).

The public catalog is organized in four zones (RF-20, spec §5.9), each a
projection of a single idea state (D21: the zone is derived from `state`, never
stored):

  - **en-proceso**  -> `VALIDADA_PUBLICA` (published, no final decision yet);
  - **aceptadas**   -> `ACEPTADA`;
  - **rechazadas**  -> `RECHAZADA`;
  - **archivadas**  -> `ARCHIVADA`.

Each zone lists its ideas as a compact entry (D16: title, publication date and
description only — the 6 fields, the debate and the evaluation live in the
detail view, RF-23) and is read-only with no proponent contact data (RNF-7).
The zone name in the query is validated (422 `CATALOG_ZONE_INVALID` when not
one of the four).

Pure domain: no FastAPI/Pydantic (decision D8).
"""

from shared.contracts.idea_ledger import (
    STATE_ACEPTADA,
    STATE_ARCHIVADA,
    STATE_RECHAZADA,
    STATE_VALIDADA_PUBLICA,
)
from shared.exceptions.handlers import ValidationFailed

# The four catalog zones (RF-20) mapped to the state they project (D21).
# The key is the public zone name (the `?zone=` query value); the value is the
# `Idea.state` it lists.
ZONE_STATES: dict[str, str] = {
    "en-proceso": STATE_VALIDADA_PUBLICA,
    "aceptadas": STATE_ACEPTADA,
    "rechazadas": STATE_RECHAZADA,
    "archivadas": STATE_ARCHIVADA,
}

# The canonical order of the zones (the tab order of the catalog, spec §5.9).
ZONE_ORDER: tuple[str, ...] = ("en-proceso", "aceptadas", "rechazadas", "archivadas")


def validate_zone(zone: str | None) -> str | None:
    """422s when `zone` is not one of the four catalog zones (D21).

    `None` means "all zones" (the catalog without a `?zone=` parameter).
    """
    if zone is None:
        return None
    if zone not in ZONE_STATES:
        raise ValidationFailed(
            code="CATALOG_ZONE_INVALID",
            message=f"Zona de catálogo no válida: «{zone}» (solo {', '.join(ZONE_ORDER)}).",
            details={"problems": [f"«{zone}» no es una zona de catálogo válida."]},
        )
    return zone


def compact_item(payload: dict) -> dict:
    """Projects a catalog payload into one compact entry (D16).

    Holds only `id`, `title`, `publishedAt` and `description` (RF-20). The
    proponent's contact data is never exposed (RNF-7); the remaining 5 fields,
    the debate and the evaluation belong to the detail view (RF-23).
    """
    return {
        "id": payload["id"],
        "title": payload.get("title", ""),
        "publishedAt": payload.get("publishedAt"),
        "description": payload.get("description", ""),
    }


def zone_items(payloads) -> list[dict]:
    """The compact entries of one zone, newest first (by publication date).

    Entries are ordered by `publishedAt` (then `id`) so the newest-published
    ideas surface first, mirroring the previous `VALIDADA_PUBLICA`-only catalog
    ordering.
    """
    items = [compact_item(payload) for payload in payloads]
    items.sort(key=lambda entry: (entry["publishedAt"] or "", entry["id"]), reverse=True)
    return items


def catalog_payloads(ledger, zone: str | None) -> dict[str, list[dict]]:
    """The four zones of the catalog as a zone-name -> compact-items map (D21).

    `zone` is validated first (422 on an unknown value); every zone is always
    populated from the ledger, so the caller can return the whole map (no
    `?zone=`) or a single zone's items from it.
    """
    validate_zone(zone)
    return {name: zone_items(ledger.list_by_state(state)) for name, state in ZONE_STATES.items()}
