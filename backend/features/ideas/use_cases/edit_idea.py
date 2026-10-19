"""Edit idea use case (T-020, RF-9, RNF-5).

Manual editing of any of the 6 fields, only while the idea is in
EN_DESARROLLO and only by its owner (RNF-7: every role sees and edits only
its own data). While the assistant is producing a version of the idea the
edit is blocked with a `DomainError` 409 (`generando` flag, RF-9); it
unblocks once the version is decided (T-024/`IdeaStore.decide`).
"""

from features.ideas.domain.idea import Idea
from features.ideas.domain.validate import validar_campos
from features.ideas.infrastructure.idea_store import IdeaStore
from shared.contracts.idea_ledger import STATE_EN_DESARROLLO
from shared.exceptions.handlers import DomainError, ValidationFailed


def edit_idea(ledger: IdeaStore, *, idea_id: str, owner_id: str, fields: dict) -> dict:
    """Applies the 6 fields to the idea and returns the updated payload.

    Order of the guards:
      - unknown idea -> `DomainError` 404;
      - not the owner -> `DomainError` 403 (RNF-7);
      - state other than EN_DESARROLLO -> `DomainError` 409
        (VALIDADA_PUBLICA is terminal, spec §8.8; SOLICITANDO_PUBLICACION
        must be decided first);
      - generation in flight -> `DomainError` 409 with the RF-9 notice;
      - incomplete fields or bad contact -> `ValidationFailed` 422 (RNF-5,
        case 12).
    """
    payload = ledger.get(idea_id)
    if payload is None:
        raise DomainError("IDEA_NOT_FOUND", "La idea no existe.", status_code=404)
    if payload["ownerId"] != owner_id:
        raise DomainError(
            "NOT_IDEA_OWNER",
            "Solo el propietario de la idea puede editarla (RNF-7).",
            status_code=403,
        )
    if payload["state"] != STATE_EN_DESARROLLO:
        raise DomainError(
            "IDEA_NOT_EDITABLE",
            f"La idea está en estado {payload['state']}; solo se edita en EN_DESARROLLO (RF-9).",
            status_code=409,
        )
    if payload.get("generando"):
        raise DomainError(
            "GENERATION_IN_PROGRESS",
            "El asistente está generando una versión de la idea; la edición manual queda "
            "bloqueada hasta que la generación termine (RF-9).",
            status_code=409,
        )
    problems = validar_campos(fields)
    if problems:
        raise ValidationFailed(
            "IDEA_FIELDS_INVALID",
            "La idea requiere los 6 campos completos (RNF-5) y un contacto con formato válido (caso 12).",
            details={"fields": problems},
        )
    idea = Idea.from_payload(payload)
    idea.apply_fields(fields)
    updated = ledger.update_state(idea, expected_state=STATE_EN_DESARROLLO)
    return updated.to_payload()
