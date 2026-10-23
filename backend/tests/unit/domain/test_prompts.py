"""Prompt company-context injection tests (T-071, RF-22, case 24).

Covers: every prompt template carries the company-context block (profile +
free guide text) when the document has content, and the exact
"(sin contexto de empresa definido)" notice when the document is empty or
absent.
"""

import pytest

from features.assistant.domain.prompts import (
    NO_CONTEXT_NOTICE,
    evaluate_idea_prompt,
    extract_fields_prompt,
    improve_idea_prompt,
    refine_idea_prompt,
    title_suggestion_prompt,
    turn_options_prompt,
)

EMPTY_NOTICE = "(sin contexto de empresa definido)"

CONTEXT = {
    "profile": {
        "name": "Innov-IA S.A.",
        "sector": "Transformación digital",
        "description": "Especialista en automatización de procesos.",
        "mission": "Modernizar la operativa",
        "strategicObjectives": ["Eficiencia operativa", "Cobertura 100% digital"],
    },
    "guideText": "Usar el vocabulario interno: «plataforma unificada».",
    "updatedAt": "2026-01-01T00:00:00Z",
}

IDEA = {
    "fields": {
        "title": "Optimización de aprobación",
        "description": "Digitalizar la validación de proveedores.",
        "problem": "Tres revisiones manuales duplican esfuerzo.",
        "expectedBenefit": "Ahorro de 120 horas/mes.",
        "strategicAlignment": "Agiliza la cadena de suministro.",
    }
}

TEMPLATES = [
    lambda ctx: extract_fields_prompt(
        "Quiero digitalizar los proveedores", ("description", "problem"), ctx
    ),
    lambda ctx: title_suggestion_prompt(
        "Idea sobre proveedores", ("Título descartado",), ctx
    ),
    lambda ctx: refine_idea_prompt(IDEA, ctx),
    lambda ctx: improve_idea_prompt(IDEA, "Cuantifica el beneficio", ctx),
    lambda ctx: turn_options_prompt(
        current_field="problem", captured={"description": "Digitalizar."}, company_context=ctx
    ),
    lambda ctx: evaluate_idea_prompt(IDEA["fields"], ctx),
]

TEMPLATE_NAMES = (
    "extract_fields_prompt",
    "title_suggestion_prompt",
    "refine_idea_prompt",
    "improve_idea_prompt",
    "turn_options_prompt",
    "evaluate_idea_prompt",
)


@pytest.mark.parametrize("build", TEMPLATES, ids=TEMPLATE_NAMES)
def test_prompt_contains_context_when_document_has_content(build):
    prompt = build(CONTEXT)
    assert "(sin contexto de empresa definido)" not in prompt
    assert "Innov-IA S.A." in prompt
    assert "Transformación digital" in prompt
    assert "Modernizar la operativa" in prompt
    assert "Eficiencia operativa" in prompt
    assert "Cobertura 100% digital" in prompt
    assert "plataforma unificada" in prompt


@pytest.mark.parametrize(
    ("build", "ctx"),
    [(build, ctx) for build in TEMPLATES for ctx in (None, {"profile": {}, "guideText": ""})],
    ids=[f"{name}-{tag}" for name in TEMPLATE_NAMES for tag in ("none", "empty-doc")],
)
def test_prompt_carries_no_context_notice_when_document_empty(build, ctx):
    prompt = build(ctx)
    assert NO_CONTEXT_NOTICE in prompt


def test_evaluate_idea_prompt_carries_the_five_fixed_criteria() -> None:
    prompt = evaluate_idea_prompt(IDEA["fields"], CONTEXT)
    for key in (
        "claridadDelProblema",
        "factibilidad",
        "impactoEsperado",
        "alineacionEstrategica",
        "gradoDeInnovacion",
    ):
        assert f'clave "{key}"' in prompt
    assert "score 1-10" in prompt
    assert "Optimización de aprobación" in prompt  # the idea itself grounds the judgment
