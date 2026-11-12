"""E2E and integration verification of the v2.1 expansion (T-078).

Spec §9 criteria 10-14 plus the limit cases 18, 20 and 22, driven end to
end against the real routers with in-memory stores: the complete
published-idea journey (publication → debate auto-opened at 30 days →
messages and `@asistant` with the linked reply → deadline closure with the
AI summary → 5-criteria AI evaluation → specialist's replacement →
catalog by zones and public detail), the company context injected into
EVERY AI operation (empty document degrades to the case 24 notice), and
the degradation when the assistant is down (`pendingAssistant` retried on
recovery, case 20; `PENDING` evaluation retried on the next verification,
case 22; a closed debate rejects new messages, case 18).
"""

import json
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app import deps as deps_module
from app.main import app as main_app
from features.auth.infrastructure.token_store import TokenStore
from features.ideas.infrastructure.idea_store import IdeaStore
from features.notifications.infrastructure.notification_store import NotificationStore
from features.org.infrastructure.org_store import OrgStore
from features.validation.infrastructure.threshold_store import ThresholdStore
from shared.contracts.evaluation import EVALUATION_CRITERIA
from shared.utils.password import hash_password
from tests.conftest import InMemoryDirectory, InMemoryStore, OllamaMock

PROPOSER = "u_ana"
OTHER = "u_beto"
SPECIALIST = "u_solo"
ADMIN = "u_admin"

PAST_DEADLINE = "2020-01-01T00:00:00"

CRITERIA: list[dict] = [
    {"criterion": key, "score": 9, "justification": f"Juicio propio sobre {key}."}
    for key in EVALUATION_CRITERIA
]


def evaluation_json(scores: list[int]) -> str:
    """A contract-shaped reply: the 5 fixed criteria, each with one of `scores`."""
    return json.dumps(
        {key: {"score": score, "justification": f"Valoración IA de {key}."}
         for key, score in zip(EVALUATION_CRITERIA, scores, strict=True)},
        ensure_ascii=False,
    )


def _fields(**overrides: object) -> dict:
    base: dict = {
        "title": "Portal de compras en línea",
        "proponent": {"name": "Ana Torres", "area": "Compras",
                       "contact": "ana.torres@innov-ia.local"},
        "description": "Migrar las compras a un portal en línea.",
        "problem": "Requisiciones en papel, sin trazabilidad.",
        "expectedBenefit": "40% menos de tiempo de ciclo de compra.",
        "strategicAlignment": "Digitalizar la cadena de suministro.",
    }
    base.update(overrides)
    return base


@pytest.fixture()
def directory() -> InMemoryDirectory:
    store = InMemoryDirectory()
    for user_id, name, roles in (
        (PROPOSER, "Ana Torres", ["proponente"]),
        (OTHER, "Beto Ruiz", ["proponente"]),
        (SPECIALIST, "Solo Esp.", ["especialista"]),
        (ADMIN, "Admin", ["admin"]),
    ):
        store.create({
            "id": user_id,
            "username": user_id.removeprefix("u_"),
            "name": name,
            "area": "Operaciones",
            "contact": f"{user_id.removeprefix('u_')}@innov-ia.local",
            "roles": roles,
            "active": True,
            "passwordHash": hash_password("clave123"),
            "shouldChangePassword": False,
        })
    return store


@pytest.fixture()
def mock() -> OllamaMock:
    return OllamaMock(available=False)


@pytest.fixture()
def idea_ledger() -> IdeaStore:
    return IdeaStore(InMemoryStore(), InMemoryStore())


@pytest.fixture()
def notify_store() -> NotificationStore:
    return NotificationStore(InMemoryStore())


@pytest.fixture()
def org_store() -> OrgStore:
    return OrgStore(InMemoryStore())


