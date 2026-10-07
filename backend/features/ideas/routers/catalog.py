"""Public catalog router (T-035, RF-20).

  GET /catalog/public -> 200 the `VALIDADA_PUBLICA` ideas (any role, 401
                         without a session)

Read-only, public catalog: only `VALIDADA_PUBLICA` ideas (decision #2), with
the 7 fields, the proponent's name and area, and the registration/publication
dates — never the `contact` (RNF-7). Implemented in the `ideas` feature so it
reuses `list_public` without any cross-feature import.
"""

from fastapi import APIRouter

from app.deps import IdeaLedgerDep, SessionDep
from features.ideas.use_cases.list_public import list_public

catalog_router = APIRouter(prefix="/catalog", tags=["catalog"])


@catalog_router.get("/public")
def public_catalog_endpoint(session: SessionDep, ledger: IdeaLedgerDep) -> list[dict]:
    """Returns the public catalog: every VALIDADA_PUBLICA idea, no contact (RF-20)."""
    return list_public(ledger)
