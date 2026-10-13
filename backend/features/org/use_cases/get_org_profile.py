"""Get organization profile use case (admin-managed profile, decision D7 replacement).

Returns the stored profile or an empty one when the administrator has not
defined it yet, so the panel and the capture flow can always count on the
documented shape (all fields present).
"""

from features.org.infrastructure.org_store import OrgStore

EMPTY_PROFILE: dict = {
    "name": "",
    "sector": "",
    "description": "",
    "mission": "",
    "strategicObjectives": [],
}


def get_org_profile(store: OrgStore) -> dict:
    profile = store.get()
    if profile is None:
        return dict(EMPTY_PROFILE, strategicObjectives=[])
    merged = dict(EMPTY_PROFILE)
    merged.update(profile)
    merged["strategicObjectives"] = list(merged.get("strategicObjectives") or [])
    return merged