@pytest.fixture()
def auth(directory, mock, idea_ledger, notify_store, org_store):
    token_store = TokenStore(InMemoryStore(), ttl_minutes=480, now_factory=datetime.now)
    threshold_store = ThresholdStore(InMemoryStore())

    main_app.dependency_overrides[deps_module.get_user_directory] = lambda: directory
    main_app.dependency_overrides[deps_module.get_token_store] = lambda: token_store
    main_app.dependency_overrides[deps_module.get_idea_ledger] = lambda: idea_ledger
    main_app.dependency_overrides[deps_module.get_assistant_client] = lambda: mock
    main_app.dependency_overrides[deps_module.get_notification_store] = lambda: notify_store
    main_app.dependency_overrides[deps_module.get_threshold_store] = lambda: threshold_store
    main_app.dependency_overrides[deps_module.get_org_store] = lambda: org_store

    def _client(user_id: str = PROPOSER, token: bool = True) -> TestClient:
        if not token:
            return TestClient(main_app)
        roles = tuple(directory.get(user_id)["roles"])
        session = token_store.issue(user_id, roles, now=datetime.now())
        return TestClient(main_app, headers={"Authorization": f"Bearer {session.token}"})

    return _client


def _publish(auth, mock) -> dict:
    """Creates + requests + approves an idea (mock off: no AI runs at
    publication, RF-26). Returns the approve response body."""
    mock.available = False
    idea = auth(PROPOSER).post("/ideas", json=_fields()).json()
    auth(PROPOSER).post(f"/ideas/{idea['id']}/request-publication")
    approved = auth(SPECIALIST).post(f"/validation/{idea['id']}/approve")
    assert approved.status_code == 200
    return approved.json()


def _close(auth, idea_id: str) -> dict:
    """Closes the debate through the real admin path: the deadline moves
    into the past and the next read runs the closure (summary + evaluation)."""
    auth(ADMIN).put(f"/admin/ideas/{idea_id}/debate/deadline",
                    json={"deadline": PAST_DEADLINE})
    return auth(SPECIALIST).get(f"/catalog/{idea_id}/debate").json()


def _stored(auth, idea_id: str) -> dict:
    return auth(PROPOSER).get(f"/ideas/{idea_id}").json()["idea"]


# -- the complete v2.1 journey (spec §9 10-12, 13) ---------------------------------


def test_full_v21_flow_from_publication_to_catalog(auth, mock) -> None:
    mock.respond = lambda _prompt: evaluation_json([8] * 5)

    # 1) Publication: VALIDADA_PUBLICA, no AI call at all (RF-26).
    approved = _publish(auth, mock)
    idea_id = approved["id"]
    assert approved["state"] == "VALIDADA_PUBLICA"
    assert mock.prompts == []

    # 2) The debate auto-opens at publication + 30 days (RF-24).
    debate = auth(OTHER).get(f"/catalog/{idea_id}/debate").json()
    assert debate["open"] is True and debate["closed"] is False
    assert debate["messages"] == []
    published_at = datetime.fromisoformat(approved["publishedAt"])
    assert datetime.fromisoformat(debate["deadline"]) - published_at == timedelta(days=30)

    # 3) Any session writes; `@asistant` answers with the linked reply (RF-25).
    mock.available = True
    base = auth(OTHER).post(f"/catalog/{idea_id}/debate",
                            json={"text": "¿Quién lideraría la migración?"}).json()
    assert base["message"]["processed"] is True and base["assistantReply"] is None
    invocation = auth(OTHER).post(
        f"/catalog/{idea_id}/debate",
        json={"text": "@asistant evalúa el riesgo de la migración",
              "linkedMessageId": base["message"]["id"]},
    )
    assert invocation.status_code == 201
    reply = invocation.json()["assistantReply"]
    assert reply is not None and reply["isAssistant"] is True
    assert reply["linkedMessageId"] == invocation.json()["message"]["id"]
    assert mock.prompts, "the @asistant invocation must reach the assistant"

    # 4) The deadline closure: one-time, AI summary generated (cases 18/21).
    mock.respond = lambda _prompt: evaluation_json([8] * 5)
    closed = _close(auth, idea_id)
    assert closed["closed"] is True and closed["open"] is False
    assert closed["summary"] and closed["summaryAt"] and closed["closedAt"]

    # 5) The AI evaluation was generated at the closure (5 criteria, RF-26).
    stored = _stored(auth, idea_id)
    evaluation = stored["evaluation"]
    assert evaluation["status"] == "GENERADA"
    assert evaluation["author"] == "Asistente (IA)"
    assert [c["criterion"] for c in evaluation["criteria"]] == list(EVALUATION_CRITERIA)
    assert stored["aiEvaluation"]["criteria"] == evaluation["criteria"]

    # 6) The specialist replaces the judgment (case 23); the snapshot survives.
    replaced = auth(SPECIALIST).post(f"/validation/{idea_id}/evaluation",
                                     json={"criteria": CRITERIA})
    assert replaced.status_code == 200
    final = replaced.json()["evaluation"]
    assert final["status"] == "SUSTITUIDA"
    assert final["author"] == "Solo Esp."
    assert final["decidedBy"] == SPECIALIST
    assert replaced.json()["aiEvaluation"]["status"] == "GENERADA"

    # 7) Catalog by zones: en-proceso only (spec §9 criterion 10, D21).
    zones = auth(OTHER).get("/catalog/public").json()["zones"]
    assert [entry["id"] for entry in zones["en-proceso"]] == [idea_id]
    for zone in ("aceptadas", "rechazadas", "archivadas"):
        assert zones[zone] == []

    # 8) The public detail: 6 fields without contact, final state, both judgments.
    detail = auth(OTHER).get(f"/catalog/{idea_id}").json()
    assert set(detail["fields"]) == {
        "title", "proponent", "description", "problem",
        "expectedBenefit", "strategicAlignment",
    }
    assert detail["fields"]["proponent"] == {"name": "Ana Torres", "area": "Compras"}
    assert "ana.torres@innov-ia.local" not in json.dumps(detail, ensure_ascii=False)
    assert detail["state"] == "VALIDADA_PUBLICA"
    assert detail["decision"] is None
    assert detail["evaluation"]["status"] == "SUSTITUIDA"
    assert detail["aiEvaluation"]["status"] == "GENERADA"


