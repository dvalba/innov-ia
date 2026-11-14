"""Evaluation router API tests (T-074, RF-26, plan §4.8, cases 22-23).

Covers the final-judgment surface end to end with in-memory stores: the
publication runs no AI call (the evaluation is generated at the debate's
closure, RF-26), the AI evaluation generated at the closure (`GENERADA` when
the assistant answers in the contract shape, `PENDING` — case 22 — when it is
down or its reply is uninterpretable, the platform never blocked), the retry
of the `PENDING` evaluations at the next assistant verification, the
specialist's acceptance (409 without an `aiEvaluation` snapshot) and
replacement (the same 5 fixed criteria, 422 with the problems otherwise), and
the "last action wins" rule in both orders (case 23) with the immutable
`aiEvaluation` snapshot kept untouched throughout (RNF-8/RF-26).
"""

import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app import deps as deps_module
from app.main import app as main_app
from features.auth.infrastructure.token_store import TokenStore
from features.ideas.infrastructure.idea_store import IdeaStore
from features.org.infrastructure.org_store import OrgStore
from shared.contracts.evaluation import EVALUATION_CRITERIA
from shared.utils.password import hash_password
from tests.conftest import InMemoryDirectory, InMemoryStore, OllamaMock

PROPOSER = "u_ana"
SPECIALIST = "u_solo"
ADMIN = "u_admin"

PAST_DEADLINE = "2020-01-01T00:00:00"

CRITERIA: list[dict] = [
    {"criterion": key, "score": 10 - index, "justification": f"Juicio sobre {key}."}
    for index, key in enumerate(EVALUATION_CRITERIA)
]


def evaluation_json() -> str:
    """A contract-shaped reply: exactly the 5 criteria, score 1-10 + justification."""
    return json.dumps(
        {key: {"score": 7, "justification": f"Valoración IA de {key}."}
         for key in EVALUATION_CRITERIA},
        ensure_ascii=False,
    )


def _fields(**overrides: object) -> dict:
    base: dict = {
        "title": "Panel de indicadores de compra",
        "proponent": {"name": "Ana Torres", "area": "Compras",
                       "contact": "ana.torres@innov-ia.local"},
        "description": "Consolidar los indicadores de compra en un panel.",
        "problem": "Indicadores dispersos en hojas de cálculo.",
        "expectedBenefit": "Tres horas semanales menos de consolidación.",
        "strategicAlignment": "Decisiones basadas en datos.",
    }
    base.update(overrides)
    return base


@pytest.fixture()
def directory() -> InMemoryDirectory:
    store = InMemoryDirectory()
    store.create({
        "id": PROPOSER, "username": "ana", "name": "Ana Torres",
        "area": "Compras", "contact": "ana@innov-ia.local",
        "roles": ["proponente"], "active": True,
        "passwordHash": hash_password("clave123"), "shouldChangePassword": False,
    })
    store.create({
        "id": SPECIALIST, "username": "solo", "name": "Solo Esp.",
        "area": "Calidad", "contact": "solo@innov-ia.local",
        "roles": ["especialista"], "active": True,
        "passwordHash": hash_password("clave123"), "shouldChangePassword": False,
    })
    store.create({
        "id": ADMIN, "username": "admin", "name": "Admin",
        "area": "Dirección", "contact": "admin@innov-ia.local",
        "roles": ["admin"], "active": True,
        "passwordHash": hash_password("clave123"), "shouldChangePassword": False,
    })
    return store


@pytest.fixture()
def mock() -> OllamaMock:
    return OllamaMock()


@pytest.fixture()
def idea_ledger() -> IdeaStore:
    return IdeaStore(InMemoryStore(), InMemoryStore())


@pytest.fixture()
def auth(directory, mock, idea_ledger):
    token_store = TokenStore(InMemoryStore(), ttl_minutes=480, now_factory=datetime.now)
    org_store = OrgStore(InMemoryStore())

    main_app.dependency_overrides[deps_module.get_user_directory] = lambda: directory
    main_app.dependency_overrides[deps_module.get_token_store] = lambda: token_store
    main_app.dependency_overrides[deps_module.get_idea_ledger] = lambda: idea_ledger
    main_app.dependency_overrides[deps_module.get_assistant_client] = lambda: mock
    main_app.dependency_overrides[deps_module.get_org_store] = lambda: org_store

    def _client(user_id: str = SPECIALIST, token: bool = True) -> TestClient:
        if not token:
            return TestClient(main_app)
        roles = tuple(directory.get(user_id)["roles"])
        session = token_store.issue(user_id, roles, now=datetime.now())
        return TestClient(main_app, headers={"Authorization": f"Bearer {session.token}"})

    return _client


