"""Refinement queue use case (T-061, RF-11/RF-12, plan §4.5 `VERIFY_Y_PROCESAR`).

On demand, verifies the assistant and processes the full queue in a single
pass (spec case 5: after a long outage the whole queue is processed, no
expiration): every manual `EN_DESARROLLO` idea without a valid refined
version (oldest first, RF-11) is refined via `refine_manual`, and an idea
holding a pending `improvementRequest` (case 10, saved by `improve_idea`
while the assistant was down) is first converted with its stored
instruction. One assistant action per idea per pass: the explicit
improvement request takes the pass, and whatever is left still pending is
counted for the next verification (case 6: the failed stays pending, the
processed is kept). The assistant down short-circuits without touching any
idea; the idea keeps operating in every situation (RF-11).

The summary is `{"status", "refined", "failed", "pending"}`: `status` is
`OK` when the pass ran (even partially) and `UNAVAILABLE` when the
assistant was down; `refined` counts the successful actions, `failed` the
attempts that produced nothing, and `pending` the ideas the next pass
still has to process. `emit` receives each updated idea payload dict; the
caller binds it (G10) to the `IDEA_REFINED` notification (RF-12).
"""

from collections.abc import Callable

from features.assistant.domain.prompts import improve_idea_prompt
from features.assistant.domain.refinement import build_refinement_queue, interpret_fields
from features.assistant.use_cases.refine_manual import refine_manual
from shared.contracts.assistant_client import AssistantClient
from shared.contracts.idea_ledger import IDEA_FIELDS, ORIGIN_MANUAL, STATE_EN_DESARROLLO, IdeaLedger
from shared.exceptions.handlers import AssistantUnavailable


def _ordered_queue(ledger: IdeaLedger) -> list[dict]:
    """The pass targets in the verification order (RF-11, oldest first).

    Combines the refinement queue with every `EN_DESARROLLO` idea holding a
    pending `improvementRequest` (case 10); an idea appearing in both is
    processed once.
    """
    queue: dict[str, dict] = {
        idea["id"]: idea
        for idea in build_refinement_queue(
            ledger.list_by_origin(ORIGIN_MANUAL, STATE_EN_DESARROLLO), ledger.versions_of
        )
    }
    for idea in ledger.list_by_state(STATE_EN_DESARROLLO):
        if idea.get("improvementRequest") is not None:
            queue.setdefault(idea["id"], idea)
    return sorted(
        queue.values(), key=lambda entry: (entry.get("createdAt") or "", entry.get("id") or "")
    )


def _pending_count(ledger: IdeaLedger) -> int:
    """Ideas a verification pass still has to process (queue + pending requests)."""
    queue: dict[str, dict] = {
        idea["id"]: idea
        for idea in build_refinement_queue(
            ledger.list_by_origin(ORIGIN_MANUAL, STATE_EN_DESARROLLO), ledger.versions_of
        )
    }
    for idea in ledger.list_by_state(STATE_EN_DESARROLLO):
        if idea.get("improvementRequest") is not None:
            queue.setdefault(idea["id"], idea)
    return len(queue)


def _convert_pending_request(
    ledger: IdeaLedger, assistant: AssistantClient, payload: dict, emit: Callable | None,
    company_context: dict | None,
) -> bool:
    """Applies the stored improvement instruction (case 10); `True` on success.

    Registers the PENDIENTE version with `requestedBy=improvement` (RF-8: it
    still requires the proponent's decision) and clears the stored request;
    nothing changes when the assistant produces nothing (the request stays
    saved and is retried at the next verification). `company_context` grounds
    the conversion on the company-context document (RF-22).
    """
    request = payload["improvementRequest"]
    idea_for_prompt = {"fields": {key: payload[key] for key in IDEA_FIELDS}}
    try:
        raw = assistant.generate(
            improve_idea_prompt(idea_for_prompt, request["instruction"], company_context)
        )
    except AssistantUnavailable:
        return False
    fields = interpret_fields(raw)
    if fields is None:
        return False
    ledger.add_version(
        idea_id=payload["id"], fields=fields, requested_by="improvement", generating=True
    )
    ledger.update(payload["id"], {"reviewedByAI": True, "improvementRequest": None})
    if emit is not None:
        emit(ledger.get(payload["id"]))
    return True


def run_refinement_queue(
    ledger: IdeaLedger,
    assistant: AssistantClient,
    *,
    emit: Callable[[dict], None] | None = None,
    company_context: dict | None = None,
) -> dict:
    """Verifies the assistant and processes the whole queue; returns the summary.

    `{"status": "UNAVAILABLE", ...}` without touching any idea when the
    assistant is down; otherwise `{"status": "OK", "refined": n, "failed": m,
    "pending": p}` for the pass result (case 6: partial failures are kept
    pending, the processed is kept). A second immediate call is idempotent
    when the assistant kept producing valid versions. `company_context` is the
    current company-context document injected in every prompt of the pass
    (RF-22); the plain dict keeps this feature feature-isolated.
    """
    if not assistant.ping():
        return {"status": "UNAVAILABLE", "refined": 0, "failed": 0,
                "pending": _pending_count(ledger)}
    refined = 0
    failed = 0
    for payload in _ordered_queue(ledger):
        try:
            if payload.get("improvementRequest") is not None:
                succeeded = _convert_pending_request(
                    ledger, assistant, payload, emit, company_context
                )
            else:
                succeeded = refine_manual(
                    ledger, assistant, idea_id=payload["id"], emit=emit,
                    company_context=company_context,
                ) is not None
        except Exception:
            succeeded = False
        if succeeded:
            refined += 1
        else:
            failed += 1
    return {"status": "OK", "refined": refined, "failed": failed,
            "pending": _pending_count(ledger)}
