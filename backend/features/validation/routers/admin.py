"""Administrator calibration-thresholds router (T-081, RF-28).

Endpoints (guarded to the `admin` role, 403 otherwise; 401 without a session):
   GET /admin/calibration-thresholds -> 200 the current thresholds, or the
                                         default `{rejectionThreshold: 4,
                                         acceptanceThreshold: 7}` (case 31)
   PUT /admin/calibration-thresholds -> 200 the saved record (422
                                         `THRESHOLDS_INVALID` when a value is
                                         not an integer 1-10 or
                                         rejection >= acceptance)

Pydantic schemas live in this layer only (plan D8, Constitution §4.2); the
validation and audit rules are enforced by the `admin_thresholds` use case.
The payload is kept loose (`Any`, defaulting to `None`) so the domain decides
whether a value is an integer or not (a `4.0`, a `true` or a missing field is
a 422 `THRESHOLDS_INVALID`, not a silent coercion or a FastAPI 422).
"""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.deps import ThresholdStoreDep, role_dependency
from features.validation.use_cases.admin_thresholds import get_thresholds, save_thresholds

admin_thresholds_router = APIRouter(prefix="/admin/calibration-thresholds", tags=["validation"])

AdminDep = role_dependency("admin")


class ThresholdsIn(BaseModel):
    rejectionThreshold: Any = None
    acceptanceThreshold: Any = None


@admin_thresholds_router.get("")
def read_thresholds(store: ThresholdStoreDep, session: AdminDep) -> dict:
    """The current calibration thresholds, or the default (RF-28, case 31)."""
    return get_thresholds(store)


@admin_thresholds_router.put("")
def write_thresholds(payload: ThresholdsIn, store: ThresholdStoreDep,
                     session: AdminDep) -> dict:
    """Replaces the thresholds, audited with the admin id and the time (RNF-8)."""
    return save_thresholds(store, payload.model_dump(), user_id=session.user_id)
