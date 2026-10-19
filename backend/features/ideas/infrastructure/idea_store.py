"""Ideas feature infrastructure (T-019, RF-8/RF-19, decision D1).

`IdeaStore` is the reference implementation of the shared `IdeaLedger`
contract (plan §1.2 coupling note): it persists `Idea` payloads (schema
§2.2) and `IdeaVersion` payloads (schema §2.5) through two `JsonStore`
files, one per collection. It only persists: the business rules live in the
domain (T-017/T-018) and the use cases of T-020 and on.

Consistency guarantees:
  - atomic writes: a failed save never leaves a partial record (case 17);
  - compare-and-set on state changes: a transition is persisted only when
    the idea is still in the state the rule was computed from (RNF-9,
    case 11 — the second concurrent action is discarded);
  - creation and version application validate the 6 fields (RNF-5) and the
    proponent contact format (case 12).
"""

import copy
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from features.ideas.domain.idea import Idea
from features.ideas.domain.validate import validar_campos
from shared.exceptions.handlers import DomainError, ValidationFailed
from shared.utils.persistence import JsonStore

# `IdeaVersion` spec contracts (schema §2.5: `requestedBy` and `status`).
VERSION_ORIGINS: tuple[str, ...] = ("refinement", "improvement", "adjustment")
VERSION_STATES: tuple[str, ...] = ("PENDIENTE", "ACEPTADA", "DESCARTADA", "VIGENTE")


class StaleIdeaState(DomainError):
    """The idea moved to another state while the action was in flight (RNF-9, case 11)."""

    def __init__(self, idea_id: str, current: str, expected: str) -> None:
        super().__init__(
            "STALE_STATE",
            f"El estado de la idea cambió de {expected} a {current}; la acción se descarta (RNF-9).",
            status_code=409,
        )
        self.idea_id = idea_id
        self.current = current
        self.expected = expected


