"""Update company context use case (RF-21, online editing / PUT).

Replaces the stored company-context document with the administrator's payload
(`profile` + `guideText`). The profile is required: a blank profile (no name,
sector, description, mission or strategic objectives) is rejected with a 400
so the AI always has at least an organization to ground its operations on.
`updatedAt` is stamped with the current time.
"""

from datetime import datetime

from features.org.domain.company_context import CompanyContext, clean_profile
from features.org.infrastructure.org_store import OrgStore
from shared.exceptions.handlers import DomainError


def update_context(store: OrgStore, payload: dict) -> dict:
    """Validates the payload, replaces the document and returns the updated one."""
    profile = clean_profile((payload or {}).get("profile"))
    guide_text = str((payload or {}).get("guideText", "")).strip()

    if not (profile["name"] or profile["sector"] or profile["description"]
            or profile["mission"] or profile["strategicObjectives"]):
        raise DomainError(
            "CONTEXT_INVALID",
            "El perfil de la organización no puede quedar vacío.",
            status_code=400,
        )

    document = CompanyContext(
        profile=profile,
        guideText=guide_text,
        updatedAt=datetime.now().isoformat(),
    )
    return store.put(document.to_payload())
