"""Get organization profile use case (decision D7 replacement).

Returns the `profile` section of the company-context document (or an empty
one) when the administrator has not defined it yet, so the capture flow —
which grounds its per-turn IA options on the organization profile — can always
count on the documented flat shape (all fields present).

The full document (profile + guide text) is served to the admin panel by
`get_context` (RF-21); the AI's full-context injection across every operation
is implemented by T-071 (RF-22).
"""

from features.org.domain.company_context import EMPTY_PROFILE
from features.org.infrastructure.org_store import OrgStore


def get_org_profile(store: OrgStore) -> dict:
    """The organization profile as a flat dict for the capture flow."""
    document = store.get() or {}
    profile = document.get("profile") or {}
    merged = dict(EMPTY_PROFILE)
    merged.update(profile)
    merged["strategicObjectives"] = list(merged.get("strategicObjectives") or [])
    return merged
