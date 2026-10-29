"""Public catalog router (T-035, T-077, RF-20, RF-23).

  GET /catalog/public   -> 200 the `VALIDADA_PUBLICA` ideas (any role, 401
                           without a session)
  GET /catalog/{idea_id}-> 200 the public detail of one published idea (6
                           fields + evaluations) or 404 (unknown / unpublished)

Read-only, public catalog: only `VALIDADA_PUBLICA` ideas (decision #2), with
the 6 fields, the proponent's name and area, and the registration/publication
dates — never the `contact` (RNF-7). The list (`/public`, D16) is the compact
projection; the detail (`/{idea_id}`, RF-23) adds the 6 fields plus the final
`evaluation` and the immutable `aiEvaluation` snapshot (RF-26). Implemented in
the `ideas` feature so it reuses the use cases without any cross-feature import.
"""

from fastapi import APIRouter

from app.deps import IdeaLedgerDep, SessionDep
from features.ideas.use_cases.detail_public import detail_public
from features.ideas.use_cases.list_public import list_public

catalog_router = APIRouter(prefix="/catalog", tags=["catalog"])


@catalog_router.get("/public")
def public_catalog_endpoint(session: SessionDep, ledger: IdeaLedgerDep) -> list[dict]:
    """Returns the public catalog: every VALIDADA_PUBLICA idea, no contact (RF-20)."""
    return list_public(ledger)


@catalog_router.get("/{idea_id}")
def public_detail_endpoint(session: SessionDep, ledger: IdeaLedgerDep, idea_id: str) -> dict:
    """Returns the public detail of one published idea (RF-23) or 404 (RF-20 guard)."""
    return detail_public(ledger, idea_id=idea_id)
