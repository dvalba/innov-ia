"""Company-context document tests (T-070, RF-21, D13/D14, cases 24/25).

Covers the single-company-context document: the empty context (case 24), the
profile normalization (clean_profile), the to_payload / from_payload round-trip,
the `text/plain` template (render_template / get_context_template) and its
reversible parsing (parse_template), and the corrupt-file rejection (case 25).
"""

import pytest

from features.org.domain.company_context import (
    CompanyContext,
    clean_profile,
    parse_template,
    render_template,
)


def _context(**overrides) -> CompanyContext:
    base = dict(
        name="Grupo Innov",
        sector="Industria",
        description="Grupo dedicado a la automatización.",
        mission="Reducir la carga administrativa manual.",
        strategicObjectives=["Digitalizar la cadena de suministro", "Datos"],
    )
    base.update(overrides)
    return CompanyContext(
        profile={
            "name": base["name"],
            "sector": base["sector"],
            "description": base["description"],
            "mission": base["mission"],
            "strategicObjectives": list(base["strategicObjectives"]),
        },
        guideText="Líneas de innovación: automatización, datos, sostenibilidad.",
        updatedAt="2026-01-01T00:00:00",
    )


# -- profile normalization ------------------------------------------------------


def test_clean_profile_strips_blanks_and_dedupes_objectives() -> None:
    result = clean_profile({
        "name": "  Grupo Innov ",
        "sector": " Industria ",
        "description": "x",
        "mission": "y",
        "strategicObjectives": ["A", " A ", "", "B", "C", "C"],
    })
    assert result["name"] == "Grupo Innov"
    assert result["sector"] == "Industria"
    assert result["strategicObjectives"] == ["A", "B", "C"]


def test_clean_profile_ignores_unknown_and_missing_keys() -> None:
    result = clean_profile({"name": "Solo nombre", "extra": "no"})
    assert result["name"] == "Solo nombre"
    assert result["sector"] == ""
    assert result["strategicObjectives"] == []


# -- empty context (case 24) ----------------------------------------------------


def test_empty_context_has_blank_profile_and_guide() -> None:
    context = CompanyContext.empty()
    assert context.profile == {
        "name": "", "sector": "", "description": "", "mission": "",
        "strategicObjectives": [],
    }
    assert context.guideText == ""
    assert context.updatedAt == ""
    assert context.is_empty is True


def test_context_is_not_empty_when_any_section_has_content() -> None:
    assert _context(guideText="").is_empty is False      # profile filled
    assert _context(name="").is_empty is False           # guide filled
    blank = CompanyContext(
        profile={"name": "", "sector": "", "description": "", "mission": "",
                 "strategicObjectives": []},
        guideText="   ",
    )
    assert blank.is_empty is True                        # only blank guide


# -- to_payload / from_payload round-trip --------------------------------------


def test_payload_round_trip_preserves_all_sections() -> None:
    context = _context()
    rebuilt = CompanyContext.from_payload(context.to_payload())
    assert rebuilt.to_payload() == context.to_payload()
    assert rebuilt.profile["name"] == "Grupo Innov"
    assert rebuilt.guideText == context.guideText
    assert rebuilt.updatedAt == "2026-01-01T00:00:00"


def test_from_payload_tolerates_missing_keys() -> None:
    rebuilt = CompanyContext.from_payload({})
    assert rebuilt.profile["name"] == ""
    assert rebuilt.guideText == ""
    assert rebuilt.updatedAt == ""


def test_from_payload_migrates_a_legacy_profile_document() -> None:
    # Legacy v2.0 records had no guideText/updatedAt: they load cleanly.
    rebuilt = CompanyContext.from_payload({"profile": {"name": "Antiguo"}})
    assert rebuilt.profile["name"] == "Antiguo"
    assert rebuilt.guideText == ""
    assert rebuilt.updatedAt == ""


# -- template rendering and parsing --------------------------------------------


def test_render_template_contains_guide_markers_and_sections() -> None:
    template = render_template(CompanyContext.empty(), template=True)
    assert "[PERFIL]" in template
    assert "[GUÍA]" in template
    assert "[/GUÍA]" in template
    assert "name:" in template
    assert "strategicObjectives:" in template
    assert "Alineación estratégica" in template


def test_render_full_document_round_trips_through_parse() -> None:
    context = _context()
    text = render_template(context, template=False)
    parsed = parse_template(text)
    assert parsed["profile"]["name"] == "Grupo Innov"
    assert parsed["profile"]["strategicObjectives"] == [
        "Digitalizar la cadena de suministro", "Datos"]
    assert parsed["guideText"] == context.guideText


def test_parse_template_rejects_a_corrupt_file_case_25() -> None:
    with pytest.raises(ValueError):
        parse_template("texto sin secciones válidas")
