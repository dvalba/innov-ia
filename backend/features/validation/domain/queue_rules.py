"""Validation queue visibility rules (T-034, RF-14; T-082, RF-14 v2.2).

Domain rule for what the specialist sees in the review queue: two stages
(RF-14, v2.2):

  - **publicacion**: only ideas in `SOLICITANDO_PUBLICACION`;
  - **calibracion**: ideas in `VALIDADA_PUBLICA` whose debate is closed,
    whose evaluation is not `PENDING`, and which carry no decision yet.

The proponent is reduced to name + area — the contact data is never exposed
(spec: "visibilidad sin datos de contacto"). Operates on shared ledger payloads
only: the `validation` feature never imports another feature.
"""

from collections.abc import Callable

from shared.contracts.evaluation import STATE_PENDING
from shared.contracts.idea_ledger import (
    IDEA_FIELDS,
    STATE_SOLICITANDO_PUBLICACION,
    STATE_VALIDADA_PUBLICA,
)
from shared.exceptions.handlers import ValidationFailed

# The states visible in the review queue (RF-14, v2.2 two stages).
QUEUE_STATE = STATE_SOLICITANDO_PUBLICACION
CALIBRATION_STATE = STATE_VALIDADA_PUBLICA

# The valid stage values (v2.2, plan §3.1 `GET /validation/queue?stage=…`).
STAGE_PUBLICACION = "publicacion"
STAGE_CALIBRACION = "calibracion"
STAGES: tuple[str, ...] = (STAGE_PUBLICACION, STAGE_CALIBRACION)


def validate_stage(stage: str | None) -> str | None:
    """422s when the stage is not one of the two valid values (v2.2)."""
    if stage is None:
        return None
    if stage not in STAGES:
        raise ValidationFailed(
            code="QUEUE_STAGE_INVALID",
            message=f"Etapa de cola no válida: «{stage}» (solo {', '.join(STAGES)}).",
            details={"problems": [f"«{stage}» no es una etapa de cola válida."]},
        )
    return stage


def in_calibration(payload: dict, is_debate_closed: Callable[[str], bool]) -> bool:
    """True when a `VALIDADA_PUBLICA` payload belongs in the calibration queue.

    The idea must (RF-14 v2.2, plan §4.9 note):
      - carry no decision yet (`decision is None`);
      - have an evaluation whose status is not `PENDING`;
      - have its debate closed (`is_debate_closed(idea_id)`).
    """
    if payload.get("decision") is not None:
        return False
    evaluation = payload.get("evaluation")
    if evaluation is None or evaluation.get("status") == STATE_PENDING:
        return False
    return is_debate_closed(str(payload.get("id", "")))


def queue_entry(payload: dict) -> dict:
    """Projects a queue payload into one queue entry (same shape for both stages).

    Holds `id`, `origin`, `requestDate` and the 6 fields (`fields`), with the
    `proponent` reduced to `name`/`area` (no `contact`). Anything beyond the
    6 fields (ownerId, state, contact, ...) is never exposed (RF-14).
    """
    raw_proponent = payload.get("proponent", {})
    proponent = {"name": raw_proponent.get("name", ""), "area": raw_proponent.get("area", "")}
    fields = {key: payload[key] for key in IDEA_FIELDS}
    fields["proponent"] = proponent
    return {
        "id": payload["id"],
        "origin": payload.get("origin", ""),
        "requestDate": payload.get("requestDate"),
        "fields": fields,
    }