def _publish(auth, mock, *, available: bool, respond=None, **field_overrides) -> dict:
    """Creates + requests + approves an idea; returns the approve response body.

    The publication never runs the AI evaluation: it is generated at the
    debate's closure (RF-26).
    """
    mock.available = available
    if respond is not None:
        mock.respond = respond
    idea = auth(PROPOSER).post("/ideas", json=_fields(**field_overrides)).json()
    auth(PROPOSER).post(f"/ideas/{idea['id']}/request-publication")
    response = auth(SPECIALIST).post(f"/validation/{idea['id']}/approve")
    assert response.status_code == 200
    return response.json()


def _close(auth, idea_id: str) -> dict:
    """Closes the debate: the deadline moves into the past and the next read
    runs the closure (summary + AI evaluation, RF-26). The deadline is fixed
    at opening (T-089), so the test forces the past deadline directly on the
    shared in-memory store. Returns the debate payload."""
    debate_store = main_app.dependency_overrides[deps_module.get_debate_store]()
    debate = debate_store.get_debate(idea_id)
    debate.deadline = PAST_DEADLINE
    debate_store.set(debate)
    return auth(SPECIALIST).get(f"/catalog/{idea_id}/debate").json()


# -- publication: no AI call (the evaluation is born at the closure) ---------------


def test_publishing_no_longer_runs_the_ai_evaluation(auth, mock) -> None:
    body = _publish(auth, mock, available=True, respond=lambda _p: evaluation_json())

    assert body["state"] == "VALIDADA_PUBLICA"
    assert body.get("evaluation") is None
    assert body.get("aiEvaluation") is None
    # No AI call at publication: the evaluation is generated at the debate's
    # closure (RF-26).
    assert mock.prompts == []


def test_closing_the_debate_generates_the_evaluation(auth, mock) -> None:
    body = _publish(auth, mock, available=True, respond=lambda _p: evaluation_json())
    idea_id = body["id"]

    debate = _close(auth, idea_id)
    assert debate["closed"] is True

    stored = auth(PROPOSER).get(f"/ideas/{idea_id}").json()["idea"]
    evaluation = stored["evaluation"]
    assert evaluation["status"] == "GENERADA"
    assert evaluation["author"] == "Asistente (IA)"
    assert evaluation["createdAt"]
    assert evaluation["decidedBy"] is None
    assert evaluation["decidedAt"] is None
    assert [c["criterion"] for c in evaluation["criteria"]] == list(EVALUATION_CRITERIA)
    for criterion in evaluation["criteria"]:
        assert 1 <= criterion["score"] <= 10
        assert criterion["justification"]
    # The immutable snapshot is stored together with the evaluation ...
    assert stored["aiEvaluation"]["criteria"] == evaluation["criteria"]
    assert stored["aiEvaluation"]["author"] == "Asistente (IA)"
    assert stored["aiEvaluation"]["status"] == "GENERADA"
    # ... and only the evaluation prompt went through the assistant.
    assert len(mock.prompts) == 1


def test_closing_with_the_assistant_down_keeps_it_pending_case_22(auth, mock) -> None:
    body = _publish(auth, mock, available=False)

    assert body["state"] == "VALIDADA_PUBLICA"
    assert body["publishedBy"] == SPECIALIST
    assert body["publishedAt"]
    assert body.get("evaluation") is None

    _close(auth, body["id"])

    stored = auth(PROPOSER).get(f"/ideas/{body['id']}").json()["idea"]
    assert stored["state"] == "VALIDADA_PUBLICA"
    assert stored["evaluation"] == {"status": "PENDING"}
    assert stored.get("aiEvaluation") is None
    # The platform was not blocked: the idea is public and the debate closed
    # (RF-26, case 22); the assistant was never reached.
    assert mock.prompts == []


def test_an_uninterpretable_reply_at_the_closure_keeps_the_evaluation_pending(auth, mock) -> None:
    body = _publish(auth, mock, available=True, respond=lambda _p: "no JSON aquí")

    _close(auth, body["id"])

    stored = auth(PROPOSER).get(f"/ideas/{body['id']}").json()["idea"]
    assert stored["evaluation"] == {"status": "PENDING"}
    assert stored.get("aiEvaluation") is None
    # The prompt ran at the closure (case 14: an uninterpretable reply is a
    # failure that keeps the evaluation PENDING).
    assert len(mock.prompts) == 1


# -- retry of the pending evaluations (case 22, at every verification) --------------