# -- the company context in every AI operation (spec §9 criterion 13, D13) ----------


def test_an_empty_company_context_degrades_to_the_notice_case_24(auth, mock) -> None:
    from features.assistant.domain.prompts import NO_CONTEXT_NOTICE

    approved = _publish(auth, mock)
    idea_id = approved["id"]
    mock.available = True
    mock.respond = lambda _prompt: evaluation_json([8] * 5)

    base = auth(OTHER).post(f"/catalog/{idea_id}/debate",
                            json={"text": "Sobre esto necesito criterio."}).json()
    auth(OTHER).post(f"/catalog/{idea_id}/debate",
                     json={"text": "@asistant ¿y aquí?",
                           "linkedMessageId": base["message"]["id"]})
    _close(auth, idea_id)

    # The @asistant prompt and the closure (summary + evaluation) all carry
    # the exact case 24 notice: the AI operates without a context.
    assert mock.prompts, "both the @asistant and the closure prompts must have run"
    assert all(NO_CONTEXT_NOTICE in prompt for prompt in mock.prompts)


def test_the_stored_company_context_is_injected_in_the_ai_operations(
        auth, mock, org_store) -> None:
    saved = auth(ADMIN).put("/admin/contexto", json={
        "profile": {
            "name": "Grupo Demo",
            "sector": "Industria",
            "description": "Fabricación de componentes.",
            "mission": "Digitalizar la operación.",
            "strategicObjectives": ["Automatización"],
        },
        "guideText": "Apuesta por la automatización y los datos.",
    })
    assert saved.status_code == 200
    assert org_store.get()["profile"]["name"] == "Grupo Demo"

    approved = _publish(auth, mock)
    idea_id = approved["id"]
    mock.available = True
    mock.respond = lambda _prompt: evaluation_json([8] * 5)

    base = auth(OTHER).post(f"/catalog/{idea_id}/debate",
                            json={"text": "¿Alineado con la estrategia?"}).json()
    auth(OTHER).post(f"/catalog/{idea_id}/debate",
                     json={"text": "@asistant ¿qué opinas?",
                           "linkedMessageId": base["message"]["id"]})
    _close(auth, idea_id)

    # Every AI operation was grounded in the stored document (RF-22/D13):
    # the @asistant prompt and the closure prompts render the profile and
    # the guide, never the case 24 notice.
    assert mock.prompts
    for prompt in mock.prompts:
        assert "Grupo Demo" in prompt
        assert "Apuesta por la automatización y los datos." in prompt


