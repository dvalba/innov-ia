"""Manual-idea refinement use case (T-061, RF-11/RF-12, plan §4.5).

Refines one manual idea into a complete 7-field version: the prompt carries
the current fields (`refine_idea_prompt`), the reply is interpreted
deterministically (`interpret_fields`) and a valid result is registered as a
PENDIENTE `IdeaVersion` with `requestedBy=refinement` (plan §2.5). The idea
keeps its current fields and its operational state (RF-11: the idea keeps
operating) — it only gains the flag `reviewedByAI` so "Mis ideas" can show
the refined state (RNF-2). On any assistant failure (ping down, generation
error or uninterpretable reply, case 14) nothing is written and `None` is
returned: the idea simply stays pending for the next verification (case 6).

`emit` receives the updated idea payload dict; the caller binds it (G10) to
the `IDEA_REFINED` notification of RF-12. The use case never imports the
`notifications` feature.
"""

from collections.abc import Callable

from features.assistant.domain.prompts import refine_idea_prompt
from features.assistant.domain.refinement import REQUESTED_BY_REFINEMENT, interpret_fields
from shared.contracts.assistant_client import AssistantClient
from shared.contracts.idea_ledger import IDEA_FIELDS, IdeaLedger
from shared.exceptions.handlers import AssistantUnavailable, DomainError


def refine_manual(
    ledger: IdeaLedger,
    assistant: AssistantClient,
    *,
    idea_id: str,
    emit: Callable[[dict], None] | None = None,
) -> dict | None:
    """Refines `idea_id` with the assistant and returns the updated payload.

    `None` when the idea is missing or the assistant cannot produce a valid
    version (case 6/14: nothing changes, the idea stays pending).
    """
    payload = ledger.get(idea_id)
    if payload is None:
        raise DomainError("IDEA_NOT_FOUND", "La idea no existe.", status_code=404)
    if not assistant.ping():
        return None
    idea_for_prompt = {"fields": {key: payload[key] for key in IDEA_FIELDS}}
    try:
        raw = assistant.generate(refine_idea_prompt(idea_for_prompt))
    except AssistantUnavailable:
        return None
    fields = interpret_fields(raw)
    if fields is None:
        return None
    ledger.add_version(idea_id=idea_id, fields=fields, requested_by=REQUESTED_BY_REFINEMENT)
    updated = ledger.update(idea_id, {"reviewedByAI": True})
    if emit is not None:
        emit(updated)
    return updated