def test_pending_evaluation_is_retried_at_the_next_assistant_check(auth, mock) -> None:
    body = _publish(auth, mock, available=False)
    _close(auth, body["id"])
    stored = auth(PROPOSER).get(f"/ideas/{body['id']}").json()["idea"]
    assert stored["evaluation"] == {"status": "PENDING"}

    # The assistant recovers (with a contract reply): the proponent triggers
    # the verification that retries the PENDING evaluation (case 22).
    mock.available = True
    mock.respond = lambda _prompt: evaluation_json()
    check = auth(PROPOSER).post("/assistant/check")
    assert check.status_code == 200
    summary = check.json()
    # The summary is still the 4-key refinement summary (T-062 contract).
    assert set(summary) == {"status", "refined", "failed", "pending"}
    assert summary["status"] == "OK"

    stored = auth(PROPOSER).get(f"/ideas/{body['id']}").json()["idea"]
    assert stored["evaluation"]["status"] == "GENERADA"
    assert stored["evaluation"]["author"] == "Asistente (IA)"
    assert stored["aiEvaluation"] is not None
    stored_criteria = {c["criterion"] for c in stored["evaluation"]["criteria"]}
    assert stored_criteria == set(EVALUATION_CRITERIA)


def test_the_check_does_not_rebuild_a_decided_evaluation(auth, mock) -> None:
    """A decided (accepted/replaced) evaluation never returns to PENDING."""
    body = _publish(auth, mock, available=True, respond=lambda _p: evaluation_json())
    idea_id = body["id"]
    _close(auth, idea_id)
    accept = auth(SPECIALIST).post(f"/validation/{idea_id}/evaluation/accept")
    assert accept.status_code == 200
    assert accept.json()["evaluation"]["status"] == "ACEPTADA"
    # A later verification must not touch it (the guard in
    # `generate_evaluation` never clobbers a decided judgment).
    check = auth(PROPOSER).post("/assistant/check")
    assert check.status_code == 200
    stored = auth(PROPOSER).get(f"/ideas/{idea_id}").json()["idea"]
    assert stored["evaluation"]["status"] == "ACEPTADA"


# -- access guards ------------------------------------------------------------------


def test_evaluation_endpoints_require_session_and_specialist_role(auth) -> None:
    assert auth(token=False).post("/validation/idea_cualquiera/evaluation/accept").status_code == 401
    assert auth(token=False).post("/validation/idea_cualquiera/evaluation",
                                  json={"criteria": CRITERIA}).status_code == 401
    # A pure proponent is out of the review surface (RF-15).
    assert auth(PROPOSER).post("/validation/idea_cualquiera/evaluation/accept").status_code == 403
    assert auth(PROPOSER).post("/validation/idea_cualquiera/evaluation",
                               json={"criteria": CRITERIA}).status_code == 403


# -- POST /validation/{id}/evaluation/accept (RF-26, case 23) ------------------------


def test_accept_makes_the_ai_evaluation_the_final_judgment(auth, mock) -> None:
    body = _publish(auth, mock, available=True, respond=lambda _p: evaluation_json())
    idea_id = body["id"]
    _close(auth, idea_id)

    response = auth(SPECIALIST).post(f"/validation/{idea_id}/evaluation/accept")
    assert response.status_code == 200
    evaluation = response.json()["evaluation"]
    assert evaluation["status"] == "ACEPTADA"
    assert evaluation["author"] == "Asistente (IA)"
    assert evaluation["criteria"] == response.json()["aiEvaluation"]["criteria"]
    assert evaluation["decidedBy"] == SPECIALIST
    assert evaluation["decidedAt"]
    # The immutable snapshot is untouched (its audit stays empty).
    snapshot = response.json()["aiEvaluation"]
    assert snapshot["status"] == "GENERADA"
    assert snapshot["decidedBy"] is None
    assert snapshot["decidedAt"] is None


def test_accept_without_an_ai_evaluation_is_a_409(auth, mock) -> None:
    body = _publish(auth, mock, available=False)
    # The debate closes with the assistant down: the evaluation stays PENDING
    # and there is no snapshot to accept (case 22).
    _close(auth, body["id"])
    response = auth(SPECIALIST).post(f"/validation/{body['id']}/evaluation/accept")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EVALUATION_MISSING"


def test_accept_404_for_an_unknown_idea(auth) -> None:
    assert auth(SPECIALIST).post("/validation/idea_nadie/evaluation/accept").status_code == 404


# -- POST /validation/{id}/evaluation (RF-26, case 23) -------------------------------


def test_replaces_the_final_judgment_with_the_specialist_own(auth, mock) -> None:
    body = _publish(auth, mock, available=True, respond=lambda _p: evaluation_json())
    idea_id = body["id"]
    _close(auth, idea_id)

    response = auth(SPECIALIST).post(f"/validation/{idea_id}/evaluation",
                                     json={"criteria": CRITERIA})
    assert response.status_code == 200
    evaluation = response.json()["evaluation"]
    assert evaluation["status"] == "SUSTITUIDA"
    assert evaluation["author"] == "Solo Esp."
    assert [c["criterion"] for c in evaluation["criteria"]] == list(EVALUATION_CRITERIA)
    assert evaluation["decidedBy"] == SPECIALIST
    assert evaluation["decidedAt"]
    # The AI's snapshot stays visible and untouched (RF-26).
    snapshot = response.json()["aiEvaluation"]
    assert [c["criterion"] for c in snapshot["criteria"]] == list(EVALUATION_CRITERIA)
    assert snapshot["author"] == "Asistente (IA)"
    assert snapshot["status"] == "GENERADA"