# -- limit case 18: a closed debate rejects new messages ----------------------------


def test_a_closed_debate_rejects_new_messages_case_18(auth, mock) -> None:
    idea_id = _publish(auth, mock)["id"]
    mock.available = True
    mock.respond = lambda _prompt: "Se debatió el liderazgo; sin acuerdo final."
    auth(OTHER).post(f"/catalog/{idea_id}/debate", json={"text": "Objeción al plazo."})

    _close(auth, idea_id)

    late = auth(OTHER).post(f"/catalog/{idea_id}/debate",
                            json={"text": "Una última opinión."})
    assert late.status_code == 409
    assert late.json()["error"]["code"] == "DEBATE_CLOSED"
    # The thread is frozen at the closure: the summary is visible and the
    # late message never entered it.
    debate = auth(OTHER).get(f"/catalog/{idea_id}/debate").json()
    assert debate["closed"] is True
    assert debate["summary"] == "Se debatió el liderazgo; sin acuerdo final."
    assert [m["text"] for m in debate["messages"]] == ["Objeción al plazo."]


# -- limit case 20: the @asistant survives the assistant being down ------------------


def test_asistant_down_keeps_the_request_pending_and_retries_case_20(auth, mock) -> None:
    idea_id = _publish(auth, mock)["id"]
    base = auth(OTHER).post(f"/catalog/{idea_id}/debate",
                            json={"text": "Este punto necesita criterio."}).json()
    mock.available = False

    attempt = auth(OTHER).post(
        f"/catalog/{idea_id}/debate",
        json={"text": "@asistant ¿procede?", "linkedMessageId": base["message"]["id"]},
    )
    assert attempt.status_code == 201
    assert attempt.json()["assistantReply"] is None
    pending = attempt.json()["debate"]["pendingAssistant"]
    assert pending is not None
    assert pending["messageId"] == attempt.json()["message"]["id"]

    # The assistant recovers: the next interaction retries the pending
    # request and the reply lands in the thread, answering the @asistant.
    mock.available = True
    mock.respond = lambda _prompt: "Criterio: procede con ajustes de plazo."
    retried = auth(OTHER).post(f"/catalog/{idea_id}/debate",
                               json={"text": "Seguimos discutiendo."})
    assert retried.json()["debate"]["pendingAssistant"] is None
    reply = next(m for m in retried.json()["debate"]["messages"] if m["isAssistant"])
    assert reply["text"] == "Criterio: procede con ajustes de plazo."
    assert reply["linkedMessageId"] == attempt.json()["message"]["id"]
    solved = next(m for m in retried.json()["debate"]["messages"]
                  if m["id"] == attempt.json()["message"]["id"])
    assert solved["processed"] is True


# -- limit case 22: the evaluation survives the assistant being down -----------------


def test_closing_with_the_assistant_down_keeps_the_evaluation_pending_case_22(
        auth, mock) -> None:
    idea_id = _publish(auth, mock)["id"]
    mock.available = False
    auth(OTHER).post(f"/catalog/{idea_id}/debate", json={"text": "Apoyo la iniciativa."})

    # The closure still happens (the platform is never blocked, RF-26/RNF-1).
    closed = _close(auth, idea_id)
    assert closed["closed"] is True
    stored = _stored(auth, idea_id)
    assert stored["state"] == "VALIDADA_PUBLICA"
    assert stored["evaluation"] == {"status": "PENDING"}
    assert stored.get("aiEvaluation") is None

    # The assistant recovers: the next verification retries the PENDING
    # evaluation and generates it (case 22).
    mock.available = True
    mock.respond = lambda _prompt: evaluation_json([8] * 5)
    check = auth(PROPOSER).post("/assistant/check")
    assert check.status_code == 200
    assert set(check.json()) == {"status", "refined", "failed", "pending"}

    stored = _stored(auth, idea_id)
    assert stored["evaluation"]["status"] == "GENERADA"
    assert stored["evaluation"]["author"] == "Asistente (IA)"
    assert stored["aiEvaluation"] is not None

    # And only then the idea becomes calibratable.
    queue = auth(SPECIALIST).get("/validation/queue",
                                 params={"stage": "calibracion"}).json()
    assert [entry["id"] for entry in queue] == [idea_id]
