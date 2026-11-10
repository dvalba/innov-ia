"""Public catalog router (T-035, T-077, RF-20, RF-23; T-083, RF-20/D16/D21).

  GET /catalog/public?zone=…   -> 200 the catalog by zones (any role, 401
                            without a session). `?zone=` filters one zone
                            (en-proceso|aceptadas|rechazadas|archivadas);
                            without it all four zones are returned. 422 on an
                            unknown zone.
  GET /catalog/{idea_id}-> 200 the public detail of a catalog idea (6 fields +
                            state + decision + evaluations) or 404 (unknown /
                            not a catalog state)

Read-only, public catalog: the four zones of RF-20, each a compact projection
(D16: title, publication date and description) — never the `contact` (RNF-7).
The list (`/public`) is the compact projection; the detail (`/{idea_id}`,
RF-23) adds the 6 fields, the `state`, the `decision` and the final
`evaluation` / immutable `aiEvaluation` snapshot (RF-26). Implemented in the
`ideas` feature so it reuses the use cases without any cross-feature import.
"""

from fastapi import APIRouter

from app.deps import IdeaLedgerDep, SessionDep
from features.ideas.use_cases.detail_public import detail_public
from features.ideas.use_cases.list_public import list_public

catalog_router = APIRouter(prefix="/catalog", tags=["catalog"])


@catalog_router.get("/public")
def public_catalog_endpoint(session: SessionDep, ledger: IdeaLedgerDep,
                            zone: str | None = None) -> dict:
    """Returns the public catalog by zones (RF-20/D16/D21); `?zone=` filters one zone."""
    return list_public(ledger, zone=zone)


@catalog_router.get("/{idea_id}")
def public_detail_endpoint(session: SessionDep, ledger: IdeaLedgerDep, idea_id: str) -> dict:
    """Returns the public detail of a catalog idea (RF-23) or 404 (the catalog guard)."""
    return detail_public(ledger, idea_id=idea_id)
