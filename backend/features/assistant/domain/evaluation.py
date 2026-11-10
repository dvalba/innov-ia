"""Interpretation and generation of the AI evaluation (T-074, RF-26, plan §4.8).

Pure-domain module over shared contracts (Constitution §4.2): the assistant
neither owns the idea record nor the evaluation rules — it consumes the
`IdeaLedger` and the `AssistantClient` prototypes and the criteria contract
(`shared.contracts.evaluation`) exactly.

`interpret_evaluation` turns the assistant's raw reply into the 5-criterion
list or `None` (an uninterpretable reply is a failure, case 14; the
evaluation stays `PENDING`). `generate_evaluation` writes the result onto the
idea at the debate's closure and `retry_pending_evaluations` re-attempts the
`PENDING` ones of the published ideas at every assistant verification (case
22: the platform is never blocked by a down assistant).
"""

from collections.abc import Callable
from typing import Any

from features.assistant.domain.prompts import evaluate_idea_prompt
from features.assistant.domain.refinement import extract_json_object
from shared.contracts.evaluation import (
    EVALUATION_AI_AUTHOR,
    EVALUATION_CRITERIA,
    STATE_ACEPTADA,
    STATE_GENERADA,
    STATE_PENDING,
    STATE_SUSTITUIDA,
)
from shared.contracts.idea_ledger import STATE_VALIDADA_PUBLICA
from shared.exceptions.handlers import AssistantUnavailable


def interpret_evaluation(raw: str) -> list[dict[str, Any]] | None:
    """The 5 criteria in canonical order, or `None` when uninterpretable.

    The reply must be a JSON object with exactly the 5 fixed criteria, each a
    `{"score": int 1-10, "justification": non-empty str}` (RNF-5: the judgment
    is the 5 criteria, nothing else). Scores must be integers — booleans and
    floats are rejected so an out-of-domain reply never becomes a score. The
    JSON recovery reuses the refinement's tolerant scanner, so a reply wrapped
    in fences or preceded by a reasoning preamble still parses.
    """
    data = extract_json_object(raw)
    if not isinstance(data, dict) or set(data) != set(EVALUATION_CRITERIA):
        return None
    criteria: list[dict[str, Any]] = []
    for key in EVALUATION_CRITERIA:
        entry = data[key]
        if not isinstance(entry, dict):
            return None
        score = entry.get("score")
        justification = entry.get("justification")
        if not isinstance(score, int) or isinstance(score, bool) or not 1 <= score <= 10:
            return None
        if not isinstance(justification, str) or not justification.strip():
            return None
        criteria.append({
            "criterion": key,
            "score": score,
            "justification": justification.strip(),
        })
    return criteria


def generate_evaluation(
    ledger,
    assistant,
    *,
    idea_id: str,
    company_context: dict | None,
    now: str,
    on_generated: Callable[[str], None] | None = None,
) -> str:
    """Generates the AI evaluation of a published idea at its debate closure
    (plan §4.8 `GENERAR_EVALUACION`).

    Writes the result onto the idea through the ledger contract and returns
    the final `evaluation.status`:
      - the current status, unchanged, when the idea already carries an
        evaluation that is not `PENDING` (`GENERADA`, `ACEPTADA` or
        `SUSTITUIDA`): a decided or already-generated judgment is never
        clobbered by a later generation attempt (a debate re-opened by an
        admin and closed again must not erase the specialist's decision);
      - `PENDING` when the assistant is down or does not answer in time (case
        22: the platform is never blocked, it keeps operating), or when the
        reply cannot be interpreted (case 14); the retry happens at the next
        assistant verification (`retry_pending_evaluations`);
      - `GENERADA` with the 5 criteria, author "Asistente (IA)", the
        generation date and the `decidedBy`/`decidedAt` audit fields still
        `None` (RF-26, RNF-8). The immutable `aiEvaluation` snapshot is
        stored together with the evaluation.

    When a fresh `GENERADA` result is written, `on_generated` (bound in the
    composition root, T-083) is invoked once with the idea id — the single
    point where an evaluation first exists, so the caller's fanout (the
    `IDEA_CALIBRATION_PENDING` notification to the specialists) fires exactly
    once per idea (RNF-9). A no-op (and `None` default) when the evaluation is
    already present or the generation did not succeed.
    """
    def persist(changes: dict[str, Any]) -> None:
        ledger.update(idea_id, changes)

    payload = ledger.get(idea_id)
    if payload is None:
        return STATE_PENDING
    current = payload.get("evaluation")
    if isinstance(current, dict) and current.get("status") in (
        STATE_GENERADA, STATE_ACEPTADA, STATE_SUSTITUIDA,
    ):
        return str(current["status"])
    if not assistant.ping():
        persist({"evaluation": {"status": STATE_PENDING}})
        return STATE_PENDING
    try:
        raw = assistant.generate(evaluate_idea_prompt(payload.get("fields") or {}, company_context))
    except AssistantUnavailable:
        persist({"evaluation": {"status": STATE_PENDING}})
        return STATE_PENDING
    criteria = interpret_evaluation(raw)
    if criteria is None:
        persist({"evaluation": {"status": STATE_PENDING}})
        return STATE_PENDING
    evaluation = {
        "status": STATE_GENERADA,
        "criteria": criteria,
        "author": EVALUATION_AI_AUTHOR,
        "createdAt": now,
        "decidedBy": None,
        "decidedAt": None,
    }
    persist({"evaluation": evaluation, "aiEvaluation": dict(evaluation)})
    if on_generated is not None:
        on_generated(idea_id)
    return STATE_GENERADA


def retry_pending_evaluations(
    ledger,
    assistant,
    now: str,
    company_context: dict | None = None,
    on_generated: Callable[[str], None] | None = None,
) -> int:
    """Retries the `PENDING` evaluations of the published ideas (case 22, RF-11).

    Runs at every assistant verification (plan §4.8
    `REINTENTAR_EVALUACION_PENDIENTE`): each `VALIDADA_PUBLICA` idea whose
    `evaluation.status` is still `PENDING` gets a new generation attempt. An
    idea the specialist already decided on (accepted or replaced) never
    returns to `PENDING`, so its snapshot is never overwritten. Returns the
    number of evaluations that reached `GENERADA`; the assistant down
    short-circuits to `0` without touching any idea (RNF-1).

    `on_generated` (T-083) is forwarded to each generation attempt, so the
    first evaluation that succeeds on this retry triggers the same one-time
    fanout as a generation at debate closure.
    """
    if not assistant.ping():
        return 0
    generated = 0
    for payload in ledger.list_by_state(STATE_VALIDADA_PUBLICA):
        evaluation = payload.get("evaluation")
        if not isinstance(evaluation, dict) or evaluation.get("status") != STATE_PENDING:
            continue
        if generate_evaluation(
            ledger, assistant,
            idea_id=str(payload["id"]), company_context=company_context, now=now,
            on_generated=on_generated,
        ) == STATE_GENERADA:
            generated += 1
    return generated
