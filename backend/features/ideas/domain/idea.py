"""Ideas domain: the central `Idea` entity (T-017, RF-9/RF-19, RNF-5).

Pure domain: no FastAPI/Pydantic (decision D8). The entity mirrors the JSON
schema `Idea` of plan §2.2 (camelCase payloads), so a payload is always its
canonical form: `Idea.from_payload(i.to_payload()) == i`.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from features.ideas.domain.validate import validar_campos
from shared.contracts.idea_ledger import (
    IDEA_FIELDS,
    ORIGIN_ASISTIDA,
    ORIGIN_MANUAL,
    STATE_ACEPTADA,
    STATE_ARCHIVADA,
    STATE_EN_DESARROLLO,
    STATE_RECHAZADA,
    STATE_SOLICITANDO_PUBLICACION,
    STATE_VALIDADA_PUBLICA,
)
from shared.exceptions.handlers import DomainError

# Spec contracts (spec §5/§5.10, plan §2.2): allowed origins and states.
ORIGINS: tuple[str, ...] = (ORIGIN_ASISTIDA, ORIGIN_MANUAL)
STATES: tuple[str, ...] = (
    STATE_EN_DESARROLLO,
    STATE_SOLICITANDO_PUBLICACION,
    STATE_VALIDADA_PUBLICA,
    STATE_ACEPTADA,
    STATE_ARCHIVADA,
    STATE_RECHAZADA,
)


class IdeaError(DomainError):
    """The `Idea` record is malformed or unusable (400)."""

    def __init__(self, message: str) -> None:
        super().__init__("IDEA_INVALID", message, status_code=400)


@dataclass
class Idea:
    """An innovation initiative, the business unit of the platform (plan §2.2).

    The 6 mandatory fields (RNF-5) live in `title`, `proponent` (name/area/
    contact), `description`, `problem`, `expectedBenefit` and
    `strategicAlignment`. `ownerId` backs "Mis ideas" (RF-19); `origin` and
    `state` drive the rest of the platform (RNF-2, plan §4.6);
    `createdAt`/`requestDate`/`publishedAt`/`publishedBy` are the audit trail
    (RNF-8). `evaluation` is the final judgment over the 5 fixed criteria
    (RF-26) and `aiEvaluation` its immutable AI-generated snapshot. `decision`
    is the final decision of the calibration stage (RF-27/RF-29, plan §2.2/§4.6):
    `{outcome, reason, score, decidedBy, decidedByName, decidedAt}`, present only
    while the idea is in a final state and cleared to `None` on re-evaluation.
    """

    id: str
    ownerId: str
    title: str
    proponent: dict
    description: str
    problem: str
    expectedBenefit: str
    strategicAlignment: str
    origin: str = ORIGIN_MANUAL
    state: str = STATE_EN_DESARROLLO
    reviewedByAI: bool = False
    currentVersionId: str | None = None
    createdAt: str = ""
    requestDate: str | None = None
    publishedAt: str | None = None
    publishedBy: str | None = None
    rejectionNote: dict | None = None
    generando: bool = False
    improvementRequest: dict | None = None
    evaluation: dict | None = None
    aiEvaluation: dict | None = None
    decision: dict | None = None

    def __post_init__(self) -> None:
        if not self.id or not str(self.id).strip():
            raise IdeaError("La idea requiere un identificador.")
        if not self.ownerId or not str(self.ownerId).strip():
            raise IdeaError("La idea debe estar asociada a una cuenta (RF-19).")
        if self.origin not in ORIGINS:
            raise IdeaError(f"Origen de idea no válido: «{self.origin}» (solo {'/'.join(ORIGINS)}).")
        if self.state not in STATES:
            raise IdeaError(f"Estado de idea no válido: «{self.state}» (solo {'/'.join(STATES)}).")
        if not isinstance(self.proponent, dict):
            raise IdeaError("El campo Proponente debe tener nombre, área y contacto.")
        if not self.createdAt:
            self.createdAt = datetime.now().isoformat()

    # -- the 6 fields, as a plain dict (spec §2.2) --------------------------

    def fields(self) -> dict[str, Any]:
        """Returns the dict of the 6 idea fields (the `fields` key of the payload)."""
        return {
            "title": self.title,
            "proponent": self.proponent,
            "description": self.description,
            "problem": self.problem,
            "expectedBenefit": self.expectedBenefit,
            "strategicAlignment": self.strategicAlignment,
        }

    def apply_fields(self, fields: dict) -> None:
        """Applies the 6 current fields (version acceptance, RF-8/RF-13)."""
        data = dict(fields)
        problems = validar_campos(data)
        if problems:
            raise IdeaError(f"Los 6 campos de la idea son obligatorios (RNF-5); faltan: {', '.join(problems)}.")
        self.title = data["title"]
        self.proponent = data["proponent"]
        self.description = data["description"]
        self.problem = data["problem"]
        self.expectedBenefit = data["expectedBenefit"]
        self.strategicAlignment = data["strategicAlignment"]

    # -- payload round-trip (camelCase, schema §2.2) ------------------------

    def to_payload(self) -> dict:
        """Serializes the entity to the canonical payload (plan §2.2)."""
        payload = dict(zip(IDEA_FIELDS, self.fields().values(), strict=False))
        payload.update(
            {
                "id": self.id,
                "ownerId": self.ownerId,
                "origin": self.origin,
                "state": self.state,
                "reviewedByAI": self.reviewedByAI,
                "currentVersionId": self.currentVersionId,
                "createdAt": self.createdAt,
                "requestDate": self.requestDate,
                "publishedAt": self.publishedAt,
                "publishedBy": self.publishedBy,
                "rejectionNote": self.rejectionNote,
                "generando": self.generando,
                "improvementRequest": self.improvementRequest,
                "evaluation": self.evaluation,
                "aiEvaluation": self.aiEvaluation,
                "decision": self.decision,
            }
        )
        return payload

    @classmethod
    def from_payload(cls, payload: dict) -> "Idea":
        try:
            return cls(
                id=payload["id"],
                ownerId=payload["ownerId"],
                title=payload["title"],
                proponent=payload["proponent"],
                description=payload["description"],
                problem=payload["problem"],
                expectedBenefit=payload["expectedBenefit"],
                strategicAlignment=payload["strategicAlignment"],
                origin=payload.get("origin", ORIGIN_MANUAL),
                state=payload.get("state", STATE_EN_DESARROLLO),
                reviewedByAI=payload.get("reviewedByAI", False),
                currentVersionId=payload.get("currentVersionId"),
                createdAt=payload.get("createdAt", ""),
                requestDate=payload.get("requestDate"),
                publishedAt=payload.get("publishedAt"),
                publishedBy=payload.get("publishedBy"),
                rejectionNote=payload.get("rejectionNote"),
                generando=payload.get("generando", False),
                improvementRequest=payload.get("improvementRequest"),
                evaluation=payload.get("evaluation"),
                aiEvaluation=payload.get("aiEvaluation"),
                decision=payload.get("decision"),
            )
        except KeyError as missing:
            raise IdeaError(f"El registro de la idea está incompleto; falta «{missing.args[0]}».") from missing
