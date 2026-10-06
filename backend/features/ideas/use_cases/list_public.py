"""List public catalog use case (T-022, RF-20, RNF-7).

The public catalog exposes only `VALIDADA_PUBLICA` ideas — nothing less
(spec §5.9/RF-20, decision #2) — with the 7 idea fields and the
proponent's name and area, the registration date and the publication
date. The proponent's `contact` is never included (read-only catalog,
RNF-7: no proponent data beyond name/area).
"""

from features.ideas.domain.idea import Idea
from features.ideas.infrastructure.idea_store import IdeaStore
from shared.contracts.idea_ledger import STATE_VALIDADA_PUBLICA


def list_public(ledger: IdeaStore) -> list[dict]:
    """Lists the public catalog: every `VALIDADA_PUBLICA` idea, any owner, newest first.

    Each entry holds `id`, the 7 fields (with the proponent reduced to
    `name`/`area`, no `contact`), `origin`, `createdAt` and `publishedAt`.
    Ideas in any other state (or of any user) are excluded from the result
    (RF-20).
    """
    entries: list[dict] = []
    for payload in ledger.list_by_state(STATE_VALIDADA_PUBLICA):
        idea = Idea.from_payload(payload)
        fields = idea.fields()
        fields["proponent"] = {
            "name": idea.proponent.get("name", ""),
            "area": idea.proponent.get("area", ""),
        }
        entries.append(
            {
                "id": idea.id,
                "fields": fields,
                "origin": idea.origin,
                "createdAt": idea.createdAt,
                "publishedAt": idea.publishedAt,
            }
        )
    entries.sort(key=lambda entry: (entry["createdAt"], entry["id"]), reverse=True)
    return entries
