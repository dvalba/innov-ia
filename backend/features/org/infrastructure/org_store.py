"""Organization feature infrastructure: the company-context document store (RF-21).

`OrgStore` persists the single company-context document in a JSON file through
`JsonStore` under the fixed key `"context"`. Writes are atomic (the store
contract) and payloads are deep-copied on read to keep the in-memory copy
insulated from storage mutations.

Backward compatibility (D13): the v2.0 profile was stored under the legacy key
`"profile"` as a bare profile mapping. `get()` transparently wraps a legacy
record into the `{profile, guideText, updatedAt}` document, and `put()` always
stores the new document shape.
"""

from features.org.domain.company_context import CompanyContext
from shared.utils.persistence import JsonStore

_CONTEXT_KEY = "context"
_LEGACY_PROFILE_KEY = "profile"


class OrgStore:
    """JSON-backed single-record store for the company-context document."""

    def __init__(self, store: JsonStore) -> None:
        self._store = store

    def _raw(self) -> dict | None:
        data = self._store.load()
        if _CONTEXT_KEY in data:
            return data.get(_CONTEXT_KEY)
        if _LEGACY_PROFILE_KEY in data:
            profile = data.get(_LEGACY_PROFILE_KEY)
            return {
                "profile": CompanyContext.from_payload(
                    {"profile": profile}).profile,
                "guideText": "",
                "updatedAt": "",
            }
        return None

    def has(self) -> bool:
        return self._raw() is not None

    def get(self) -> dict | None:
        """The stored company-context document, or None when none is set.

        A legacy profile-only record is wrapped into the document shape so the
        v2.0 profile is preserved inside the single document (D13).
        """
        raw = self._raw()
        if raw is None:
            return None
        return CompanyContext.from_payload(raw).to_payload()

    def put(self, document: dict) -> dict:
        self._store.update(
            lambda data: {k: v for k, v in data.items() if k != _LEGACY_PROFILE_KEY} |
            {_CONTEXT_KEY: document}
        )
        return self.get()  # type: ignore[return-value]

    def seed(self, document: dict) -> None:
        """Stores the document when (and only when) none exists yet (idempotent)."""
        if self.has():
            return
        self.put(document)
