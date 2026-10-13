"""Prompt templates for the assistant (T-060, plan §4).

Pure domain module (Constitution §4.2): no FastAPI/Pydantic. All templates are
in Spanish (RNF-4) and instruct the model to answer with strict JSON so the
reply can be interpreted deterministically by the domain logic
(`refinement.py`). The model is only ever asked for content; the structural
rules (field order, chips, validation) live in the capture/assistant code.
"""

# Names of the 7 idea fields (spec §1.1), shared by the extract/refine prompts.
FIELD_LABELS: dict[str, str] = {
    "title": "Título",
    "proponent": "Proponente (nombre, área y contacto)",
    "description": "Descripción",
    "problem": "Problema u oportunidad",
    "expectedBenefit": "Beneficio esperado",
    "strategicAlignment": "Alineación estratégica",
    "estimatedResources": "Recursos estimados (tiempo, personal, presupuesto)",
}


def _json_only_prelude() -> str:
    return (
        "Responde exclusivamente con un objeto JSON válido, sin markdown, sin bloques de "
        "código y sin texto antes o después del JSON.\n"
    )


def extract_fields_prompt(narrative: str, pending_fields: tuple[str, ...]) -> str:
    """Prompts the field extraction from a free narrative (RF-3).

    Only fields not yet captured are extracted; the rest are ignored so the
    code never re-asks about a completed field (RF-3 acceptance criterion).
    """
    labels = "\n".join(f"- {key}: {FIELD_LABELS[key]}" for key in pending_fields)
    return _json_only_prelude() + (
        "Eres el asistente de registro de ideas de Innov-IA. A partir del texto del "
        "usuario, asigna la información a los campos PENDIENTES que faltan de la idea. "
        "NO inventes información: solo usa lo que el usuario escribió. Un campo cuyo "
        "contenido no aparezca en el texto debe devolverse como una cadena vacía. "
        "Si el texto de un fragmento es demasiado vago para ser útil, devuelve la cadena "
        "especial \"__CLARIFICAR__\" en ese campo.\n"
        f"Campos pendientes:\n{labels}\n\n"
        f"Texto del usuario:\n\"\"\"{narrative}\"\"\"\n\n"
        "JSON esperado: un objeto con como mucho una clave por campo pendiente, cuyos "
        "valores son cadenas de texto."
    )


def title_suggestion_prompt(context: str, avoid: tuple[str, ...]) -> str:
    """Proactive title suggestion (RF-4); `avoid` lists the earlier suggestions.

    The returned text must be different from every avoided candidate; the code
    validates the "another" loop and re-asks if the model repeats one (RF-4).
    """
    avoided = "\n".join(f"- \"{item}\"" for item in avoid) if avoid else "- (ninguna)"
    return _json_only_prelude() + (
        "Eres el asistente de registro de ideas de Innov-IA. Propón un título corto "
        "(máximo 140 caracteres) para la idea descrita. Debe ser una frase nominal "
        "sustantiva, en español, sin punto final y distinta de cualquier título "
        "previamente rechazado o ya propuesto.\n"
        f"Resumen de la idea: \"\"\"{context}\"\"\"\n"
        f"Títulos que DEBEN evitarse (no repitas ninguno):\n{avoided}\n\n"
        "JSON esperado: {\"title\": \"<el título propuesto>\"}"
    )


def refine_idea_prompt(idea: dict) -> str:
    """Refinement of a manual idea into its 7-field version (RF-11, RF-13).

    `idea` is the full idea payload (schema plan §2.2). The refined version
    keeps all 7 fields and improves wording without inventing facts
    (the 7-field completeness is re-validated by the code, RNF-5).
    """
    fields = idea.get("fields", {})
    current = "\n".join(f"- {FIELD_LABELS[key]}: {value or '(vacío)'}" for key, value in fields.items())
    for key in ("proponent", "estimatedResources"):
        if isinstance(fields.get(key), dict):
            current += f"\n- ({FIELD_LABELS[key]}) detalle: {fields[key]}"
    return _json_only_prelude() + (
        "Eres el asistente de Innov-IA. La siguiente idea fue capturada de forma "
        "manual y necesita ser refinada y estructurada. Mejora la redacción de cada "
        "campo para que sea clara y profesional, manteniendo el contenido original: "
        "NO añadas datos que no estén en la idea. Los 7 campos deben quedar completos.\n"
        f"Idea actual:\n{current}\n\n"
        "JSON esperado: un objeto con las claves title, proponent, description, problem, "
        "expectedBenefit, strategicAlignment, estimatedResources. `proponent` y "
        "`estimatedResources` son objetos con sus subcampos (name/area/contact; "
        "time/people/budget respectivamente)."
    )


