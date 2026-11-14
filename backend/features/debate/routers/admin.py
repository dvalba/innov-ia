"""Administrator debate-days router (T-089, RF-24, RNF-11).

Endpoints (guarded to the `admin` role, 403 otherwise; 401 without a session):
   GET /admin/debate-days -> 200 the current record, or the default
                             `{debateDays: 30, updatedBy: null, updatedAt: null}`
   PUT /admin/debate-days -> 200 the saved record (422 `DEBATE_DAYS_INVALID`
                             when the value is not an integer in 1-90)

Pydantic schemas live in this layer only (plan D8, Constitution §4.2); the
validation and audit rules are enforced by the `debate_days` use case. The
payload is kept loose (`Any`, defaulting to `None`) so the domain decides
whether a value is an integer or not (a `4.0`, a `true` or a missing field is
a 422 `DEBATE_DAYS_INVALID`, not a silent coercion or a FastAPI 422).
"""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.deps import DebateDaysStoreDep, role_dependency
from features.debate.use_cases.debate_days import get_debate_days, save_debate_days

admin_debate_days_router = APIRouter(prefix="/admin/debate-days", tags=["debate"])

AdminDep = role_dependency("admin")


class DebateDaysIn(BaseModel):
    debateDays: Any = None


@admin_debate_days_router.get("")
def read_debate_days(store: DebateDaysStoreDep, session: AdminDep) -> dict:
    """The current debate-days record, or the default (RF-24, v2.4)."""
    return get_debate_days(store)


@admin_debate_days_router.put("")
def write_debate_days(payload: DebateDaysIn, store: DebateDaysStoreDep,
                      session: AdminDep) -> dict:
    """Replaces the debate days, audited with the admin id and the time (RNF-11)."""
    return save_debate_days(store, payload.model_dump(), user_id=session.user_id)
