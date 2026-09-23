"""IdeaStore tests (T-019, decision D1): persistence, IdeaLedger contract and consistency.

Uses real `JsonStore` over `tmp_path` (no in-memory override here, the atomic
write failures are exercised on the file store itself).
"""

import pathlib

import pytest

from features.ideas.domain.idea import Idea
from features.ideas.infrastructure.idea_store import IdeaStore, StaleIdeaState
from shared.contracts.idea_ledger import IdeaLedger
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
        "estimatedResources": {"time": "6 semanas", "people": "2 personas", "budget": "50000 PLN"},
    }
    base.update(overrides)
    return base


def _idea_payload(idea_id: str = "idea_a", owner_id: str = "u_ana", origin: str = "asistida",
                  state: str = "EN_DESARROLLO", **ideakwargs: object) -> dict:
    payload = {
        "id": idea_id,
        "ownerId": owner_id,
        "origin": origin,
        "state": state,
        "reviewedByAI": False,
        "currentVersionId": None,
        "createdAt": "2026-09-23T08:00:00",
        "requestDate": None,
        "publishedAt": None,
        "publishedBy": None,
        "rejectionNote": None,
    }
    payload.update(_fields())
    payload.update(ideakwargs)
    return payload


def _idea(idea_id: str = "idea_a", owner_id: str = "u_ana", state: str = "EN_DESARROLLO") -> Idea:
    return Idea.from_payload(_idea_payload(idea_id, owner_id, state=state))


@pytest.fixture()
def store(tmp_path: pathlib.Path) -> IdeaStore:
    return IdeaStore(
        JsonStore(tmp_path / "ideas.json"),
        JsonStore(tmp_path / "versions.json"),
    )


# -- the shared contract -------------------------------------------------------


def test_store_is_the_reference_idea_ledger(store: IdeaStore) -> None:
    assert isinstance(store, IdeaLedger)


# -- save and load -------------------------------------------------------------


def test_create_get_and_persist_across_instances(store: IdeaStore, tmp_path: pathlib.Path) -> None:
    store.create(_idea())
    payload = store.get("idea_a")
    assert payload is not None
    assert payload["state"] == "EN_DESARROLLO"
    assert payload["proponent"]["contact"] == "ana.torres@innov-ia.local"

    fresh = IdeaStore(JsonStore(tmp_path / "ideas.json"), JsonStore(tmp_path / "versions.json"))
    assert fresh.get("idea_a") == payload  # persisted on disk, reloaded


def test_get_missing_returns_none(store: IdeaStore) -> None:
    assert store.get("nope") is None
    assert store.get_idea("nope") is None


def test_create_rejects_duplicate_id(store: IdeaStore) -> None:
    store.create(_idea())
    with pytest.raises(DomainError) as error:
        store.create(_idea())
    assert error.value.status_code == 409


def test_create_rejects_incomplete_fields_without_leaving_a_record(store: IdeaStore) -> None:
    idea = _idea("idea_incompleta", state="EN_DESARROLLO")
    idea.problem = "   "
    with pytest.raises(ValidationFailed) as error:
        store.create(idea)
    assert error.value.code == "IDEA_FIELDS_INVALID"
    assert "problem" in error.value.details["fields"]
    assert store.list() == []  # case 17: no partial record


def test_create_rejects_an_invalid_contact_store(store: IdeaStore) -> None:
    idea = _idea("idea_contacto")
    idea.proponent = {"name": "Ana", "area": "Compras", "contact": "telefono??"}
    with pytest.raises(ValidationFailed) as error:
        store.create(idea)
    assert "proponent" in error.value.details["fields"]
    assert store.list() == []


# -- listing (RF-19 / queue of RF-11 / RF-14) -----------------------------------


def test_list_by_state_and_by_owner(store: IdeaStore) -> None:
    store.create(_idea("idea_a", "u_ana", state="EN_DESARROLLO"))
    store.create(_idea("idea_b", "u_beto", state="SOLICITANDO_PUBLICACION"))
    store.create(_idea("idea_c", "u_ana", state="SOLICITANDO_PUBLICACION"))

    assert [p["id"] for p in store.list_by_state("SOLICITANDO_PUBLICACION")] == ["idea_b", "idea_c"]
    assert [p["id"] for p in store.list_by_state("SOLICITANDO_PUBLICACION", owner_id="u_ana")] == ["idea_c"]
    assert [p["id"] for p in store.list_by_state("EN_DESARROLLO")] == ["idea_a"]
    assert store.list_by_state("VALIDADA_PUBLICA") == []


