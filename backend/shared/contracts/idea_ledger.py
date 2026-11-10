"""Shared idea ledger contract (T-008).

Resolves coupling between features (plan §1.2, coupling note): the
`assistant` and `validation` features consume ideas ONLY through this
Protocol, injected via dependency composition; no feature imports from
another one.

Payloads are dicts shaped like the JSON schemas of plan §2 (`Idea` and
`IdeaVersion`). The `fields` key in a payload is the dict of the 6 idea
fields (schema `Idea` §2.2). State/origin string values are spec contracts
and are kept as defined in the specification.
"""

from collections.abc import Iterable
from typing import Protocol, runtime_checkable

# The 6 idea fields (spec §1.1). An idea payload's `fields` dict always
# contains these keys.
IDEA_FIELDS: tuple[str, ...] = (
    "title",
    "proponent",
    "description",
    "problem",
    "expectedBenefit",
    "strategicAlignment",
)

# State machine states (plan §4.6, v2.2 final states spec §5.10).
STATE_EN_DESARROLLO = "EN_DESARROLLO"
STATE_SOLICITANDO_PUBLICACION = "SOLICITANDO_PUBLICACION"
STATE_VALIDADA_PUBLICA = "VALIDADA_PUBLICA"
STATE_ACEPTADA = "ACEPTADA"
STATE_ARCHIVADA = "ARCHIVADA"
STATE_RECHAZADA = "RECHAZADA"

# Idea origins (spec RF-2/RNF-2).
ORIGIN_ASISTIDA = "asistida"
ORIGIN_MANUAL = "manual"


@runtime_checkable
class IdeaLedger(Protocol):
    """Idea ledger shared between features.

    The reference implementation is `features.ideas.infrastructure.idea_store`
    (T-019). The `assistant` and `validation` features depend only on this
    Protocol.
    """

    def get(self, idea_id: str) -> dict | None:
        """Returns the full idea payload by id, or `None` if it does not exist."""
        ...

    def list_by_state(self, state: str, owner_id: str | None = None) -> Iterable[dict]:
        """Lists ideas in `state`. If `owner_id` is passed, filters by owner (RF-19)."""
        ...

    def list_by_origin(self, origin: str, state: str, owner_id: str | None = None) -> Iterable[dict]:
        """Lists ideas with the given `origin` and `state` (refinement queue, RF-11)."""
        ...

    def save_current_fields(self, idea_id: str, fields: dict) -> dict:
        """Applies the current fields to the idea (version acceptance, RF-8/RF-13).

        Returns the updated payload. Raises `DomainError` if the idea is missing.
        """
        ...

    def get_version(self, idea_id: str, version_id: str) -> dict | None:
        """Returns the `IdeaVersion` payload or `None`."""
        ...

    def versions_of(self, idea_id: str) -> Iterable[dict]:
        """All `IdeaVersion` payloads of the idea, oldest to newest (RF-11 queue)."""
        ...

    def add_version(self, *, idea_id: str, fields: dict, requested_by: str,
                    generating: bool = False) -> dict:
        """Registers a PENDIENTE version (RF-8/RF-11); returns its payload."""
        ...

    def update(self, idea_id: str, changes: dict) -> dict:
        """Merges scalar payload changes (e.g. `reviewedByAI`, `improvementRequest`).

        Returns the updated payload. Raises `DomainError` if the idea is missing.
        """
        ...
