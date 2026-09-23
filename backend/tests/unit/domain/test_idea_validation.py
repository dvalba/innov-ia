"""Idea domain tests (T-017, RF-9/RF-19, RNF-5): entity, completeness and contact format (case 12).

Pure domain: no FastAPI/Pydantic imports are allowed here.
"""

import pytest

from features.ideas.domain.idea import ORIGINS, STATES, Idea, IdeaError
from features.ideas.domain.validate import (
    campos_completos,
    campos_incompletos,
    contacto_valido,
    validar_campos,
)
from shared.exceptions.handlers import DomainError


def _fields(**overrides: object) -> dict:
    """A dict of complete 7 fields, open to pinpoint overrides per test."""
    base: dict = {
        "title": "Optimización del proceso de aprobación de proveedores",
        "proponent": {"name": "Ana Torres", "area": "Compras", "contact": "ana.torres@innov-ia.local"},
        "description": "Digitalizar la validación de proveedores eliminando la revisión manual duplicada entre áreas.",
        "problem": "El proceso actual exige tres revisiones manuales independientes que duplican esfuerzo.",
        "expectedBenefit": "Ahorro de 120 horas por mes de personal.",
        "strategicAlignment": "Agilizar la cadena de suministro y reducir carga administrativa manual.",
        "estimatedResources": {"time": "6 semanas", "people": "2 desarrolladores", "budget": "50000 PLN"},
    }
    base.update(overrides)
    return base


def _idea(**overrides: object) -> Idea:
    data = {
        "id": "idea_1",
        "ownerId": "u_ana",
        "origin": "manual",
        "state": "EN_DESARROLLO",
    }
    data.update(_fields())
    data.update(overrides)
    return Idea(**data)


# -- IDEA_FIELDS / contracts -------------------------------------------------


def test_seven_fields_match_the_contract() -> None:
    assert tuple(_fields()) == (
        "title",
        "proponent",
        "description",
        "problem",
        "expectedBenefit",
        "strategicAlignment",
        "estimatedResources",
    )


# -- the entity ----------------------------------------------------------------


def test_idea_holds_the_seven_fields_and_the_spec_attributes() -> None:
    idea = _idea()
    assert set(idea.fields()) == {
        "title", "proponent", "description", "problem",
        "expectedBenefit", "strategicAlignment", "estimatedResources",
    }
    assert idea.fields()["proponent"]["name"] == "Ana Torres"
    assert idea.origin in ORIGINS
    assert idea.state in STATES
    assert idea.reviewedByAI is False
    assert idea.currentVersionId is None
    assert idea.publishedBy is None


def test_idea_payload_round_trip_is_lossless() -> None:
    idea = _idea(reviewedByAI=True, currentVersionId="ver_01", requestDate="2026-09-16T10:00:00")
    assert Idea.from_payload(idea.to_payload()) == idea


def test_idea_requires_id_and_owner() -> None:
    with pytest.raises(DomainError) as error:
        _idea(id="")
    assert error.value.status_code == 400
    with pytest.raises(DomainError) as error:
        _idea(ownerId="   ")
    assert error.value.status_code == 400


def test_idea_rejects_unknown_origin_and_state() -> None:
    with pytest.raises(DomainError):
        _idea(origin="robotica")
    with pytest.raises(DomainError):
        _idea(state="EN_DEBATE")


def test_from_payload_reports_the_missing_key() -> None:
    payload = _idea().to_payload()
    del payload["expectedBenefit"]
    with pytest.raises(IdeaError, match="expectedBenefit"):
        Idea.from_payload(payload)


def test_apply_fields_updates_the_seven_fields_and_rejects_incomplete() -> None:
    idea = _idea()
    idea.apply_fields(_fields(title="Nuevo título"))
    assert idea.title == "Nuevo título"
    with pytest.raises(DomainError, match="RNF-5"):
        idea.apply_fields(_fields(problem=""))


# -- completeness (RNF-5) -------------------------------------------------------


def test_complete_fields_pass() -> None:
    assert campos_completos(_fields()) is True
    assert validar_campos(_fields()) == []


def test_a_scalar_empty_field_breaks_completeness() -> None:
    for name in ("title", "description", "problem", "expectedBenefit", "strategicAlignment"):
        fields = _fields(**{name: "   "})
        assert campos_completos(fields) is False
        assert name in campos_incompletos(fields)


def test_a_missing_field_breaks_completeness() -> None:
    fields = _fields()
    del fields["problem"]
    assert campos_incompletos(fields) == ["problem"]
    assert campos_completos(fields) is False


def test_an_object_field_is_incomplete_with_any_empty_part() -> None:
    fields = _fields(proponent={"name": "Ana", "area": "", "contact": "a@b.co"})
    assert campos_incompletos(fields) == ["proponent"]
    fields = _fields(estimatedResources={"time": "6 semanas", "people": "", "budget": "1"})
    assert campos_incompletos(fields) == ["estimatedResources"]


def test_a_garbage_extra_key_is_ignored_for_completeness() -> None:
    assert campos_incompletos(_fields(**{"otraClave": "x"})) == []


def test_empty_dict_is_seven_missing_fields() -> None:
    missing = campos_incompletos({})
    assert missing == [
        "title", "proponent", "description", "problem",
        "expectedBenefit", "strategicAlignment", "estimatedResources",
    ]
    assert campos_completos({}) is False


# -- contact format (case 12) ----------------------------------------------------


@pytest.mark.parametrize(
    ("contact", "expected"),
    [
        ("ana.torres@innov-ia.local", True),
        ("ana.torres@innov-ia", False),  # e-mail without a domain with extension
        ("ana.torres@", False),
        ("48123456789", True),  # plain digits, 11
        ("+48 123-456-789", True),  # phone with signs and country code
        ("(55) 555-1234", True),  # short phone, 7 digits after the signs
        ("12345", False),  # too short for a phone number
        ("123456789-123456789-1", False),  # too long
        ("12a456789", False),  # letters inside the number
        ("", False),  # neither an e-mail nor a phone number
        ("hola", False),
    ],
)
def test_contacto_valido(contact: str, expected: bool) -> None:
    assert contacto_valido(contact) is expected


def test_validar_campos_flags_an_invalid_contact_without_duplicating_the_field() -> None:
    fields = _fields(proponent={"name": "Ana", "area": "Compras", "contact": "no-es-una-clave"})
    assert validar_campos(fields) == ["proponent"]


def test_validar_campos_reports_both_an_empty_contact_and_another_missing_field() -> None:
    fields = _fields(proponent={"name": "Ana", "area": "Compras", "contact": ""}, description="")
    assert set(validar_campos(fields)) == {"proponent", "description"}
    assert validar_campos(fields).count("proponent") == 1


def test_validar_campos_passes_valid_e_mail_and_phone_contacts() -> None:
    assert validar_campos(_fields()) == []
    assert validar_campos(_fields(proponent={"name": "Ana", "area": "Compras", "contact": "+48 123-456-789"})) == []
