"""Debate router API tests (T-073, RF-24/RF-25, plan §3.1, cases 18-21).

Covers the published-idea debate surface end to end with in-memory stores:
the auto-open on publication (via the real approve flow), posting messages,
the `@asistant` invocation matrix (valid link, no link, dangling link, blank
request), the pending-retry when the assistant is down (case 20), the
deadline closure (once, idempotent) with the AI summary and its pending retry
(cases 18/21), and the admin-only deadline adjustment (audit + re-open).

The `OllamaMock` is a single instance per test so a test can take the
assistant down and back mid-flow (the real client is overridden); the
`debate_store` autouse fixture from `conftest.py` keeps the debates in memory.
"""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import deps as deps_module
from app.main import app as main_app
from features.auth.infrastructure.token_store import TokenStore
from features.ideas.infrastructure.idea_store import IdeaStore
from features.org.infrastructure.org_store import OrgStore
from shared.utils.password import hash_password
from tests.conftest import InMemoryDirectory, InMemoryStore, OllamaMock

PROPOSER = "u_ana"
OTHER = "u_beto"
SPECIALIST = "u_solo"
ADMIN = "u_admin"

PAST_DEADLINE = "2020-01-01T00:00:00"
FUTURE_DEADLINE = "2099-01-01T00:00:00"


