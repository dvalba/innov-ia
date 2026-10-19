"""Ideas listings tests (T-022, RF-19/RF-20, RNF-7).

Covers the owner filter of "Mis ideas" (only the user's ideas, any state,
RF-19 summary), the public catalog state filter (only `VALIDADA_PUBLICA`,
any owner, RF-20/decision #2) and the suppression of the proponent's
`contact` in the catalog (RNF-7, spec §5.9).
"""

import pathlib

import pytest

from features.ideas.infrastructure.idea_store import IdeaStore
from features.ideas.use_cases.create_idea import create_idea
from features.ideas.use_cases.list_my_ideas import list_my_ideas
from features.ideas.use_cases.list_public import list_public
from shared.contracts.idea_ledger import IDEA_FIELDS
from shared.utils.persistence import JsonStore

SUMMARY_KEYS = {"id", "title", "createdAt", "origin", "state"}


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


def _idea(store: IdeaStore, owner_id: str = "u_ana", origin: str = "manual",
          title: str = "Idea", **overrides: object) -> dict:
    fields = _fields(title=title)
    fields.update(overrides)
    return create_idea(store, owner_id=owner_id, origin=origin, fields=fields)


def _dated(store: IdeaStore, payload: dict, created_at: str) -> dict:
    return store.update(payload["id"], {"createdAt": created_at})


# -- Mis ideas (RF-19, RNF-7) ----------------------------------------------------


def test_list_my_ideas_returns_only_the_owner_ideas_with_the_summary(store: IdeaStore) -> None:
    mine_a = _idea(store, owner_id="u_ana", title="A")
    mine_b = _idea(store, owner_id="u_ana", title="B")
    other = _idea(store, owner_id="u_carlos", title="C")

    entries = list_my_ideas(store, owner_id="u_ana")
    assert {entry["id"] for entry in entries} == {mine_a["id"], mine_b["id"]}
    for entry in entries:
        assert set(entry) == SUMMARY_KEYS
        assert "contact" not in str(entry)  # RF-19 summary: no proponent data beyond the fields
    assert other["id"] not in {entry["id"] for entry in entries}
    assert len(entries) == 2


def test_list_my_ideas_includes_any_state(store: IdeaStore) -> None:
    _idea(store, owner_id="u_ana", title="En desarrollo")
    requesting = _idea(store, owner_id="u_ana", title="Solicitando")
    validated = _idea(store, owner_id="u_ana", title="Validada")
    store.update(requesting["id"], {"state": "SOLICITANDO_PUBLICACION", "requestDate": "2026-10-01T00:00:00"})
    store.update(validated["id"], {"state": "VALIDADA_PUBLICA", "publishedBy": "u_exp", "publishedAt": "2026-10-01T00:00:00"})

    states = {entry["state"] for entry in list_my_ideas(store, owner_id="u_ana")}
    assert states == {"EN_DESARROLLO", "SOLICITANDO_PUBLICACION", "VALIDADA_PUBLICA"}
    assert len(states) == 3


def test_list_my_ideas_is_sorted_newest_to_oldest(store: IdeaStore) -> None:
    old = _idea(store, title="Antigua")
    middle = _idea(store, title="Media")
    recent = _idea(store, title="Reciente")
    _dated(store, old, "2026-09-01T08:00:00")
    _dated(store, middle, "2026-09-15T08:00:00")
    _dated(store, recent, "2026-09-30T08:00:00")

    entries = list_my_ideas(store, owner_id="u_ana")
    assert [entry["title"] for entry in entries] == ["Reciente", "Media", "Antigua"]


def test_list_my_ideas_is_empty_for_a_user_without_ideas(store: IdeaStore) -> None:
    _idea(store, owner_id="u_ana")
    assert list_my_ideas(store, owner_id="u_sin_ideas") == []


# -- Catálogo público (RF-20, RNF-7) ----------------------------------------------


def test_list_public_returns_only_validada_publica_of_any_owner(store: IdeaStore) -> None:
    in_dev = _idea(store, owner_id="u_ana", title="Borrador visible")
    requesting = _idea(store, owner_id="u_carlos", title="En cola")
    published_a = _idea(store, owner_id="u_ana", title="Publicada A")
    published_b = _idea(store, owner_id="u_carlos", title="Publicada B")
    store.update(requesting["id"], {"state": "SOLICITANDO_PUBLICACION", "requestDate": "2026-10-01T00:00:00"})
    store.update(published_a["id"], {"state": "VALIDADA_PUBLICA", "publishedAt": "2026-10-01T09:00:00", "publishedBy": "u_exp"})
    store.update(published_b["id"], {"state": "VALIDADA_PUBLICA", "publishedAt": "2026-10-01T10:00:00", "publishedBy": "u_exp"})

    entries = list_public(store)
    assert {entry["id"] for entry in entries} == {published_a["id"], published_b["id"]}
    for excluded in (in_dev["id"], requesting["id"]):
        assert excluded not in {entry["id"] for entry in entries}


def test_list_public_exposes_the_7_fields_without_the_proponent_contact(store: IdeaStore) -> None:
    published = _idea(store, owner_id="u_ana")
    store.update(published["id"], {"state": "VALIDADA_PUBLICA", "publishedAt": "2026-10-01T09:00:00"})

    (entry,) = list_public(store)
    assert set(entry["fields"]) == set(IDEA_FIELDS)
    proponent = entry["fields"]["proponent"]
    assert set(proponent) == {"name", "area"}  # contact suppressed (RF-20/RNF-7)
    assert "contact" not in str(entry)
    assert "publishedAt" in entry and "createdAt" in entry


def test_list_public_is_sorted_newest_to_oldest(store: IdeaStore) -> None:
    old = _idea(store, title="A")
    recent = _idea(store, title="B")
    _dated(store, old, "2026-09-01T08:00:00")
    _dated(store, recent, "2026-09-30T08:00:00")
    store.update(old["id"], {"state": "VALIDADA_PUBLICA", "publishedAt": "2026-09-01T09:00:00"})
    store.update(recent["id"], {"state": "VALIDADA_PUBLICA", "publishedAt": "2026-09-30T09:00:00"})

    entries = list_public(store)
    assert [entry["fields"]["title"] for entry in entries] == ["B", "A"]


def test_list_public_is_empty_when_nothing_is_published(store: IdeaStore) -> None:
    _idea(store, owner_id="u_ana")
    requesting = _idea(store, owner_id="u_carlos")
    store.update(requesting["id"], {"state": "SOLICITANDO_PUBLICACION", "requestDate": "2026-10-01T00:00:00"})
    assert list_public(store) == []
