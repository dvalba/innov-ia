"""Shared AI-evaluation contract (T-074, RF-26, plan §2.2/§4.8).

Resolves the coupling between the `assistant` feature (which generates the
evaluation at publication and retries it at the next verification) and the
`validation` feature (which accepts or replaces it), both of which only know
the `IdeaLedger` contract: the five fixed criteria, the evaluation states and
the criteria-validation rule live here, in the shared layer, exactly as the
state/origin constants of `idea_ledger` do.

The payload shape is the `evaluation`/`aiEvaluation` object of the `Idea`
schema (plan §2.2): `{status, criteria[], author, createdAt, decidedBy,
decidedAt}`. `aiEvaluation` is the immutable snapshot of the AI's evaluation;
`evaluation` is the final judgment, always the result of the specialist's
last action (case 23).
"""

from collections.abc import Mapping, Sequence
from typing import Any

# The 5 fixed criteria (RF-26, decision D15): the keys are the spec contract
# exposed in the idea payload and the API, in their canonical order.
EVALUATION_CRITERIA: tuple[str, ...] = (
    "claridadDelProblema",
    "factibilidad",
    "impactoEsperado",
    "alineacionEstrategica",
    "gradoDeInnovacion",
)

# Display names of the criteria (RNF-4: UI/prompt-facing, in Spanish).
EVALUATION_CRITERIA_LABELS: dict[str, str] = {
    "claridadDelProblema": "Claridad del problema",
    "factibilidad": "Factibilidad",
    "impactoEsperado": "Impacto esperado",
    "alineacionEstrategica": "Alineación estratégica",
    "gradoDeInnovacion": "Grado de innovación",
}

# Evaluation lifecycle (plan §2.2 `evaluation.status`): `PENDING` while the
# AI could not generate it (case 22), `GENERADA` once the AI produced it,
# `ACEPTADA`/`SUSTITUIDA` after the specialist's decision (case 23: the final
# judgment is always the result of the last action).
STATE_PENDING = "PENDING"
STATE_GENERADA = "GENERADA"
STATE_ACEPTADA = "ACEPTADA"
STATE_SUSTITUIDA = "SUSTITUIDA"
EVALUATION_STATES: tuple[str, ...] = (
    STATE_PENDING,
    STATE_GENERADA,
    STATE_ACEPTADA,
    STATE_SUSTITUIDA,
)

# Displayed author of the AI evaluation (plan §4.8: "Asistente (IA)").
EVALUATION_AI_AUTHOR = "Asistente (IA)"

# Score bounds (RF-26: integer 1-10 per criterion).
SCORE_MIN = 1
SCORE_MAX = 10


def _is_int_in_range(value: Any, low: int, high: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and low <= value <= high


def validate_evaluation_criteria(criteria: Any) -> list[str]:
    """The problems of a criterion list (`[]` when it is exactly the 5 fixed).

    The list must contain each of the `EVALUATION_CRITERIA` keys exactly once
    (no missing, no unknown, no duplicate) and each criterion carries a `score`
    integer in `SCORE_MIN..SCORE_MAX` plus a non-empty `justification` string
    (RNF-5: the 5 criteria are the complete judgment; the API returns 422 with
    these problems, plan §4.8 `SUSTITUIR_EVALUACION`).
    """
    if not isinstance(criteria, Sequence) or isinstance(criteria, (str, bytes, dict)):
        return ["La evaluación requiere la lista de criterios."]
    if len(criteria) != len(EVALUATION_CRITERIA):
        return [f"La evaluación requiere exactamente los {len(EVALUATION_CRITERIA)} criterios."]
    problems: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(criteria):
        location = f"criterio {index + 1}"
        if not isinstance(item, Mapping):
            problems.append(f"El {location} debe ser un objeto con criterion, score y justification.")
            continue
        name = item.get("criterion")
        if name not in EVALUATION_CRITERIA:
            expected = ", ".join(EVALUATION_CRITERIA)
            problems.append(f"Criterion desconocido o mal escrito: «{name}» (esperado: {expected}).")
        elif name in seen:
            problems.append(f"Criterion repetido: «{name}».")
        else:
            seen.add(str(name))
        if not _is_int_in_range(item.get("score"), SCORE_MIN, SCORE_MAX):
            problems.append(
                f"El score del {location} debe ser un entero entre {SCORE_MIN} y {SCORE_MAX}."
            )
        justification = item.get("justification")
        if not (isinstance(justification, str) and justification.strip()):
            problems.append(f"La justificación del {location} no puede estar vacía.")
    for name in EVALUATION_CRITERIA:
        if str(name) not in seen:
            problems.append(f"Falta el criterio «{name}».")
    return problems