def _fields(**overrides: object) -> dict:
    base: dict = {
        "title": "Flujo digital de compras",
        "proponent": {"name": "Ana Torres", "area": "Compras",
                      "contact": "ana.torres@innov-ia.local"},
        "description": "Reducir los tiempos de compra con un flujo digital.",
        "problem": "Revisión manual duplicada del proveedor.",
        "expectedBenefit": "Ahorro de 120 horas mensuales.",
        "strategicAlignment": "Agilizar la cadena de suministro.",
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
    return OllamaMock()


@pytest.fixture()
def auth(directory, mock):
    ledger = IdeaStore(InMemoryStore(), InMemoryStore())
    token_store = TokenStore(InMemoryStore(), ttl_minutes=480, now_factory=datetime.now)
    org_store = OrgStore(InMemoryStore())

    main_app.dependency_overrides[deps_module.get_user_directory] = lambda: directory
    main_app.dependency_overrides[deps_module.get_token_store] = lambda: token_store
    main_app.dependency_overrides[deps_module.get_idea_ledger] = lambda: ledger
    main_app.dependency_overrides[deps_module.get_assistant_client] = lambda: mock
    main_app.dependency_overrides[deps_module.get_org_store] = lambda: org_store

    def _client(user_id: str = PROPOSER, token: bool = True) -> TestClient:
        if not token:
            return TestClient(main_app)
        roles = tuple(directory.get(user_id)["roles"])
        session = token_store.issue(user_id, roles, now=datetime.now())
        return TestClient(main_app, headers={"Authorization": f"Bearer {session.token}"})

    return SimpleNamespace(client=_client)


def _publish(env, title: str = "Flujo digital de compras") -> dict:
    """Creates, requests publication of and approves an idea; returns it
    (`VALIDADA_PUBLICA`, with the debate opened by the approve flow)."""
    idea = env.client(PROPOSER).post("/ideas", json=_fields(title=title)).json()
    requested = env.client(PROPOSER).post(f"/ideas/{idea['id']}/request-publication")
    assert requested.status_code == 200
    approved = env.client(SPECIALIST).post(f"/validation/{idea['id']}/approve")
    assert approved.status_code == 200
    return approved.json()


def _post(env, idea_id: str, text: str, user_id: str = PROPOSER,
          linked_message_id: str | None = None) -> dict:
    response = env.client(user_id).post(
        f"/catalog/{idea_id}/debate",
        json={"text": text, "linkedMessageId": linked_message_id},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _force_deadline(debate_store, idea_id: str, deadline: str) -> None:
    """Moves the deadline past (or ahead) of the clock, bypassing the audit:
    the deadline rule is what is under test, not the admin adjustment. A
    past deadline leaves the debate open (the closure happens at the next
    read/write); a future one re-opens it, mirroring the admin rule."""
    debate = debate_store.get_debate(idea_id)
    assert debate is not None
    debate.deadline = deadline
    if deadline >= datetime.now().isoformat():
        debate.closed = False
        debate.open = True
        debate.closedAt = None
    debate_store.set(debate)


# -- access guards ------------------------------------------------------------------


def test_debate_endpoints_require_session_401(auth) -> None:
    anonymous = auth.client(token=False)
    idea = auth.client(PROPOSER).post("/ideas", json=_fields()).json()
    assert anonymous.get(f"/catalog/{idea['id']}/debate").status_code == 401
    assert anonymous.post(f"/catalog/{idea['id']}/debate",
                          json={"text": "Hola"}).status_code == 401
    assert anonymous.put(f"/admin/ideas/{idea['id']}/debate/deadline",
                         json={"deadline": FUTURE_DEADLINE}).status_code == 401


# -- reading the debate --------------------------------------------------------------


def test_read_debate_404_when_the_idea_was_not_published(auth) -> None:
    idea = auth.client(PROPOSER).post("/ideas", json=_fields()).json()
    response = auth.client().get(f"/catalog/{idea['id']}/debate")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DEBATE_NOT_FOUND"


def test_approve_opens_the_debate_with_a_30_day_deadline(auth, debate_store) -> None:
    approved = _publish(auth)
    idea_id = approved["id"]

    body = auth.client(OTHER).get(f"/catalog/{idea_id}/debate").json()
    assert body["ideaId"] == idea_id
    assert body["closed"] is False
    assert body["open"] is True
    assert body["summary"] is None
    assert body["pendingAssistant"] is None
    assert body["messages"] == []

    published_at = datetime.fromisoformat(approved["publishedAt"])
    deadline = datetime.fromisoformat(body["deadline"])
    assert deadline - published_at == timedelta(days=30)

    # The debate is keyed by the idea id in the (in-memory) debate store.
    assert debate_store.has(idea_id)


def test_read_debate_lists_the_messages_in_order(auth, debate_store) -> None:
    idea = _publish(auth)
    first = _post(auth, idea["id"], "Primera opinión favorable.")
    _post(auth, idea["id"], "Yo discrepo en cuanto al plazo.", user_id=OTHER)

    body = auth.client().get(f"/catalog/{idea['id']}/debate").json()
    messages = body["messages"]
    assert [message["text"] for message in messages] == [
        "Primera opinión favorable.",
        "Yo discrepo en cuanto al plazo.",
    ]
    assert messages[0]["id"] == first["message"]["id"]
    assert messages[0]["authorId"] == PROPOSER
    assert messages[0]["authorName"] == "Ana Torres"
    assert messages[1]["authorId"] == OTHER
    for message in messages:
        assert set(message) == {
            "id", "ideaId", "authorId", "authorName", "text", "createdAt",
            "linkedMessageId", "isAssistant", "processed",
        }
    assert all(message["isAssistant"] is False for message in messages)


# -- posting messages ----------------------------------------------------------------


def test_post_message_201_registers_the_author_and_the_text(auth) -> None:
    idea = _publish(auth)
    body = _post(auth, idea["id"], "Muy buena iniciativa, ¿quién lideraría?")
    assert body["assistantReply"] is None
    assert body["message"]["authorId"] == PROPOSER
    assert body["message"]["authorName"] == "Ana Torres"
    assert body["message"]["processed"] is True
    assert body["message"]["linkedMessageId"] is None
    assert [message["text"] for message in body["debate"]["messages"]] == [
        "Muy buena iniciativa, ¿quién lideraría?"
    ]


def test_post_a_blank_message_is_a_400(auth) -> None:
    idea = _publish(auth)
    for text in ("", "   "):
        response = auth.client().post(f"/catalog/{idea['id']}/debate",
                                      json={"text": text})
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "DEBATE_INVALID"


def test_post_on_a_non_published_idea_is_a_404(auth) -> None:
    idea = auth.client(PROPOSER).post("/ideas", json=_fields()).json()
    response = auth.client().post(f"/catalog/{idea['id']}/debate", json={"text": "Hola"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DEBATE_NOT_FOUND"


# -- the @asistant invocation (RF-25, cases 19-20) -----------------------------------


def test_asistant_with_a_valid_link_replies_in_the_thread(auth, mock) -> None:
    idea = _publish(auth)
    mock.respond = lambda prompt: "Criterio: el ahorro de 120 horas justifica la inversión."
    base = _post(auth, idea["id"], "El plazo de tres meses me parece corto.")

    invocation = auth.client(OTHER).post(
        f"/catalog/{idea['id']}/debate",
        json={"text": "@asistant ¿es viable financieramente?",
              "linkedMessageId": base["message"]["id"]},
    )
    assert invocation.status_code == 201
    # `message` is the participant's `@asistant` message (it references the
    # base message); `assistantReply` is the AI's answer to it (RF-25).
    asistant_msg = invocation.json()["message"]
    assert asistant_msg["linkedMessageId"] == base["message"]["id"]
    assert asistant_msg["isAssistant"] is False
    assert asistant_msg["processed"] is True

    reply = invocation.json()["assistantReply"]
    assert reply is not None
    assert reply["text"] == "Criterio: el ahorro de 120 horas justifica la inversión."
    assert reply["isAssistant"] is True
    assert reply["authorId"] == "assistant"
    assert reply["authorName"] == "Asistente (IA)"
    assert reply["linkedMessageId"] == asistant_msg["id"]  # the reply answers the @asistant message

    debate = invocation.json()["debate"]
    assert debate["pendingAssistant"] is None
    assert len(debate["messages"]) == 3
    assert any("contexto de la empresa" in p.lower() for p in mock.prompts)


def test_asistant_without_a_link_is_a_plain_message(auth, mock) -> None:
    idea = _publish(auth)
    mock.respond = lambda prompt: "Respuesta del asistente"
    body = auth.client().post(
        f"/catalog/{idea['id']}/debate", json={"text": "@asistant"},
    )
    assert body.status_code == 201
    assert body.json()["assistantReply"] is None
    # only the on-publish AI evaluation ran (RF-26); the debate assistant
    # was never invoked (case 19).
    assert len(mock.prompts) == 1 and "comité de evaluación" in mock.prompts[0]
    messages = body.json()["debate"]["messages"]
    assert len(messages) == 1
    assert messages[0]["text"] == "@asistant"
    assert messages[0]["processed"] is True
    assert messages[0]["linkedMessageId"] is None


def test_asistant_with_a_blank_request_still_invokes(auth, mock) -> None:
    idea = _publish(auth)
    mock.respond = lambda prompt: "Análisis general de la idea."
    base = _post(auth, idea["id"], "Base para el análisis general.")
    body = auth.client(OTHER).post(
        f"/catalog/{idea['id']}/debate",
        json={"text": "@asistant   ", "linkedMessageId": base["message"]["id"]},
    )
    assert body.status_code == 201
    assert body.json()["assistantReply"] is not None
    assert "Análisis general de la idea" in body.json()["assistantReply"]["text"]


def test_asistant_with_a_dangling_link_is_a_400(auth) -> None:
    idea = _publish(auth)
    response = auth.client().post(
        f"/catalog/{idea['id']}/debate",
        json={"text": "@asistant ¿lo que dije?", "linkedMessageId": "mesaje_inexistente"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "DEBATE_LINK_INVALID"
    # The failed invocation never reaches the thread.
    debate = auth.client().get(f"/catalog/{idea['id']}/debate").json()
    assert debate["messages"] == []


def test_asistant_down_keeps_the_request_pending(auth, mock, debate_store) -> None:
    idea = _publish(auth)
    base = _post(auth, idea["id"], "Sobre esto pido criterio.")
    mock.available = False
    mock.respond = lambda prompt: "Criterio: procede."

    attempt = auth.client(OTHER).post(
        f"/catalog/{idea['id']}/debate",
        json={"text": "@asistant ¿procede?", "linkedMessageId": base["message"]["id"]},
    )
    assert attempt.status_code == 201
    assert attempt.json()["assistantReply"] is None
    asistant_msg = attempt.json()["message"]
    assert asistant_msg["linkedMessageId"] == base["message"]["id"]
    pending = attempt.json()["debate"]["pendingAssistant"]
    assert pending is not None
    assert pending["messageId"] == asistant_msg["id"]
    assert pending["request"] == "¿procede?"
    stored = next(m for m in debate_store.get(idea["id"])["messages"]
                  if m["id"] == asistant_msg["id"])
    assert stored["processed"] is False

    # The next interaction (a plain post) retries the pending request.
    mock.available = True
    retried = auth.client().post(f"/catalog/{idea['id']}/debate",
                                 json={"text": "Seguimos discutiendo."})
    assert retried.json()["debate"]["pendingAssistant"] is None
    reply = next(m for m in retried.json()["debate"]["messages"] if m["isAssistant"])
    assert reply["text"] == "Criterio: procede."
    assert reply["linkedMessageId"] == asistant_msg["id"]  # the reply answers the @asistant message
    solved = next(m for m in retried.json()["debate"]["messages"]
                  if m["id"] == asistant_msg["id"])
    assert solved["processed"] is True


def test_asistant_pending_retries_on_the_next_read(auth, mock) -> None:
    idea = _publish(auth)
    base = _post(auth, idea["id"], "Este punto necesita criterio.")
    mock.available = False
    mock.respond = lambda prompt: "Respuesta reintentada."

    attempt = auth.client().post(
        f"/catalog/{idea['id']}/debate",
        json={"text": "@asistant", "linkedMessageId": base["message"]["id"]},
    )
    asistant_msg = attempt.json()["message"]
    assert attempt.json()["debate"]["pendingAssistant"] is not None

    mock.available = True
    reading = auth.client(OTHER).get(f"/catalog/{idea['id']}/debate")
    assert reading.status_code == 200
    body = reading.json()
    assert body["pendingAssistant"] is None
    reply = next(m for m in body["messages"] if m["isAssistant"])
    assert reply["text"] == "Respuesta reintentada."
    assert reply["linkedMessageId"] == asistant_msg["id"]  # the reply answers the @asistant message


# -- the deadline closure (RF-24, cases 18/21) ---------------------------------------


def test_first_read_at_the_deadline_closes_and_summarizes(auth, mock, debate_store) -> None:
    idea = _publish(auth)
    _post(auth, idea["id"], "Apoyo total a la iniciativa.", user_id=OTHER)
    mock.respond = lambda prompt: "Se debatió el plazo y el liderazgo; mayoría a favor."

    _force_deadline(debate_store, idea["id"], PAST_DEADLINE)

    closure = auth.client().get(f"/catalog/{idea['id']}/debate")
    assert closure.status_code == 200
    body = closure.json()
    assert body["closed"] is True
    assert body["open"] is False
    assert body["closedAt"]
    assert body["summary"] == "Se debatió el plazo y el liderazgo; mayoría a favor."
    assert body["summaryAt"]

    # The closure is definitive and idempotent: nothing changes on the next read.
    again = auth.client().get(f"/catalog/{idea['id']}/debate").json()
    assert again == body


def test_a_closed_debate_rejects_new_messages_with_409(auth, mock, debate_store) -> None:
    idea = _publish(auth)
    mock.respond = lambda prompt: "Resumen del cierre."
    _force_deadline(debate_store, idea["id"], PAST_DEADLINE)

    response = auth.client(OTHER).post(
        f"/catalog/{idea['id']}/debate", json={"text": "Última opinión, oiga."},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DEBATE_CLOSED"
    # The write that found the deadline also closed the debate.
    body = auth.client().get(f"/catalog/{idea['id']}/debate").json()
    assert body["closed"] is True
    assert body["summary"] is None  # no message was ever posted: no summary (case 21)


def test_the_deadline_closes_even_with_messages_but_no_summary_yet(auth, mock, debate_store) -> None:
    idea = _publish(auth)
    _post(auth, idea["id"], "Objeción sobre el presupuesto.")
    mock.available = False
    _force_deadline(debate_store, idea["id"], PAST_DEADLINE)

    closed = auth.client().get(f"/catalog/{idea['id']}/debate").json()
    assert closed["closed"] is True
    assert closed["summary"] is None  # the assistant is down (RNF-1, case 21)

    # The next read retries the pending summary once the assistant is back.
    mock.available = True
    mock.respond = lambda prompt: "Se objetó el presupuesto; sin acuerdo final."
    summarized = auth.client().get(f"/catalog/{idea['id']}/debate").json()
    assert summarized["summary"] == "Se objetó el presupuesto; sin acuerdo final."
    assert summarized["summaryAt"]


def test_a_debate_closed_without_messages_has_no_summary(auth, mock, debate_store) -> None:
    idea = _publish(auth)
    mock.respond = lambda prompt: "Resumen imposible."
    _force_deadline(debate_store, idea["id"], PAST_DEADLINE)

    body = auth.client().get(f"/catalog/{idea['id']}/debate").json()
    assert body["closed"] is True
    assert body["summary"] is None
    # no message: the summary prompt never ran (case 21); only the on-publish
    # AI evaluation (RF-26) produced a prompt.
    assert len(mock.prompts) == 1 and "comité de evaluación" in mock.prompts[0]


# -- the admin deadline adjustment (RF-24, RNF-11, case 18) ---------------------------


def test_admin_adjusts_the_deadline_with_an_audit_trail(auth, debate_store) -> None:
    idea = _publish(auth)
    idea_id = idea["id"]

    extended = auth.client(ADMIN).put(f"/admin/ideas/{idea_id}/debate/deadline",
                                      json={"deadline": FUTURE_DEADLINE})
    assert extended.status_code == 200
    body = extended.json()
    assert body["deadline"] == FUTURE_DEADLINE
    history = body["deadlineHistory"]
    assert len(history) == 1
    entry = history[0]
    assert entry["by"] == ADMIN
    assert entry["byName"] == "Admin"
    assert entry["at"]
    assert entry["after"] == FUTURE_DEADLINE
    assert entry["before"] != entry["after"]

    # A non-future date closes the (still open) debate straight away.
    closed = auth.client(ADMIN).put(f"/admin/ideas/{idea_id}/debate/deadline",
                                    json={"deadline": PAST_DEADLINE})
    assert closed.status_code == 200
    assert closed.json()["closed"] is True
    assert len(closed.json()["deadlineHistory"]) == 2


def test_admin_reopens_a_closed_debate_with_a_future_deadline(auth, debate_store) -> None:
    idea = _publish(auth)
    _force_deadline(debate_store, idea["id"], PAST_DEADLINE)
    closed = auth.client().get(f"/catalog/{idea['id']}/debate").json()
    assert closed["closed"] is True

    reopened = auth.client(ADMIN).put(f"/admin/ideas/{idea['id']}/debate/deadline",
                                      json={"deadline": FUTURE_DEADLINE})
    assert reopened.status_code == 200
    body = reopened.json()
    assert body["closed"] is False
    assert body["open"] is True
    assert body["closedAt"] is None
    assert len(body["deadlineHistory"]) == 1

    # The re-opened debate admits messages again.
    posted = _post(auth, idea["id"], "El debate vuelve a estar abierto.")
    assert [m["text"] for m in posted["debate"]["messages"]] == [
        "El debate vuelve a estar abierto."
    ]


def test_the_deadline_adjustment_requires_admin(auth) -> None:
    idea = _publish(auth)
    for user_id in (PROPOSER, OTHER, SPECIALIST):
        response = auth.client(user_id).put(
            f"/admin/ideas/{idea['id']}/debate/deadline",
            json={"deadline": FUTURE_DEADLINE},
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "ROLE_NOT_ALLOWED"


def test_the_deadline_adjustment_404s_without_a_debate(auth) -> None:
    idea = auth.client(PROPOSER).post("/ideas", json=_fields()).json()
    response = auth.client(ADMIN).put(f"/admin/ideas/{idea['id']}/debate/deadline",
                                      json={"deadline": FUTURE_DEADLINE})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "DEBATE_NOT_FOUND"


def test_the_deadline_adjustment_rejects_an_invalid_date(auth) -> None:
    idea = _publish(auth)
    response = auth.client(ADMIN).put(f"/admin/ideas/{idea['id']}/debate/deadline",
                                      json={"deadline": "no-es-una-fecha"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "DEBATE_INVALID"
