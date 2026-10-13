"""Update organization profile use case (admin-managed profile, decision D7
replacement).

Validates the administrator's payload and replaces the stored profile
atomically. A non-blank name is required so the assistant always has an
organization to ground its options on; the remaining fields may be empty and
`strategicObjectives` a list of short statements (duplicates and blanks are
dropped).
"""

from features.org.domain.org_profile import OrgProfile
from features.org.infrastructure.org_store import OrgStore
from shared.exceptions.handlers import DomainError


def update_org_profile(store: OrgStore, payload: dict) -> dict:
    name = str(payload.get("name", "")).strip()
    if not name:
        raise DomainError("ORG_PROFILE_INVALID",
                          "El nombre de la organización es obligatorio.",
                          status_code=400)
    seen: set[str] = set()
    objectives: list[str] = []
    for raw in payload.get("strategicObjectives", []) or []:
        target = str(raw).strip()
        if target and target not in seen:
            seen.add(target)
            objectives.append(target)

    profile = OrgProfile(
        name=name,
        sector=str(payload.get("sector", "")).strip(),
        description=str(payload.get("description", "")).strip(),
        mission=str(payload.get("mission", "")).strip(),
        strategicObjectives=objectives,
    )
    return store.put(profile.to_payload())
