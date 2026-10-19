"""Ideas use cases tests (T-020, RF-9, RNF-5): creation and manual editing.

Covers idea registration (the 7 mandatory fields, origin, owner), manual
editing while the idea is in EN_DESARROLLO, the edit block while the
assistant is generating a version (409, `generando` flag), non-owner
editing (403) and editing outside EN_DESARROLLO (409).
"""

import pathlib

import pytest

from features.ideas.infrastructure.idea_store import IdeaStore
from features.ideas.use_cases.create_idea import create_idea
from features.ideas.use_cases.edit_idea import edit_idea
from shared.exceptions.handlers import DomainError, ValidationFailed
from shared.utils.persistence import JsonStore


def _fields(**overrides: object) -> dict:
    base: dict = {
        "title": "Optimización del proceso de aprobación de proveedores",
        "proponent": {"name": "Ana Torres", "area": "Compras", "contact": "ana.torres@innov-ia.local"},
        "description": "Digitalizar la validación de proveedores eliminando la revisión manual duplicada.",
        "problem": "Tres revisiones manuales independientes que duplican esfuerzo.",
        "expectedBenefit": "Ahorro de 120 horas mensuales de personal.",
        "strategicAlignment": "Agilizar la cadena de suministro de la empresa.",
    }
    base.update(overrides)
    return base


@pytest.fixture()
def store(tmp_path: pathlib.Path) -> IdeaStore:
    return IdeaStore(
        JsonStore(tmp_path / "ideas.json"),
        JsonStore(tmp_path / "versions.json"),
    )


def _created(store: IdeaStore, owner_id: str = "u_ana", origin: str = "manual") -> dict:
    payload = create_idea(store, owner_id=owner_id, origin=origin, fields=_fields())
    assert payload["state"] == "EN_DESARROLLO"
    return payload


# -- create (RNF-5, RF-6/RF-7 origins) ----------------------------------------


def test_create_idea_registers_a_complete_idea_in_en_desarrollo(store: IdeaStore) -> None:
    payload = create_idea(store, owner_id="u_ana", origin="asistida", fields=_fields())
    assert payload["ownerId"] == "u_ana"
    assert payload["origin"] == "asistida"
    assert payload["state"] == "EN_DESARROLLO"
    assert payload["createdAt"]
    assert payload["id"]
    assert store.get(payload["id"]) == payload  # persisted with the 7 fields


def test_create_idea_persists_across_instances(store: IdeaStore, tmp_path: pathlib.Path) -> None:
    payload = create_idea(store, owner_id="u_ana", origin="manual", fields=_fields())
    fresh = IdeaStore(JsonStore(tmp_path / "ideas.json"), JsonStore(tmp_path / "versions.json"))
    assert fresh.get(payload["id"]) == payload


def test_create_idea_rejects_incomplete_fields_without_leaving_a_record(store: IdeaStore) -> None:
    with pytest.raises(ValidationFailed) as error:
        create_idea(store, owner_id="u_ana", origin="manual",
                    fields=_fields(problem="", expectedBenefit="   "))
    assert error.value.code == "IDEA_FIELDS_INVALID"
    assert set(error.value.details["fields"]) == {"problem", "expectedBenefit"}
    assert store.list() == []  # case 17 / RNF-5: no partial record


def test_create_idea_rejects_an_invalid_contact(store: IdeaStore) -> None:
    with pytest.raises(ValidationFailed) as error:
        create_idea(store, owner_id="u_ana", origin="manual",
                    fields=_fields(proponent={"name": "Ana", "area": "Compras", "contact": "???"}))
    assert "proponent" in error.value.details["fields"]
    assert store.list() == []


def test_create_idea_rejects_unknown_origin(store: IdeaStore) -> None:
    with pytest.raises(DomainError) as error:
        create_idea(store, owner_id="u_ana", origin="robotica", fields=_fields())
    assert error.value.status_code == 400
    assert store.list() == []


