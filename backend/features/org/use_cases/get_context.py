"""Get company context use case (RF-21/RF-22, case 24).

Returns the stored company-context document or the blank one when the
administrator has not defined it yet, so the admin panel and every AI
operation can always count on the documented shape (profile + guideText +
updatedAt). A blank context is the *case 24*: the AI operates without it and
the admin is warned.
"""

from features.org.domain.company_context import CompanyContext
from features.org.infrastructure.org_store import OrgStore


def get_context(store: OrgStore) -> dict:
    """The current company-context document, or the empty one (case 24)."""
    stored = store.get()
    if stored is None:
        return CompanyContext.empty().to_payload()
    return stored