def test_last_action_wins_in_both_orders_case_23(auth, mock) -> None:
    # Order A: replace first, then accept (the acceptance re-applies the AI's).
    body = _publish(auth, mock, available=True, respond=lambda _p: evaluation_json())
    idea_id = body["id"]
    _close(auth, idea_id)
    replace = auth(SPECIALIST).post(f"/validation/{idea_id}/evaluation",
                                    json={"criteria": CRITERIA})
    assert replace.status_code == 200
    assert replace.json()["evaluation"]["status"] == "SUSTITUIDA"
    accept = auth(SPECIALIST).post(f"/validation/{idea_id}/evaluation/accept")
    assert accept.status_code == 200
    final = accept.json()["evaluation"]
    assert final["status"] == "ACEPTADA"
    assert final["author"] == "Asistente (IA)"
    assert final["criteria"] == accept.json()["aiEvaluation"]["criteria"]

    # Order B: accept first, then replace (the replacement re-applies).
    body2 = _publish(auth, mock, available=True, respond=lambda _p: evaluation_json(),
                     title="Segunda iniciativa")
    idea_id2 = body2["id"]
    _close(auth, idea_id2)
    accept2 = auth(SPECIALIST).post(f"/validation/{idea_id2}/evaluation/accept")
    assert accept2.status_code == 200
    assert accept2.json()["evaluation"]["status"] == "ACEPTADA"
    replace2 = auth(SPECIALIST).post(f"/validation/{idea_id2}/evaluation",
                                     json={"criteria": CRITERIA})
    assert replace2.status_code == 200
    final2 = replace2.json()["evaluation"]
    assert final2["status"] == "SUSTITUIDA"
    assert final2["author"] == "Solo Esp."


@pytest.mark.parametrize(
    "criteria, problem_fragment",
    [
        (CRITERIA[:4], "exactamente los 5 criterios"),             # one missing
        (CRITERIA[:2] + [CRITERIA[0]] + CRITERIA[3:5],
         "repetido"),                                             # a duplicated one
        (CRITERIA[:4] + [{"criterion": "otroCriterio", "score": 5,
                          "justification": "x"}],
         "desconocido o mal escrito"),                            # unknown
    ],
    ids=["criterio-faltante", "criterio-repetido", "criterio-desconocido"],
)
def test_invalid_criteria_are_a_422_with_the_problems(auth, criteria, problem_fragment) -> None:
    body = _publish(auth, mock, available=False)
    response = auth(SPECIALIST).post(f"/validation/{body['id']}/evaluation",
                                     json={"criteria": criteria})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "EVALUATION_INVALID"
    assert any(problem_fragment in problem for problem in error["details"]["problems"])


def test_an_out_of_range_score_is_a_422(auth, mock) -> None:
    body = _publish(auth, mock, available=False)
    for score in (0, 11):
        bad = [dict(c) for c in CRITERIA]
        bad[0] = {"criterion": CRITERIA[0]["criterion"], "score": score,
                  "justification": "x"}
        response = auth(SPECIALIST).post(f"/validation/{body['id']}/evaluation",
                                         json={"criteria": bad})
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "EVALUATION_INVALID"


def test_a_blank_justification_is_a_422(auth, mock) -> None:
    body = _publish(auth, mock, available=False)
    bad = [dict(c) for c in CRITERIA]
    bad[1] = {"criterion": CRITERIA[1]["criterion"], "score": 5, "justification": "   "}
    response = auth(SPECIALIST).post(f"/validation/{body['id']}/evaluation",
                                     json={"criteria": bad})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "EVALUATION_INVALID"


def test_a_fractional_score_is_rejected_by_the_framework(auth, mock) -> None:
    body = _publish(auth, mock, available=False)
    bad = [dict(c) for c in CRITERIA]
    bad[0] = {"criterion": CRITERIA[0]["criterion"], "score": 8.5, "justification": "x"}
    assert auth(SPECIALIST).post(f"/validation/{body['id']}/evaluation",
                                 json={"criteria": bad}).status_code == 422


def test_replace_404_for_an_unknown_idea(auth) -> None:
    assert auth(SPECIALIST).post("/validation/idea_nadie/evaluation",
                                 json={"criteria": CRITERIA}).status_code == 404
