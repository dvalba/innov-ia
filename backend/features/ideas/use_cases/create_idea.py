"""Create idea use case (T-020, RF-9, RF-6/RF-7, RNF-5).

Registers a complete idea in EN_DESARROLLO. It is the single creation entry
point shared by the assisted capture (RF-6), the manual contingency form
(RF-7) and the direct API creation (T-023). No idea is ever created with a
missing or empty field (RNF-5) nor with an invalid proponent contact
(case 12): in any of those cases the creation is a `ValidationFailed`.
"""

import uuid

from features.ideas.domain.idea import Idea
from features.ideas.domain.validate import validar_campos
from features.ideas.infrastructure.idea_store import IdeaStore
from shared.contracts.idea_ledger import IDEA_FIELDS, STATE_EN_DESARROLLO
from shared.exceptions.handlers import ValidationFailed


def create_idea(ledger: IdeaStore, *, owner_id: str, origin: str, fields: dict) -> dict:
    """Registers the idea in EN_DESARROLLO and returns its payload.

    `origin` is `asistida` (RF-6) or `manual` (RF-7). Raises
    `ValidationFailed` (422) when any of the 6 fields is missing, empty or
    the contact is malformed (RNF-5, case 12), and `DomainError` for an
    unknown origin or a duplicated id.
    """
    data = {name: fields.get(name) for name in IDEA_FIELDS}
    problems = validar_campos(data)
    if problems:
        raise ValidationFailed(
            "IDEA_FIELDS_INVALID",
                "La idea requiere los 6 campos completos (RNF-5) y un contacto con formato válido (caso 12).",
            details={"fields": problems},
        )
    idea = Idea(
        id="idea_" + uuid.uuid4().hex[:12],
        ownerId=owner_id,
        origin=origin,
        state=STATE_EN_DESARROLLO,
        **{name: data[name] for name in IDEA_FIELDS},
    )
    return ledger.create(idea).to_payload()
