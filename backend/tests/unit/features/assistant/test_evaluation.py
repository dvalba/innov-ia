"""AI evaluation generation and interpretation tests (T-074, RF-26, plan §4.8).

Covers: the interpretation of the assistant reply (a strict JSON object with
the 5 fixed criteria; fences/prose tolerated, case-14 failures), the
generation of the evaluation at the debate's closure (`GENERADA` with the
immutable `aiEvaluation` snapshot, `PENDING` when the assistant is down or the
reply is uninterpretable — the platform is never blocked, case 22), the
clobber guard (a decided or already-generated evaluation is never overwritten
by a later generation attempt) and the retry of the `PENDING` evaluations at
the next assistant verification.
"""

import json

from features.assistant.domain.evaluation import (
    generate_evaluation,
    interpret_evaluation,
    retry_pending_evaluations,
)
from shared.contracts.evaluation import (
    EVALUATION_AI_AUTHOR,
    EVALUATION_CRITERIA,
    STATE_ACEPTADA,
    STATE_GENERADA,
    STATE_PENDING,
    STATE_SUSTITUIDA,
)
from shared.exceptions.handlers import AssistantUnavailable

REPLY = json.dumps({
    "claridadDelProblema": {"score": 8, "justification": "Problema nítido y medible."},
    "factibilidad": {"score": 7, "justification": "Tecnología disponible."},
    "impactoEsperado": {"score": 9, "justification": "Ahorro de horas relevante."},
    "alineacionEstrategica": {"score": 8, "justification": "Encaja en la línea digital."},
    "gradoDeInnovacion": {"score": 6, "justification": "Mejora incremental clara."},
})


class FakeAssistant:
    def __init__(self, available: bool = True, reply: str = REPLY):
        self.available = available
        self.reply = reply
        self.prompts: list[str] = []

    def ping(self) -> bool:
        return self.available

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if not self.available:
            raise AssistantUnavailable("ASSISTANT_UNAVAILABLE", "fuera de línea")
        return self.reply


class FakeLedger:
    def __init__(self, ideas: dict[str, dict] | None = None):
        self.ideas = ideas or {}

    def get(self, idea_id: str) -> dict | None:
        return self.ideas.get(idea_id)

    def update(self, idea_id: str, changes: dict) -> dict:
        idea = self.ideas[idea_id]
        idea.update(changes)
        return idea

    def list_by_state(self, state: str, owner_id: str | None = None):
        return [idea for idea in self.ideas.values() if idea.get("state") == state]


def _published_idea(idea_id: str = "idea_pub", evaluation: dict | None = None) -> dict:
    idea = {
        "id": idea_id,
        "state": "VALIDADA_PUBLICA",
        "publishedAt": "2026-01-01T00:00:00",
        "fields": {"title": "Flujo digital", "proponent": {"name": "Ana", "area": "Compras",
                                                           "contact": "a@x"},
                   "description": "d", "problem": "p", "expectedBenefit": "b",
                   "strategicAlignment": "s"},
    }
    if evaluation is not None:
        idea["evaluation"] = evaluation
    return idea


# -- interpretation (case 14: an uninterpretable reply is a failure) ------------------


def test_interprets_the_five_criteria_in_canonical_order() -> None:
    criteria = interpret_evaluation(REPLY)
    assert criteria is not None
    assert [item["criterion"] for item in criteria] == list(EVALUATION_CRITERIA)
    assert {item["criterion"]: item["score"] for item in criteria} == {
        "claridadDelProblema": 8, "factibilidad": 7, "impactoEsperado": 9,
        "alineacionEstrategica": 8, "gradoDeInnovacion": 6,
    }
    assert all(item["justification"] for item in criteria)


def test_interprets_the_reply_wrapped_in_fences_or_prose() -> None:
    fenced = "Claro, evaluación:\n```json\n" + REPLY + "\n```"
    assert interpret_evaluation(fenced) is not None
    pimpled = "Proceso mental " + REPLY
    assert interpret_evaluation(pimpled) is not None


def test_missing_or_unknown_criteria_fail() -> None:
    reply = json.loads(REPLY)
    del reply["factibilidad"]
    assert interpret_evaluation(json.dumps(reply)) is None
    reply = json.loads(REPLY)
    reply["invento"] = {"score": 5, "justification": "x"}
    reply["factibilidad"] = {"score": 5, "justification": "x"}
    assert interpret_evaluation(json.dumps(reply)) is None


def test_score_out_of_bounds_or_wrong_type_fails() -> None:
    for score in (0, 11, 8.0, "8", True):
        reply = json.loads(REPLY)
        reply["factibilidad"] = {"score": score, "justification": "x"}
        assert interpret_evaluation(json.dumps(reply)) is None


def test_blank_justification_fails() -> None:
    reply = json.loads(REPLY)
    reply["factibilidad"] = {"score": 7, "justification": "   "}
    assert interpret_evaluation(json.dumps(reply)) is None


def test_non_json_reply_fails() -> None:
    assert interpret_evaluation("no hay JSON aquí") is None


# -- generation at the debate's closure (case 22: the platform is never blocked) -------


