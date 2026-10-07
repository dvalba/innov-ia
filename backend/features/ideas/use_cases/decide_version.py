"""Decide version use case (T-024, RF-8, RF-13).

The proponent accepts or discards a PENDIENTE version of their idea
(decision once per version). Accepting makes the version VIGENTE: the idea
adopts its fields, marks `reviewedByAI`, and its `currentVersionId` moves to
it — the idea keeps EN_DESARROLLO (decision #1: acceptance does not publish).
Discarding marks the version DESCARTADA and leaves the idea untouched.
Either way the `generando` flag is released once no pending version remains,
so manual editing unblocks (RF-9). The state rules live in
`IdeaStore.decide` (T-020); this use case only owns the access guards
(RNF-7) and returns the idea payload.
"""

from features.ideas.infrastructure.idea_store import IdeaStore
from shared.exceptions.handlers import DomainError


def decide_version(
    ledger: IdeaStore, *, idea_id: str, version_id: str, owner_id: str, accept: bool
) -> dict:
    """Applies the proponent's decision and returns the updated idea payload.

    Guards: unknown idea -> 404; not the owner -> 403 (RNF-7). Then delegates
    to `IdeaStore.decide` (unknown version -> 404; a second decision on the
    same version -> 409, decision once).
    """
    payload = ledger.get(idea_id)
    if payload is None:
        raise DomainError("IDEA_NOT_FOUND", "La idea no existe.", status_code=404)
    if payload["ownerId"] != owner_id:
        raise DomainError(
            "NOT_IDEA_OWNER",
            "Solo el propietario de la idea puede decidir sus versiones (RNF-7).",
            status_code=403,
        )
    ledger.decide(idea_id=idea_id, version_id=version_id, accept=accept)
    return ledger.get(idea_id)  # type: ignore[return-value]
