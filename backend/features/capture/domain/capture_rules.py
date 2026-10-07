"""Capture rules (T-025, RF-2/RF-3/RF-5, plan §4.1-§4.2, decision D7).

Pure domain (Constitution §4.2): no FastAPI/Pydantic, no store. Owns the
spec's conversational contracts:

  - the EXACT field order (RF-3): description -> title -> problem ->
    expectedBenefit -> strategicAlignment -> estimatedResources -> proponent;
  - the FIXED quick-reply catalog per field (chips, RF-5, decision D7): the
    backend is the source of the catalog; a selected chip is the field's
    COMPLETE answer and chips stay available until the field is answered;
  - the free-narrative assignment (RF-3): a narrative may complete several
    fields at once; each assigned field is marked captured and never
    re-asked, and an insufficient answer triggers a clarification without
    advancing (``needsClarification``);
  - the limit of one ``ACTIVA`` conversation per user (RF-2) is enforced by
    the use case through the store's active lookup (case 8).
"""

from collections.abc import Mapping
from datetime import datetime

from features.capture.domain.conversation import FIELD_ORDER, Conversation

# The marker the extraction prompt uses for an insufficient fragment (RF-3).
CLARIFY_FLAG = "__CLARIFICAR__"

# RF-2: the assistant's opening when a new capture starts.
GREETING_TEXT = (
    "¡Hola! Te ayudo a registrar tu idea de innovación. Vamos completando 7 datos, "
    "paso a paso. En cada pregunta puedes responder libremente o elegir una de las "
    "opciones rápidas que te ofrezco."
)

# RF-3: the question asked for each field (Spanish, RNF-4).
QUESTION_BY_FIELD: dict[str, str] = {
    "description": (
        "Para empezar: cuéntame, ¿de qué trata tu idea? Escríbela en tus propias "
        "palabras y tan libremente como quieras; si en el texto aparecen datos de "
        "otros campos, los capturo directamente."
    ),
    "title": (
        "Ya tengo una primera visión de tu idea. Aquí va mi sugerencia de título; "
        "puedes aceptarla, pedir otra, o escribir la que prefieras."
    ),
    "problem": "¿Cuál es el problema u oportunidad que tu idea aborda?",
    "expectedBenefit": "¿Qué beneficio esperado genera para la organización?",
    "strategicAlignment": "¿Cómo se alinea tu idea con la estrategia de la organización?",
    "estimatedResources": (
        "¿Qué recursos estimas necesitas? Indícame tiempo, personal y presupuesto."
    ),
    "proponent": (
        "Por último, estos son tus datos de proponente registrados en tu cuenta. "
        "Confírmame si están bien o escríbeme la corrección."
    ),
}

# D7/RF-5: the FIXED quick-reply catalog per field. A chip is the field's
# complete answer; the two handled by their own rules (free description,
# suggested title, RF-4) have no catalog.
CHIPS_BY_FIELD: dict[str, tuple[str, ...]] = {
    "description": (),
    "title": (),
    "problem": (
        "Retrasos en la operación actual",
        "Tarea manual repetitiva",
        "Costos elevados del proceso actual",
        "Falta de visibilidad del área",
    ),
    "expectedBenefit": (
        "Ahorro de tiempo operativo",
        "Reducción de costos",
        "Mejor atención al cliente",
        "Generación de ingresos nuevos",
    ),
    "strategicAlignment": (
        "Agilizar procesos internos",
        "Reducir la carga administrativa manual",
        "Mejorar la experiencia del cliente",
        "Alinear con los objetivos estratégicos del año",
    ),
    "estimatedResources": (
        "Bajo: menos de un mes",
        "Medio: de 1 a 3 meses",
        "Alto: más de 3 meses",
    ),
    "proponent": (
        "Confirmar mi información",
        "Corregir mi información",
    ),
}


def new_conversation(
    *,
    conversation_id: str,
    user_id: str,
    order: tuple[str, ...] | None = None,
    prefill: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> Conversation:
    """Creates a new ``ACTIVA`` conversation with the RF-3 order.

    `prefill` seeds the fields already known (e.g. the proponent data from
    the account, spec §5.2) so they are never asked (RF-3: no re-asking).
    """
    conversation = Conversation(
        id=conversation_id,
        userId=user_id,
        state="ACTIVA",
        capturedFields=dict(prefill or {}),
        currentField=None,
        order=tuple(order) if order is not None else tuple(FIELD_ORDER),
        titleSuggestions=[],
        createdAt=(now or datetime.now()).isoformat(),
    )
    conversation.currentField = next_pending_field(conversation.order, conversation.capturedFields)
    return conversation


def next_pending_field(order: tuple[str, ...], captured: Mapping[str, str]) -> str | None:
    """Returns the first field of `order` not yet captured, or `None` (RF-3).

    Skipping completed fields is the rule that makes the narrative
    assignment safe: a field completed earlier is never re-asked.
    """
    for field_name in order:
        if str(captured.get(field_name, "")).strip() == "":
            return field_name
    return None


def apply_capture(
    captured: dict[str, str], fields: Mapping[str, str], current_field: str | None
) -> None:
    """Applies the extracted fields of a message (RF-3, in place).

    The field in the course always takes the new value (a free answer may
    correct a prefill); the other captured fields only fill gaps, so an
    earlier capture is never lost (RNF-10) and never re-asked (RF-3).
    """
    if current_field is not None and current_field in fields:
        captured[current_field] = str(fields[current_field])
    for key, value in fields.items():
        captured.setdefault(key, str(value))


def needs_clarification(fields: Mapping[str, str]) -> bool:
    """`True` when any extracted fragment is insufficient (RF-3: no advance)."""
    return any(str(value).strip() == CLARIFY_FLAG for value in fields.values())


def is_complete(order: tuple[str, ...], captured: Mapping[str, str]) -> bool:
    """The 7 fields are captured (RF-6 triggers the editable summary)."""
    return next_pending_field(order, captured) is None


def build_question(*, current_field: str) -> dict:
    """The assistant turn for `current_field`: question + fixed chips (RF-5).

    The `quickOptions` are the field's fixed catalog (decision D7) and are
    offered every turn of the field until it is answered (RF-5).
    """
    return {
        "text": QUESTION_BY_FIELD.get(current_field, ""),
        "currentField": current_field,
        "quickOptions": list(CHIPS_BY_FIELD.get(current_field, ())),
    }