def test_generation_writes_evaluation_and_snapshot() -> None:
    ledger = FakeLedger({"idea_pub": _published_idea()})
    assistant = FakeAssistant()

    status = generate_evaluation(ledger, assistant, idea_id="idea_pub",
                                 company_context=None, now="2026-01-01T00:00:00")

    assert status == STATE_GENERADA
    idea = ledger.get("idea_pub")
    assert idea["evaluation"]["status"] == STATE_GENERADA
    assert idea["evaluation"]["author"] == EVALUATION_AI_AUTHOR
    assert [item["criterion"] for item in idea["evaluation"]["criteria"]] == list(EVALUATION_CRITERIA)
    assert idea["evaluation"]["createdAt"] == "2026-01-01T00:00:00"
    assert idea["evaluation"]["decidedBy"] is None and idea["evaluation"]["decidedAt"] is None
    # The immutable snapshot mirrors the AI's judgment (RF-26).
    assert idea["aiEvaluation"] == idea["evaluation"]
    assert len(assistant.prompts) == 1


def test_generation_down_keeps_the_idea_pending() -> None:
    ledger = FakeLedger({"idea_pub": _published_idea()})
    assistant = FakeAssistant(available=False)

    assert generate_evaluation(ledger, assistant, idea_id="idea_pub",
                               company_context=None, now="2026-01-01T00:00:00") == STATE_PENDING

    idea = ledger.get("idea_pub")
    assert idea["evaluation"] == {"status": STATE_PENDING}
    assert "aiEvaluation" not in idea
    assert assistant.prompts == []


def test_generation_with_uninterpretable_reply_keeps_pending() -> None:
    ledger = FakeLedger({"idea_pub": _published_idea()})
    assistant = FakeAssistant(reply="prosa sin JSON")

    assert generate_evaluation(ledger, assistant, idea_id="idea_pub",
                               company_context=None, now="2026-01-01T00:00:00") == STATE_PENDING
    assert ledger.get("idea_pub")["evaluation"] == {"status": STATE_PENDING}


def test_generation_never_clobbers_a_decided_evaluation() -> None:
    # A re-opened-and-reclosed debate must not erase the specialist's decision:
    # an evaluation that is not PENDING is left untouched (no AI call, no write).
    decided = {
        "status": STATE_ACEPTADA,
        "criteria": [],
        "author": EVALUATION_AI_AUTHOR,
        "createdAt": "2026-01-01T00:00:00",
        "decidedBy": "u_solo",
        "decidedAt": "2026-01-02T00:00:00",
    }
    ledger = FakeLedger({"idea_pub": _published_idea(evaluation=dict(decided))})
    assistant = FakeAssistant()

    assert generate_evaluation(ledger, assistant, idea_id="idea_pub",
                               company_context=None, now="2026-01-03T00:00:00") == STATE_ACEPTADA
    assert ledger.get("idea_pub")["evaluation"] == decided
    assert "aiEvaluation" not in ledger.get("idea_pub")
    assert assistant.prompts == []


# -- retry of the pending evaluations (case 22, at every verification) -----------------


def test_retry_generates_the_pending_evaluations() -> None:
    ledger = FakeLedger({
        "idea_a": _published_idea("idea_a", {"status": STATE_PENDING}),
        "idea_b": _published_idea("idea_b", {"status": STATE_PENDING}),
    })
    assistant = FakeAssistant()

    generated = retry_pending_evaluations(ledger, assistant, now="2026-01-02T00:00:00")

    assert generated == 2
    for idea_id in ("idea_a", "idea_b"):
        idea = ledger.get(idea_id)
        assert idea["evaluation"]["status"] == STATE_GENERADA
        assert idea["aiEvaluation"] == idea["evaluation"]


def test_retry_ignores_decided_or_generated_ideas() -> None:
    ai = {"status": STATE_GENERADA, "criteria": [], "author": EVALUATION_AI_AUTHOR,
          "createdAt": "2026-01-01T00:00:00", "decidedBy": None, "decidedAt": None}
    ledger = FakeLedger({
        "idea_a": _published_idea("idea_a", dict(ai)),
        "idea_b": _published_idea("idea_b", {"status": STATE_ACEPTADA, "criteria": []}),
        "idea_c": _published_idea("idea_c", {"status": STATE_SUSTITUIDA, "criteria": []}),
        "idea_d": _published_idea("idea_d"),  # no evaluation at all yet
    })
    assistant = FakeAssistant()

    generated = retry_pending_evaluations(ledger, assistant, now="2026-01-02T00:00:00")

    assert generated == 0  # nothing to retry
    assert ledger.get("idea_a")["evaluation"]["status"] == STATE_GENERADA
    assert ledger.get("idea_b")["evaluation"]["status"] == STATE_ACEPTADA
    assert ledger.get("idea_c")["evaluation"]["status"] == STATE_SUSTITUIDA
    assert "evaluation" not in ledger.get("idea_d")
    assert assistant.prompts == []


def test_retry_is_a_no_op_when_the_assistant_is_down() -> None:
    ledger = FakeLedger({"idea_a": _published_idea("idea_a", {"status": STATE_PENDING})})
    assistant = FakeAssistant(available=False)

    assert retry_pending_evaluations(ledger, assistant, now="2026-01-02T00:00:00") == 0
    assert ledger.get("idea_a")["evaluation"] == {"status": STATE_PENDING}