def turn_options_prompt(*, current_field: str, captured: dict, org: dict | None) -> str:
    """Per-turn capture assistance (D7 replacement: IA-generated quick options).

    Asks the model for BOTH at once, grounded on the organization profile:
      - `options`: up to 5 short candidate replies (chips) for the field being
        asked right now,
      - `compact`: improved, concise versions of the free-text fields already
        captured (only the non-empty string fields are shown; structured fields
        never reach the model).
    When the organization profile is missing or empty the model is told so and
    must still answer strictly (the code degrades to no chips, never breaks).
    The `JSON esperado: {"options` marker is the contract the test mock keys on.
    """
    label = FIELD_LABELS.get(current_field, current_field)
    profile = org or {}
    has_profile = any(str(profile.get(key, "")).strip()
                      for key in ("name", "sector", "description", "mission")) \
        or bool(profile.get("strategicObjectives"))
    if has_profile:
        objectives = profile.get("strategicObjectives") or []
        objectives_text = "\n".join(f"- {item}" for item in objectives) if objectives else "- (sin definir)"
        org_block = (
            "Perfil de la organización:\n"
            f"- Nombre: {profile.get('name') or '(sin definir)'}\n"
            f"- Sector: {profile.get('sector') or '(sin definir)'}\n"
            f"- Descripción: {profile.get('description') or '(sin definir)'}\n"
            f"- Misión: {profile.get('mission') or '(sin definir)'}\n"
            f"- Objetivos estratégicos:\n{objectives_text}"
        )
    else:
        org_block = "Perfil de la organización: (sin perfil de organización definido)"
    free_lines = [
        f"- {FIELD_LABELS.get(key, key)}: {value}"
        for key, value in captured.items()
        if isinstance(value, str) and str(value).strip()
    ]
    free_block = "\n".join(free_lines) if free_lines else "(ninguno)"
    return _json_only_prelude() + (
        "Eres el asistente de Innov-IA en la captura asistida de una idea. En este "
        "turno se está preguntando por el campo indicado. Propón opciones rápidas "
        "que el proponente podría responder con un clic, basándote en el perfil de "
        "la organización y en lo ya capturado: NO inventes datos no apoyados. "
        "Además, mejora y acorta la redacción de los campos de texto libre ya "
        "capturados, conservando su significado sin añadir datos nuevos.\n"
        f"{org_block}\n"
        f"Campo en curso: {label}.\n"
        f"Campos de texto libre ya capturados:\n{free_block}\n\n"
        "Reglas: las opciones son cadenas cortas (máximo 90 caracteres, sin punto "
        "final, en español), únicas y no vacías; devuelve hasta 5, o un array vacío "
        "si no puedes proponer ninguna con fundamento. `compact` contiene solo las "
        "claves de los campos de texto libre capturados, con su nueva redacción "
        "concisa (o la misma si no mejora); no incluyas campos que no hayan sido "
        "capturados.\n"
        "JSON esperado: {\"options\": [\"opción 1\", \"opción 2\"], "
        "\"compact\": {\"<campo>\": \"<redacción concisa>\"}}"
    )


def improve_idea_prompt(idea: dict, instruction: str) -> str:
    """Improvement of an idea under the proponent's instruction (RF-8).

    Produces a proposed version; it is NEVER applied automatically — the
    proponent must accept or discard it (RF-8 acceptance criterion).
    """
    fields = idea.get("fields", {})
    current = "\n".join(f"- {FIELD_LABELS[key]}: {value}" for key, value in fields.items()
                        if not isinstance(value, dict))
    return _json_only_prelude() + (
        "Eres el asistente de Innov-IA. El proponente pide una mejora concreta a su "
        "idea. Aplica la instrucción a los campos correspondientes y devuelve la "
        "versión COMPLETA de los 7 campos; los campos que la instrucción no afecte "
        "se devuelven sin cambio. No inventes datos nuevos salvo los que la "
        "instrucción pida explícitamente.\n"
        f"Campo instrucción del proponente: \"\"\"{instruction}\"\"\"\n"
        f"Idea actual:\n{current}\n\n"
        "JSON esperado: un objeto con las claves title, proponent, description, problem, "
        "expectedBenefit, strategicAlignment, estimatedResources."
    )