def test_list_by_origin_and_state_filters_the_refinement_queue(store: IdeaStore) -> None:
    store.create(Idea.from_payload(_idea_payload("idea_m", origin="manual")))
    store.create(Idea.from_payload(_idea_payload("idea_as", origin="asistida")))
    store.create(Idea.from_payload(_idea_payload("idea_m2", owner_id="u_beto", origin="manual",
                                                state="SOLICITANDO_PUBLICACION")))

    queue = store.list_by_origin("manual", "EN_DESARROLLO")
    assert [p["id"] for p in queue] == ["idea_m"]
    assert [p["id"] for p in store.list_by_origin("manual", "SOLICITANDO_PUBLICACION")] == ["idea_m2"]
    assert [p["id"] for p in store.list_by_origin("asistida", "EN_DESARROLLO")] == ["idea_as"]


def test_reads_return_copies(store: IdeaStore) -> None:
    store.create(_idea())
    payload = store.get("idea_a")
    payload["state"] = "VALIDADA_PUBLICA"  # mutating a read must not leak
    assert store.get("idea_a")["state"] == "EN_DESARROLLO"


# -- compare-and-set (RNF-9, case 11) --------------------------------------------


def test_update_state_persists_when_state_matches(store: IdeaStore) -> None:
    store.create(_idea())
    idea = store.get_idea("idea_a")
    idea.state = "SOLICITANDO_PUBLICACION"
    idea.requestDate = "2026-09-23T09:00:00"
    store.update_state(idea, expected_state="EN_DESARROLLO")
    assert store.get("idea_a")["state"] == "SOLICITANDO_PUBLICACION"
    assert store.get("idea_a")["requestDate"] == "2026-09-23T09:00:00"


def test_update_state_discards_when_the_state_moved_first(store: IdeaStore) -> None:
    store.create(_idea())
    stored = store.get_idea("idea_a")
    stored.state = "SOLICITANDO_PUBLICACION"
    store.update_state(stored, expected_state="EN_DESARROLLO")  # first action wins

    late = store.get_idea("idea_a")
    late.state = "VALIDADA_PUBLICA"  # a concurrent/late action
    with pytest.raises(StaleIdeaState) as error:
        store.update_state(late, expected_state="EN_DESARROLLO")
    assert error.value.status_code == 409
    assert store.get("idea_a")["state"] == "SOLICITANDO_PUBLICACION"  # discarded, no inconsistency


def test_update_state_missing_idea_is_404(store: IdeaStore) -> None:
    with pytest.raises(DomainError) as error:
        store.update_state(_idea("nope"), expected_state="EN_DESARROLLO")
    assert error.value.status_code == 404


def test_failed_writes_leave_no_partial_record(store: IdeaStore, tmp_path: pathlib.Path, monkeypatch) -> None:
    store.create(_idea())

    def broken_replace(source: pathlib.Path, destination: pathlib.Path) -> Exception:
        raise OSError("simulated disk failure while replacing the file")

    monkeypatch.setattr("os.replace", broken_replace)
    stored = store.get_idea("idea_a")
    stored.state = "SOLICITANDO_PUBLICACION"
    with pytest.raises(OSError):
        store.update_state(stored, expected_state="EN_DESARROLLO")
    assert store.get("idea_a")["state"] == "EN_DESARROLLO"  # case 17
    assert not (tmp_path / "ideas.json.tmp").exists()


def test_failing_mutator_leaves_the_previous_file(store: IdeaStore) -> None:
    store.create(_idea())
    payload_before = store.get("idea_a")
    with pytest.raises(DomainError):
        store.save_current_fields("nope", _fields())
    assert store.get("idea_a") == payload_before


# -- versions (IdeaVersion, §2.5) --------------------------------------------------