class IdeaStore:
    """JSON-backed idea ledger (ideas + versions), reference `IdeaLedger`.

    Records mirror `Idea.to_payload()` / schema §2.5, keyed by id in their
    own `JsonStore`. All reads return deep copies, mirroring `UserStore`.
    """

    def __init__(self, ideas: JsonStore, versions: JsonStore) -> None:
        self._ideas = ideas
        self._versions = versions

    # -- ideas (IdeaLedger contract) ------------------------------------------

    def create(self, idea: Idea) -> Idea:
        """Registers a new idea (RNF-5: the 6 fields must be complete)."""
        problems = validar_campos(idea.fields())
        if problems:
            raise ValidationFailed(
                "IDEA_FIELDS_INVALID",
                "La idea requiere los 6 campos completos (RNF-5) y un contacto con formato válido (caso 12).",
                details={"fields": problems},
            )
        if self.get(idea.id) is not None:
            raise DomainError("IDEA_EXISTS", "Ya existe una idea con ese identificador.", status_code=409)
        self._ideas.update(lambda data: {**data, idea.id: idea.to_payload()})
        return idea

    def get(self, idea_id: str) -> dict | None:
        payload = self._ideas.load().get(idea_id)
        return copy.deepcopy(payload) if payload is not None else None

    def get_idea(self, idea_id: str) -> Idea | None:
        payload = self.get(idea_id)
        return Idea.from_payload(payload) if payload is not None else None

    def list(self) -> list[dict]:
        return [copy.deepcopy(payload) for payload in self._ideas.load().values()]

    def list_by_state(self, state: str, owner_id: str | None = None) -> Sequence[dict]:
        return [
            payload
            for payload in self.list()
            if payload["state"] == state and (owner_id is None or payload["ownerId"] == owner_id)
        ]

    def list_by_origin(self, origin: str, state: str, owner_id: str | None = None) -> Sequence[dict]:
        return [
            payload
            for payload in self.list()
            if payload["origin"] == origin
            and payload["state"] == state
            and (owner_id is None or payload["ownerId"] == owner_id)
        ]

    def save_current_fields(self, idea_id: str, fields: dict) -> dict:
        """Contract entry: applies the 6 current fields (version acceptance)."""

        def apply(data: dict) -> dict:
            payload = data.get(idea_id)
            if payload is None:
                raise DomainError("IDEA_NOT_FOUND", "La idea no existe.", status_code=404)
            updated = Idea.from_payload(payload)
            updated.apply_fields(fields)
            return {**data, idea_id: updated.to_payload()}

        self._ideas.update(apply)
        return self.get(idea_id)  # type: ignore[return-value]

    def update(self, idea_id: str, changes: dict) -> dict:
        """Merges scalar payload changes (e.g. the `reviewedByAI` flag, T-020/T-024)."""

        def apply(data: dict) -> dict:
            payload = data.get(idea_id)
            if payload is None:
                raise DomainError("IDEA_NOT_FOUND", "La idea no existe.", status_code=404)
            return {**data, idea_id: {**payload, **changes}}

        self._ideas.update(apply)
        return self.get(idea_id)  # type: ignore[return-value]

    def update_state(self, idea: Idea, expected_state: str) -> Idea:
        """Persists the idea with compare-and-set (RNF-9, case 11).

        The (already domain-validated) `idea` is stored only if the persisted
        state is still `expected_state`; otherwise the action is discarded
        with `StaleIdeaState` and nothing changes on disk.
        """

        def apply(data: dict) -> dict:
            payload = data.get(idea.id)
            if payload is None:
                raise DomainError("IDEA_NOT_FOUND", "La idea no existe.", status_code=404)
            if payload["state"] != expected_state:
                raise StaleIdeaState(idea.id, payload["state"], expected_state)
            return {**data, idea.id: idea.to_payload()}

        self._ideas.update(apply)
        return idea

    # -- versions (IdeaVersion, schema §2.5) -----------------------------------

    def add_version(self, *, idea_id: str, fields: dict, requested_by: str,
                    generating: bool = False) -> dict:
        """Registers a PENDIENTE version of a registered idea (RF-8/RF-11/RF-13).

        With `generating`, the idea is additionally flagged `generando` in its
        own record (RF-9/RNF-9: manual editing is blocked while the assistant
        is producing the version).
        """
        if self.get(idea_id) is None:
            raise DomainError("IDEA_NOT_FOUND", "La versión requiere una idea registrada.", status_code=404)
        if requested_by not in VERSION_ORIGINS:
            raise DomainError(
                "UNKNOWN_VERSION_ORIGIN",
                f"Origen de versión no válido: «{requested_by}» (solo {', '.join(VERSION_ORIGINS)}).",
                status_code=400,
            )
        problems = validar_campos(fields)
        if problems:
            raise ValidationFailed(
                "VERSION_FIELDS_INVALID",
                "La versión propuesta requiere los 6 campos completos (RNF-5) y un contacto válido (caso 12).",
                details={"fields": problems},
            )
        numbers = [entry["version"] for entry in self._versions.load().values() if entry["ideaId"] == idea_id]
        next_number = max(numbers, default=0) + 1
        version_id = f"ver_{idea_id}_{next_number:02d}"
        payload: dict[str, Any] = {
            "id": version_id,
            "ideaId": idea_id,
            "version": next_number,
            "fields": copy.deepcopy(fields),
            "requestedBy": requested_by,
            "status": "PENDIENTE",
            "createdAt": datetime.now().isoformat(),
        }

        def apply(data: dict) -> dict:
            if version_id in data:
                raise DomainError("VERSION_EXISTS", "Ya existe una versión con ese identificador.",
                                  status_code=409)
            return {**data, version_id: payload}

        self._versions.update(apply)
        if generating:
            self.update(idea_id, {"generando": True})
        return self.get_version(idea_id, version_id)  # type: ignore[return-value]

    def get_version(self, idea_id: str, version_id: str) -> dict | None:
        payload = self._versions.load().get(version_id)
        if payload is None or payload.get("ideaId") != idea_id:
            return None
        return copy.deepcopy(payload)

    def versions_of(self, idea_id: str) -> Sequence[dict]:
        """All versions of the idea, oldest to newest."""
        return sorted(
            (copy.deepcopy(v) for v in self._versions.load().values() if v["ideaId"] == idea_id),
            key=lambda entry: entry["version"],
        )

    def decide(self, *, idea_id: str, version_id: str, accept: bool,
               fields: dict | None = None) -> dict:
        """Accepts or discards a PENDIENTE version (RF-8, RF-13; decision once).

        Discarding marks the version DESCARTADA and leaves the idea untouched.
        Accepting makes the version VIGENTE: the idea adopts its fields (or
        `fields` when provided), is marked `reviewedByAI`, and its
        `currentVersionId` moves to it — the idea keeps its current state
        (decision #1); the previously current version is marked ACEPTADA.
        Either way the `generando` flag is cleared: the version the assistant
        was producing has been resolved, so manual editing unblocks (RF-9).
        """
        version = self.get_version(idea_id, version_id)
        if version is None:
            raise DomainError("VERSION_NOT_FOUND", "La versión no existe.", status_code=404)
        if version["status"] != "PENDIENTE":
            raise DomainError(
                "VERSION_ALREADY_DECIDED",
                f"La versión {version_id} ya fue decidida (estado «{version['status']}»).",
                status_code=409,
            )
        idea_payload = self.get(idea_id)
        if idea_payload is None:
            raise DomainError("IDEA_NOT_FOUND", "La idea no existe.", status_code=404)

        previous_version_id: str | None = None
        if accept:
            previous_version_id = idea_payload.get("currentVersionId")
            proposed = copy.deepcopy(fields if fields is not None else version["fields"])
            updated = Idea.from_payload(idea_payload)
            try:
                updated.apply_fields(proposed)
            except DomainError:
                raise ValidationFailed(
                    "VERSION_FIELDS_INVALID",
                    "La versión propuesta no es válida: los 6 campos deben estar completos y el "
                    "contacto debe tener un formato válido (RNF-5, caso 12).",
                ) from None
            updated.currentVersionId = version_id
            updated.reviewedByAI = True
            self._ideas.update(lambda data: {**data, idea_id: updated.to_payload()})

        target_status = "VIGENTE" if accept else "DESCARTADA"

        def apply_versions(data: dict) -> dict:
            if data[version_id]["status"] != "PENDIENTE":
                raise DomainError("VERSION_ALREADY_DECIDED",
                                  f"La versión {version_id} ya fue decidida.", status_code=409)
            result = {**data, version_id: {**data[version_id], "status": target_status}}
            if accept and previous_version_id and previous_version_id in result:
                previous = result[previous_version_id]
                if previous["status"] == "VIGENTE":
                    result[previous_version_id] = {**previous, "status": "ACEPTADA"}
            return result

        self._versions.update(apply_versions)
        if idea_payload.get("generando") and not any(
            entry["status"] == "PENDIENTE" for entry in self.versions_of(idea_id)
        ):
            self.update(idea_id, {"generando": False})
        return self.get_version(idea_id, version_id)  # type: ignore[return-value]
