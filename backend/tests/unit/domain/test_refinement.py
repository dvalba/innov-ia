"""Refinement queue and reply interpretation tests (T-060, plan §4.5 / §6.3).

Covers: queue filtering (origin manual + EN_DESARROLLO + no valid refinement,
oldest first) and the interpretation of the assistant reply (valid 7-field
payload extracted from noisy text; uninterpretable replies are failures,
spec case 6/14).
"""

from features.assistant.domain.refinement import (
    build_refinement_queue,
    extract_json_object,
    interpret_fields,
    needs_refinement,
)

GOOD_REPLY = (
    'Claro, aquí está la versión refinada:\n'
    '```json\n'
    '{\n'
    '  "title": "Optimización del proceso de aprobación de proveedores",\n'
    '  "proponent": {"name": "Ana Torres", "area": "Compras", "contact": "ana@innov-ia.local"},\n'
    '  "description": "Digitalizar la validación de proveedores.",\n'
    '  "problem": "Tres revisiones manuales duplican esfuerzo.",\n'
    '  "expectedBenefit": "Ahorro de 120 horas/mes.",\n'
    '  "strategicAlignment": "Agiliza la cadena de suministro.",\n'
    '  "estimatedResources": {"time": "6 semanas", "people": "2 dev", "budget": "50000 PLN"}\n'
    '}\n'
    '```'
)


def _idea(origin: str = "manual", state: str = "EN_DESARROLLO", created: str = "2026-01-01T00:00:00Z") -> dict:
    return {"id": "idea_1", "origin": origin, "state": state, "createdAt": created}


def test_manual_idea_in_development_needs_refinement() -> None:
    assert needs_refinement(_idea()) is True


def test_assisted_idea_never_enters_queue() -> None:
    assert needs_refinement(_idea(origin="asistida")) is False


def test_published_idea_never_enters_queue() -> None:
    assert needs_refinement(_idea(state="SOLICITANDO_PUBLICACION")) is False
    assert needs_refinement(_idea(state="VALIDADA_PUBLICA")) is False


def test_idea_with_pending_refinement_is_out_of_queue() -> None:
    versions = [{"requestedBy": "refinement", "status": "PENDIENTE"}]
    assert needs_refinement(_idea(), versions) is False


def test_idea_with_only_discarded_refinement_reenters_queue() -> None:
    versions = [{"requestedBy": "refinement", "status": "DESCARTADA"}]
    assert needs_refinement(_idea(), versions) is True


def test_improvement_versions_do_not_prevent_refinement() -> None:
    versions = [{"requestedBy": "improvement", "status": "ACEPTADA"}]
    assert needs_refinement(_idea(), versions) is True


def test_queue_orders_oldest_first() -> None:
    older = _idea(created="2026-01-01T00:00:00Z")
    newer = _idea(created="2026-02-01T00:00:00Z")
    ideas = [newer, older]

    def versions_for(_idea_id: str):
        return ()

    queue = build_refinement_queue(ideas, versions_for)
    assert [idea["createdAt"] for idea in queue] == [
        "2026-01-01T00:00:00Z",
        "2026-02-01T00:00:00Z",
    ]


def test_queue_filters_out_ids_already_refined() -> None:
    pending = _idea(created="2026-01-02T00:00:00Z")
    pending["id"] = "idea_pend"
    ready = _idea(created="2026-01-01T00:00:00Z")
    ready["id"] = "idea_ok"

    def versions_for(idea_id: str):
        if idea_id == "idea_pend":
            return [{"requestedBy": "refinement", "status": "VIGENTE"}]
        return ()

    queue = build_refinement_queue([pending, ready], versions_for)
    assert [idea["id"] for idea in queue] == ["idea_ok"]


def test_interprets_valid_reply_wrapped_in_noise() -> None:
    fields = interpret_fields(GOOD_REPLY)
    assert fields is not None
    assert fields["title"] == "Optimización del proceso de aprobación de proveedores"
    assert fields["proponent"]["contact"] == "ana@innov-ia.local"
    assert set(fields.keys()) == {
        "title",
        "proponent",
        "description",
        "problem",
        "expectedBenefit",
        "strategicAlignment",
        "estimatedResources",
    }


def test_interprets_plain_json_without_fences() -> None:
    plain = (
        '{"title": "T", "proponent": {"name": "A", "area": "C", "contact": "a@x"}, '
        '"description": "d", "problem": "Pregunta directa", "expectedBenefit": "b",'
        ' "strategicAlignment": "s", '
        '"estimatedResources": {"time": "t", "people": "p", "budget": "b"}}'
    )
    fields = interpret_fields(plain)
    assert fields is not None
    assert fields["problem"] == "Pregunta directa"


def test_extracts_object_after_reasoning_preamble_with_embedded_example() -> None:
    """A thinking model may emit a reasoning preamble that embeds its own sample
    objects and a `</thinking>` fence before the real payload. The extractor
    must discard everything up to the fence and keep the LAST well-formed
    top-level object, so the embedded example never shadows the real reply
    (G15 real-model smoke, T-063/T-065)."""
    raw = (
        '[Thinking]\n'
        'Voy a devolver JSON como {"title": "Borrador de ejemplo", "descripcion": "x"}… '
        '"descripcion" no está bien, mejor uso title. '
        '</thinking>\n'
        '{"title": "T", "proponent": {"name": "A", "area": "C", "contact": "a@x"}, '
        '"description": "d", "problem": "p", "expectedBenefit": "b", '
        '"strategicAlignment": "s", '
        '"estimatedResources": {"time": "t", "people": "p", "budget": "b"}}'
    )
    obj = extract_json_object(raw)
    assert obj is not None
    assert obj["title"] == "T"  # the real payload, not the embedded example


def test_uninterpretable_reply_is_a_failure() -> None:
    assert interpret_fields("no hay json aquí, solo prosa") is None
    assert interpret_fields("```json\n{texto roto\n```") is None
    assert interpret_fields('{"title": "x"}') is None  # missing the rest of the fields


def test_incomplete_reply_is_a_failure() -> None:
    reply = (
        '{"title": "T", "proponent": {"name": "A", "area": "C", "contact": "a@x"}, '
        '"description": "d", "problem": "p", "expectedBenefit": "b",'
        ' "strategicAlignment": "s", '
        '"estimatedResources": {"time": "t", "people": "p"}}'
    )  # budget missing
    assert interpret_fields(reply) is None


def test_empty_field_rejected() -> None:
    reply = (
        '{"title": "T", "proponent": {"name": "A", "area": "C", "contact": "a@x"}, '
        '"description": "", "problem": "p", "expectedBenefit": "b",'
        ' "strategicAlignment": "s", '
        '"estimatedResources": {"time": "t", "people": "p", "budget": "b"}}'
    )
    assert interpret_fields(reply) is None


def test_proponent_contact_is_required() -> None:
    reply = (
        '{"title": "T", "proponent": {"name": "A", "area": "C"}, '
        '"description": "d", "problem": "p", "expectedBenefit": "b",'
        ' "strategicAlignment": "s", '
        '"estimatedResources": {"time": "t", "people": "p", "budget": "b"}}'
    )
    assert interpret_fields(reply) is None