def test_add_version_registers_a_pending_numbered_version(store: IdeaStore) -> None:
    store.create(_idea())
    first = store.add_version(idea_id="idea_a", fields=_fields(title="Mejora"), requested_by="improvement")
    assert first["id"] == "ver_idea_a_01"
    assert first["version"] == 1
    assert first["status"] == "PENDIENTE"
    assert first["requestedBy"] == "improvement"
    assert first["fields"]["title"] == "Mejora"
    assert first["createdAt"]

    second = store.add_version(idea_id="idea_a", fields=_fields(), requested_by="refinement")
    assert second["id"] == "ver_idea_a_02"
    assert [v["id"] for v in store.versions_of("idea_a")] == ["ver_idea_a_01", "ver_idea_a_02"]


def test_add_version_validates_the_idea_the_origin_and_the_fields(store: IdeaStore) -> None:
    with pytest.raises(DomainError) as error:
        store.add_version(idea_id="nope", fields=_fields(), requested_by="improvement")
    assert error.value.status_code == 404

    store.create(_idea())
    with pytest.raises(DomainError) as error:
        store.add_version(idea_id="idea_a", fields=_fields(), requested_by="manual")
    assert error.value.status_code == 400

    with pytest.raises(ValidationFailed) as error:
        store.add_version(idea_id="idea_a", fields=_fields(description=""), requested_by="improvement")
    assert "description" in error.value.details["fields"]
    assert list(store.versions_of("idea_a")) == []


def test_versions_are_persisted_across_instances(store: IdeaStore, tmp_path: pathlib.Path) -> None:
    store.create(_idea())
    store.add_version(idea_id="idea_a", fields=_fields(), requested_by="improvement")
    fresh = IdeaStore(JsonStore(tmp_path / "ideas.json"), JsonStore(tmp_path / "versions.json"))
    assert [v["id"] for v in fresh.versions_of("idea_a")] == ["ver_idea_a_01"]
    assert fresh.get_version("idea_a", "ver_idea_a_01") is not None
    assert fresh.get_version("idea_a", "ver_idea_a_99") is None


def test_get_version_is_scoped_to_the_idea(store: IdeaStore) -> None:
    store.create(_idea("idea_a"))
    store.create(_idea("idea_b"))
    store.add_version(idea_id="idea_a", fields=_fields(), requested_by="improvement")
    assert store.get_version("idea_b", "ver_idea_a_01") is None  # not its version


def test_discard_keeps_the_idea_and_blocks_the_second_decision(store: IdeaStore) -> None:
    store.create(_idea())
    before = store.get("idea_a")
    store.add_version(idea_id="idea_a", fields=_fields(title="Candidata"), requested_by="improvement")

    version = store.decide(idea_id="idea_a", version_id="ver_idea_a_01", accept=False)
    assert version["status"] == "DESCARTADA"
    assert store.get("idea_a") == before  # the idea is untouched
    assert store.get_idea("idea_a").currentVersionId is None
    assert store.get_idea("idea_a").reviewedByAI is False

    with pytest.raises(DomainError) as error:
        store.decide(idea_id="idea_a", version_id="ver_idea_a_01", accept=True)
    assert error.value.status_code == 409


def test_accept_makes_the_version_current_and_keeps_the_state_decision_1(store: IdeaStore) -> None:
    store.create(_idea("idea_a", state="EN_DESARROLLO"))
    store.add_version(idea_id="idea_a", fields=_fields(title="Versión final"), requested_by="refinement")

    version = store.decide(idea_id="idea_a", version_id="ver_idea_a_01", accept=True)
    assert version["status"] == "VIGENTE"
    idea = store.get("idea_a")
    assert idea["title"] == "Versión final"  # fields applied to the idea
    assert idea["currentVersionId"] == "ver_idea_a_01"
    assert idea["reviewedByAI"] is True
    assert idea["state"] == "EN_DESARROLLO"  # decision #1: acceptance does not publish


