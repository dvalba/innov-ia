"""Improve idea use case (T-024, RF-8, plan §4.5 `SOLICITAR_MEJORA`).

Orchestration of the AI improvement: the proponent's instruction is sent to
the assistant (injected `AssistantClient`, G04) grounded on the company
context document (RF-22) and the reply is interpreted into the 6 structured
fields (`refinement.interpret_fields`). On success a
`IdeaVersion` PENDIENTE with `requestedBy=improvement` is registered (it
always requires an accept/discard decision, RF-8) and the idea flags
`reviewedByAI` and `generando` (manual editing is blocked until the version
is decided, RF-9/T-020).

When the assistant is unavailable — the ping fails, the generation raises
`AssistantUnavailable`, or the reply cannot be interpreted (case 14) — the
instruction is saved on the idea as `improvementRequest` (pending request,
case 10) and the case-10 notice is returned without any error; the
refinement queue (`run_refinement_queue`) converts it once the IA is back.
"""

from datetime import datetime

from features.assistant.domain.prompts import improve_idea_prompt
from features.assistant.domain.refinement import interpret_fields
from features.ideas.infrastructure.idea_store import IdeaStore
from shared.contracts.assistant_client import AssistantClient
from shared.contracts.idea_ledger import IDEA_FIELDS, STATE_EN_DESARROLLO
from shared.exceptions.handlers import AssistantUnavailable, DomainError

# Case-10 notice (spec plan §4.5), exact wording (RNF-4).
CASE_10_NOTICE = "IA no disponible; tu solicitud quedará registrada."


def _own_idea(ledger: IdeaStore, *, idea_id: str, owner_id: str) -> dict:
    """404 when the idea is unknown, 403 for a non-owner (RNF-7); else payload."""
    payload = ledger.get(idea_id)
    if payload is None:
        raise DomainError("IDEA_NOT_FOUND", "La idea no existe.", status_code=404)
    if payload["ownerId"] != owner_id:
        raise DomainError(
            "NOT_IDEA_OWNER",
            "Solo el propietario de la idea puede solicitar su mejora (RNF-7).",
            status_code=403,
        )
    return payload


def improve_idea(
    ledger: IdeaStore,
    assistant: AssistantClient,
    *,
    idea_id: str,
    owner_id: str,
    instruction: str,
    company_context: dict | None = None,
) -> dict:
    """Applies the proponent's instruction via the IA and returns the outcome.

    Guards: unknown idea -> 404; not the owner -> 403 (RNF-7); state other
    than EN_DESARROLLO -> 409 (RF-8); a generation already in flight -> 409
    (no overlapping improvement, RF-9). `company_context` is the current
    company-context document injected in the prompt (RF-22).

    Returns:
      - on success: `{"version": <the PENDIENTE version>, "idea": <payload>}`
        (the idea now has `reviewedByAI=True`, `generando=True` and a
        cleared `improvementRequest`);
      - without the IA (case 10): `{"notice": <case-10 notice>,
        "improvementRequest": <the saved pending request>}` and no version.
    """
    payload = _own_idea(ledger, idea_id=idea_id, owner_id=owner_id)
    if payload["state"] != STATE_EN_DESARROLLO:
        raise DomainError(
            "IDEA_NOT_IMPROVABLE",
            f"La idea está en estado {payload['state']}; solo se solicita mejora en "
            "EN_DESARROLLO (RF-8).",
            status_code=409,
        )
    if payload.get("generando"):
        raise DomainError(
            "GENERATION_IN_PROGRESS",
            "Ya hay una mejora o versión en curso; espera a que se decida antes de "
            "solicitar otra (RF-9).",
            status_code=409,
        )

    improved: dict | None = None
    if assistant.ping():
        idea_for_prompt = {"fields": {key: payload[key] for key in IDEA_FIELDS}}
        prompt = improve_idea_prompt(idea_for_prompt, instruction, company_context)
        try:
            raw = assistant.generate(prompt)
        except AssistantUnavailable:
            raw = None
        if raw is not None:
            improved = interpret_fields(raw)

    if improved is None:
        request = {
            "instruction": instruction,
            "requestedBy": owner_id,
            "requestedAt": datetime.now().isoformat(),
        }
        ledger.update(idea_id, {"improvementRequest": request})
        return {"notice": CASE_10_NOTICE, "improvementRequest": request}

    version = ledger.add_version(
        idea_id=idea_id, fields=improved, requested_by="improvement", generating=True
    )
    ledger.update(idea_id, {"reviewedByAI": True, "improvementRequest": None})
    return {"version": version, "idea": ledger.get(idea_id)}  # type: ignore[return-value]