# -- edit (RF-9) ---------------------------------------------------------------


def test_edit_idea_updates_the_fields_and_preserves_the_identity(store: IdeaStore) -> None:
    created = _created(store)
    updated = edit_idea(store, idea_id=created["id"], owner_id="u_ana",
                        fields=_fields(title="Título revisado", problem="Nuevo planteamiento."))
    assert updated["title"] == "Título revisado"
    assert updated["problem"] == "Nuevo planteamiento."
    assert updated["id"] == created["id"]
    assert updated["ownerId"] == "u_ana"
    assert updated["origin"] == created["origin"]
    assert updated["state"] == "EN_DESARROLLO"
    assert updated["createdAt"] == created["createdAt"]
    assert store.get(created["id"]) == updated


def test_edit_idea_of_a_missing_idea_is_404(store: IdeaStore) -> None:
    with pytest.raises(DomainError) as error:
        edit_idea(store, idea_id="nope", owner_id="u_ana", fields=_fields())
    assert error.value.status_code == 404
    assert error.value.code == "IDEA_NOT_FOUND"


def test_edit_idea_by_a_non_owner_is_403_and_changes_nothing(store: IdeaStore) -> None:
    created = _created(store, owner_id="u_ana")
    with pytest.raises(DomainError) as error:
        edit_idea(store, idea_id=created["id"], owner_id="u_otro",
                  fields=_fields(title="Robado"))
    assert error.value.status_code == 403
    assert error.value.code == "NOT_IDEA_OWNER"
    assert store.get(created["id"])["title"] == created["title"]


def test_edit_idea_is_blocked_with_409_while_a_generation_is_in_flight(store: IdeaStore) -> None:
    created = _created(store)
    store.add_version(idea_id=created["id"], fields=_fields(title="Candidate"),
                      requested_by="improvement", generating=True)
    assert store.get(created["id"])["generando"] is True

    with pytest.raises(DomainError) as error:
        edit_idea(store, idea_id=created["id"], owner_id="u_ana",
                  fields=_fields(title="Edición durante generación"))
    assert error.value.status_code == 409
    assert error.value.code == "GENERATION_IN_PROGRESS"
    assert store.get(created["id"])["title"] == created["title"]


def test_edit_idea_unblocks_once_the_pending_version_is_decided(store: IdeaStore) -> None:
    created = _created(store)
    version = store.add_version(idea_id=created["id"], fields=_fields(title="Candidate"),
                                requested_by="improvement", generating=True)
    store.decide(idea_id=created["id"], version_id=version["id"], accept=False)
    assert store.get(created["id"])["generando"] is False

    updated = edit_idea(store, idea_id=created["id"], owner_id="u_ana",
                        fields=_fields(title="Edición tras decidir"))
    assert updated["title"] == "Edición tras decidir"


def test_edit_idea_outside_en_desarrollo_is_409(store: IdeaStore) -> None:
    for state in ("SOLICITANDO_PUBLICACION", "VALIDADA_PUBLICA"):
        created = _created(store, owner_id="u_" + state[:3])
        store.update(created["id"], {"state": state})
        with pytest.raises(DomainError) as error:
            edit_idea(store, idea_id=created["id"], owner_id=f"u_{state[:3]}",
                      fields=_fields(title="Tarde"))
        assert error.value.status_code == 409


def test_edit_idea_rejects_incomplete_fields_with_422(store: IdeaStore) -> None:
    created = _created(store)
    with pytest.raises(ValidationFailed) as error:
        edit_idea(store, idea_id=created["id"], owner_id="u_ana",
                  fields=_fields(strategicAlignment=""))
    assert error.value.code == "IDEA_FIELDS_INVALID"
    assert error.value.details["fields"] == ["strategicAlignment"]
    assert store.get(created["id"])["strategicAlignment"] == created["strategicAlignment"]