def test_accept_supersedes_the_previous_current_version(store: IdeaStore) -> None:
    store.create(_idea())
    v1 = store.add_version(idea_id="idea_a", fields=_fields(title="V1"), requested_by="refinement")
    store.decide(idea_id="idea_a", version_id=v1["id"], accept=True)
    v2 = store.add_version(idea_id="idea_a", fields=_fields(title="V2"), requested_by="improvement")
    store.decide(idea_id="idea_a", version_id=v2["id"], accept=True)

    ideas = store.get_idea("idea_a")
    assert ideas.currentVersionId == v2["id"]
    assert ideas.title == "V2"
    statuses = {v["id"]: v["status"] for v in store.versions_of("idea_a")}
    assert statuses == {v1["id"]: "ACEPTADA", v2["id"]: "VIGENTE"}


def test_accept_with_overridden_fields_and_decide_errors(store: IdeaStore) -> None:
    store.create(_idea())
    version = store.add_version(idea_id="idea_a", fields=_fields(title="Base"), requested_by="improvement")
    store.decide(idea_id="idea_a", version_id=version["id"], accept=True,
                 fields=_fields(title="Ajustada en el chat"))
    assert store.get("idea_a")["title"] == "Ajustada en el chat"

    with pytest.raises(DomainError) as error:
        store.decide(idea_id="idea_a", version_id="nope", accept=True)
    assert error.value.status_code == 404


def test_save_current_fields_applies_and_404s_on_missing(store: IdeaStore) -> None:
    store.create(_idea())
    updated = store.save_current_fields("idea_a", _fields(title="Campos guardados"))
    assert updated["title"] == "Campos guardados"
    with pytest.raises(DomainError) as error:
        store.save_current_fields("nope", _fields())
    assert error.value.status_code == 404


def test_update_merges_scalar_changes(store: IdeaStore) -> None:
    store.create(_idea())
    updated = store.update("idea_a", {"reviewedByAI": True})
    assert updated["reviewedByAI"] is True
    with pytest.raises(DomainError):
        store.update("nope", {"reviewedByAI": True})


# -- generation flag (RF-9, T-020/T-024) -----------------------------------------


def test_add_version_with_generating_flags_the_idea(store: IdeaStore) -> None:
    store.create(_idea())
    store.add_version(idea_id="idea_a", fields=_fields(title="Generada"),
                      requested_by="improvement", generating=True)
    flag = store.get("idea_a")
    assert flag["generando"] is True
    # the idea is fully intact aside from the flag
    assert flag["title"] == "Optimización del proceso de aprobación de proveedores"


def test_add_version_without_generating_leaves_the_idea_unflagged(store: IdeaStore) -> None:
    store.create(_idea())
    store.add_version(idea_id="idea_a", fields=_fields(), requested_by="refinement")
    assert store.get("idea_a")["generando"] is False
    assert Idea.from_payload(store.get("idea_a")).generando is False  # round trip


def test_generating_flag_survives_between_instances(store: IdeaStore, tmp_path: pathlib.Path) -> None:
    store.create(_idea())
    store.add_version(idea_id="idea_a", fields=_fields(), requested_by="improvement", generating=True)
    fresh = IdeaStore(JsonStore(tmp_path / "ideas.json"), JsonStore(tmp_path / "versions.json"))
    assert fresh.get("idea_a")["generando"] is True


def test_decide_clears_the_generating_flag(store: IdeaStore) -> None:
    store.create(_idea())
    version = store.add_version(idea_id="idea_a", fields=_fields(title="Final"),
                                requested_by="improvement", generating=True)
    store.decide(idea_id="idea_a", version_id=version["id"], accept=False)
    assert store.get("idea_a")["generando"] is False


def test_deciding_a_pending_version_while_another_generation_runs_keeps_the_flag(store: IdeaStore) -> None:
    store.create(_idea())
    first = store.add_version(idea_id="idea_a", fields=_fields(title="Una"), requested_by="improvement",
                              generating=True)
    store.add_version(idea_id="idea_a", fields=_fields(title="Dos"), requested_by="improvement")
    store.decide(idea_id="idea_a", version_id=first["id"], accept=True)
    assert store.get("idea_a")["generando"] is True  # the second generation is still in flight
    store.decide(idea_id="idea_a", version_id="ver_idea_a_02", accept=False)
    assert store.get("idea_a")["generando"] is False
