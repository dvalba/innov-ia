"""Public detail use case (T-077, RF-23, plan §3.1/§6, D12/D16; T-083, D21).

The public detail of an idea that exists in the catalog (plan line 708:
`GET /catalog/{ideaId} -> 6 campos, debate y evaluación`). It returns the same
public projection as the list: the 6 fields with the proponent reduced to
`name`/`area` (never `contact`, RNF-7), the origin and the
registration/publication dates — plus the final judgment `evaluation` and the
immutable `aiEvaluation` snapshot (RF-26), which are only meaningful once the
idea is published, hence live here and not in the compact list (D16).

From v2.2 (T-083, D21) the detail operates for the four catalog zones, not only
`VALIDADA_PUBLICA`: an idea in any of the catalog states (en-proceso, aceptada,
rechazada, archivada) is returned with its `state` and its `decision` (the final
calibration decision, present in the three final states and `None` while the
idea is still in calibration).

The debate is NOT embedded: it belongs to the `debate` feature and is exposed
on its own endpoint (`GET /catalog/{ideaId}/debate`, T-073) so `ideas` never
imports `debate` (decision D12). The frontend composes both views.

Guard: only ideas in one of the four catalog states exist in the catalog — an
unknown id and an idea in any other state are both a 404 (the catalog never
leaks the existence of unpublished data, RNF-7).
"""

from features.ideas.domain.catalog_zones import ZONE_STATES
from features.ideas.domain.idea import Idea
from features.ideas.infrastructure.idea_store import IdeaStore
from shared.exceptions.handlers import DomainError

# The states that exist in the catalog (D21): the four catalog zones.
_CATALOG_STATES: tuple[str, ...] = tuple(ZONE_STATES.values())


def detail_public(ledger: IdeaStore, *, idea_id: str) -> dict:
    """Returns the public detail of a catalog idea, or 404.

    Unknown id, or an idea not in one of the four catalog states (en-proceso,
    aceptada, rechazada, archivada), raises `DomainError` (404): from the
    catalog's point of view such an idea does not exist. The entry holds `id`,
    the 6 fields (proponent reduced to `name`/`area`, never `contact`),
    `origin`, `createdAt`, `publishedAt`, the `state`, the `decision` (the final
    calibration decision, `None` while the idea is still in calibration) and
    the two evaluation objects (RF-26, present once the idea is published).
    """
    payload = ledger.get(idea_id)
    if payload is None or payload.get("state") not in _CATALOG_STATES:
        raise DomainError("IDEA_NOT_FOUND", "La idea no existe en el catálogo público.", status_code=404)
    idea = Idea.from_payload(payload)
    fields = idea.fields()
    fields["proponent"] = {
        "name": idea.proponent.get("name", ""),
        "area": idea.proponent.get("area", ""),
    }
    return {
        "id": idea.id,
        "fields": fields,
        "origin": idea.origin,
        "createdAt": idea.createdAt,
        "publishedAt": idea.publishedAt,
        "state": idea.state,
        "decision": idea.decision,
        "evaluation": idea.evaluation,
        "aiEvaluation": idea.aiEvaluation,
    }
