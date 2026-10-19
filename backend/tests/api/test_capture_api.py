"""Capture router API tests (T-031, RF-2..RF-7, plan §3.3/§3.4).

Covers the proponent surface of `/capture`:
  - `POST /capture/start` (200): new conversation with greeting + first
    question (RF-2; RF-5 chips are generated per turn by the assistant, D7
    replacement), resume of the single ``ACTIVA`` (case 8), and the manual
    signal without the assistant (RF-7 case 1, no orphan conversation);
  - `GET /capture/assistant-status` (200): the availability probe
    OK/UNAVAILABLE (RF-7 case 1);
  - `POST /capture/messages` (200): the complete assisted flow — narrative
    extraction (RF-3), title suggestion turn (RF-4), chip turns as complete
    answers using only the options offered on the turn (RF-5, D7), the 7
    fields closing to the editable summary (RF-6);
    mid-conversation assistant failure: 503 with the captured fields as
    pre-fill (RF-7 case 2, RNF-10);
  - `POST /capture/title` (200): the RF-4 actions on the title turn;
  - `POST /capture/finish` (201 {ideaId, state, origin}): the idea in
    EN_DESARROLLO origin `asistida` (RF-6); a failed registration (422, RNF-5)
    leaves no partial record (case 17) and the conversation still in RESUMEN;
  - `POST /capture/activate-manual` (200): the conversation moves to
    CONTINGENCIA with its fields pre-filled (RNF-10);
  - guards: 401 without session, 403 for other roles.

The `auth` fixture injects in-memory stores and a programmable assistant
mock by default (deterministic, no network to the local Ollama).
"""

import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app import deps as deps_module
from app.main import app as main_app
from features.assistant.domain.prompts import FIELD_LABELS
from features.auth.infrastructure.token_store import TokenStore
from features.capture.infrastructure.conversation_store import ConversationStore
from features.ideas.infrastructure.idea_store import IdeaStore
from features.org.infrastructure.org_store import OrgStore
from shared.utils.password import hash_password
from tests.conftest import (
    InMemoryDirectory,
    InMemoryStore,
    OllamaMock,
    options_for_label,
    turn_options_json,
)

PROPOSER = "u_ana"


class ProgrammableMock:
    """`OllamaMock` whose extraction/titling replies are programmed in-place
    (the prompt markers are the same the unit tests use)."""

    def __init__(self, available: bool = True) -> None:
        self.inner = OllamaMock(available=available)
        self.extract: dict = {}
        self.title = "Flujo digital de compras"

    def ping(self) -> bool:
        return self.inner.ping()

    def generate(self, prompt: str) -> str:
        self.inner.prompts.append(prompt)
        if 'JSON esperado: {"options' in prompt:  # the per-turn options prompt
            return turn_options_json(prompt, compact={})
        if "JSON esperado: {\"title" in prompt:
            return json.dumps({"title": self.title}, ensure_ascii=False)
        if "Campos pendientes" in prompt:
            return json.dumps(self.extract, ensure_ascii=False)
        return json.dumps({}, ensure_ascii=False)

    @property
    def prompts(self) -> list[str]:
        return self.inner.prompts

    def make_unavailable(self) -> "ProgrammableMock":
        self.inner.available = False
        return self


@pytest.fixture()
def directory() -> InMemoryDirectory:
    store = InMemoryDirectory()
    store.create({
        "id": PROPOSER,
        "username": "ana",
        "name": "Ana Torres",
        "area": "Compras",
        "contact": "ana.torres@innov-ia.local",
        "roles": ["proponente"],
        "active": True,
        "passwordHash": hash_password("clave123"),
        "shouldChangePassword": False,
    })
    store.create({
        "id": "u_beto",
        "username": "beto",
        "name": "Beto Ruiz",
        "area": "Logística",
        "contact": "beto.ruiz@innov-ia.local",
        "roles": ["proponente"],
        "active": True,
        "passwordHash": hash_password("clave123"),
        "shouldChangePassword": False,
    })
    store.create({
        "id": "u_solo",
        "username": "solo",
        "name": "Solo",
        "area": "",
        "contact": "",
        "roles": ["especialista"],
        "active": True,
        "passwordHash": hash_password("clave123"),
        "shouldChangePassword": False,
    })
    return store


@pytest.fixture()
def idea_ledger() -> IdeaStore:
    return IdeaStore(InMemoryStore(), InMemoryStore())


@pytest.fixture()
def conversation_store() -> ConversationStore:
    return ConversationStore(InMemoryStore())


@pytest.fixture()
def assistant() -> ProgrammableMock:
    return ProgrammableMock()


@pytest.fixture()
def org_store() -> OrgStore:
    return OrgStore(InMemoryStore())


@pytest.fixture()
def auth(directory, idea_ledger, conversation_store, assistant, org_store):
    """Issues bearer-authenticated clients against the in-memory stores."""
    token_store = TokenStore(InMemoryStore(), ttl_minutes=480, now_factory=datetime.now)
    main_app.dependency_overrides[deps_module.get_user_directory] = lambda: directory
    main_app.dependency_overrides[deps_module.get_token_store] = lambda: token_store
    main_app.dependency_overrides[deps_module.get_idea_ledger] = lambda: idea_ledger
    main_app.dependency_overrides[deps_module.get_conversation_store] = (
        lambda: conversation_store
    )
    main_app.dependency_overrides[deps_module.get_assistant_client] = lambda: assistant
    main_app.dependency_overrides[deps_module.get_org_store] = lambda: org_store
    # T-062: /capture/start's background check must not reach the real stores.
    main_app.dependency_overrides[deps_module.get_assistant_check] = (
        lambda: (lambda: {"status": "OK", "refined": 0, "failed": 0, "pending": 0})
    )

    def _client(user_id: str = PROPOSER, token: bool = True) -> TestClient:
        if not token:
            return TestClient(main_app)
        roles = tuple(directory.get(user_id)["roles"])
        session = token_store.issue(user_id, roles, now=datetime.now())
        return TestClient(main_app, headers={"Authorization": f"Bearer {session.token}"})

    return _client


def _structure(**overrides: dict) -> dict:
    """The structured field (`proponent`) as a valid object (§2.2)."""
    data = {
        "proponent": {"name": "Ana Torres", "area": "Compras",
                      "contact": "ana.torres@innov-ia.local"},
    }
    data.update(overrides)
    return data


def _full_flow(client: TestClient, assistant: ProgrammableMock) -> str:
    """Drives the assisted chat to the RESUMEN state and returns the
    conversation id (start → narrative → title → 4 chip turns)."""
    start = client.post("/capture/start")
    assert start.status_code == 200
    conv_id = start.json()["conversation"]["id"]
    # The opening turn is `description`: free narrative, no chips (RF-5, D7 —
    # chips are generated per turn, only for chip-eligible fields on landing).
    turn = start.json()["assistant"]
    assert turn["currentField"] == "description"
    assert turn["quickOptions"] == []
    # The proponent is prefilled from the account (spec §5.2): only the 5
    # remaining fields are walked (RF-3 order), the last landing on RESUMEN.

    assistant.extract = {"description": "Reducir los tiempos de compra con un flujo digital."}
    reply = client.post("/capture/messages", json={"conversationId": conv_id,
                                                   "message": "Quiero reducir los tiempos de compra."})
    assert reply.status_code == 200
    turn = reply.json()["assistant"]
    assert turn["currentField"] == "title"
    assert turn["titleSuggestion"]["text"] == "Flujo digital de compras"

    reply = client.post("/capture/title", json={"conversationId": conv_id, "action": "accept"})
    assert reply.status_code == 200
    turn = reply.json()["assistant"]
    assert turn["currentField"] == "problem"

    # Each of the 4 remaining fields is answered with the per-turn option the
    # assistant offered (RF-5, D7: a chip is only valid when actually offered).
    for field in ("problem", "expectedBenefit", "strategicAlignment"):
        assert turn["currentField"] == field
        reply = client.post("/capture/messages",
                            json={"conversationId": conv_id,
                                  "quickOptionSelected": turn["quickOptions"][0]})
        assert reply.status_code == 200
        if reply.json()["state"] != "RESUMEN":
            turn = reply.json()["assistant"]
    assert reply.json()["state"] == "RESUMEN"
    summary = reply.json()["summary"]
    assert len(summary) == 6
    return conv_id


def test_guard_requires_a_session_and_the_proponent_role(auth) -> None:
    assert auth(token=False).get("/capture/assistant-status").status_code == 401
    assert auth(token=False).post("/capture/start").status_code == 401
    specialist = auth(user_id="u_solo")
    assert specialist.get("/capture/assistant-status").status_code == 403
    assert specialist.post("/capture/start").status_code == 403
    assert specialist.post("/capture/finish", json={"captured": {}}).status_code == 403


def test_assistant_status_reports_ok_and_unavailable(auth, assistant) -> None:
    client = auth()
    assert client.get("/capture/assistant-status").json() == {"status": "OK"}
    assistant.make_unavailable()
    assert client.get("/capture/assistant-status").json() == {"status": "UNAVAILABLE"}
    # The probe never touches the generate path (no refinement here, T-031).
    assert assistant.prompts == []


def test_start_unavailable_returns_manual_without_a_conversation(auth, assistant,
                                                                 conversation_store) -> None:
    """Case 1: assistant down at start → the manual signal, nothing persisted."""
    assistant.make_unavailable()
    client = auth()
    response = client.post("/capture/start")
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "manual"
    assert body["conversation"] is None
    assert "asistente no está disponible" in body["manual"]["notice"]
    # The proponent prefill travels with the form (spec §5.2, RNF-10).
    proponent = json.loads(body["manual"]["capturedFields"]["proponent"])
    assert proponent["name"] == "Ana Torres"
    assert conversation_store.list() == []


def test_start_resumes_the_existing_active_conversation(auth, assistant,
                                                        conversation_store) -> None:
    """Case 8: a second start resumes, never creates a second conversation."""
    client = auth()
    first = client.post("/capture/start").json()
    first_id = first["conversation"]["id"]
    assistant.extract = {"description": "Una idea con descripción."}
    client.post("/capture/messages",
                json={"conversationId": first_id, "message": "mi idea"})
    second = client.post("/capture/start").json()
    assert second["resumed"] is True
    assert second["conversation"]["id"] == first_id
    assert len(conversation_store.list()) == 1


def test_full_assisted_flow_finishes_with_a_201_idea(auth, assistant,
                                                     conversation_store, idea_ledger) -> None:
    """Plan §3.3: start → messages → title → RESUMEN → finish 201 (RF-6)."""
    client = auth()
    conv_id = _full_flow(client, assistant)
    # The summary is editable (RF-6): the confirmed payload corrects the two
    # structured fields into their objects (plan §2.2) and an edited title.
    result = client.post(
        "/capture/finish",
        json={"conversationId": conv_id,
              "captured": {**_structure(), "title": "Título corregido"}},
    )
    assert result.status_code == 201
    body = result.json()
    assert body["state"] == "EN_DESARROLLO"
    assert body["origin"] == "asistida"
    assert body["ideaId"].startswith("idea_")
    idea = idea_ledger.get(body["ideaId"])
    assert idea["ownerId"] == PROPOSER
    assert idea["title"] == "Título corregido"
    assert idea["proponent"]["contact"] == "ana.torres@innov-ia.local"
    assert conversation_store.get(conv_id)["state"] == "TERMINADA"
    # Exactly one idea was registered by the capture (no partial record).
    assert len(idea_ledger.list()) == 1


def test_finish_without_confirmation_is_a_422_with_no_partial_record(
        auth, assistant, conversation_store, idea_ledger) -> None:
    """Case 17 + RNF-5/case 12: the proponent was prefilled from the account
    (spec §5.2) but the confirmed summary carries an invalid contact —
    confirming is a 422; nothing is registered and the conversation keeps the
    summary for a corrected retry."""
    client = auth()
    conv_id = _full_flow(client, assistant)
    # The confirmed summary wins over the stored value: an invalid proponent
    # contact (neither a valid e-mail nor a phone) fails the 6-field check.
    bad = _structure(proponent={"name": "Ana Torres", "area": "Compras",
                                "contact": "no-es-una-clave"})
    result = client.post("/capture/finish", json={"conversationId": conv_id, "captured": bad})
    assert result.status_code == 422
    assert result.json()["error"]["code"] == "IDEA_FIELDS_INVALID"
    assert result.json()["error"]["details"]["fields"] == ["proponent"]
    assert idea_ledger.list() == []  # no draft, no partial record (case 7/17)
    assert conversation_store.get(conv_id)["state"] == "RESUMEN"
    # The next attempt with the corrected fields succeeds (the retry works).
    retry = client.post("/capture/finish",
                        json={"conversationId": conv_id, "captured": _structure()})
    assert retry.status_code == 201
    assert len(idea_ledger.list()) == 1


def test_finish_from_a_non_summary_state_is_a_409(auth, assistant, idea_ledger,
                                                  conversation_store) -> None:
    """Case 7: a conversation still in flight (ACTIVA) cannot finish — even a
    perfect payload registers nothing."""
    client = auth()
    start = client.post("/capture/start").json()
    conv_id = start["conversation"]["id"]
    result = client.post(
        "/capture/finish",
        json={"conversationId": conv_id,
              "captured": {"title": "t", **_structure()}},
    )
    assert result.status_code == 409
    assert idea_ledger.list() == []
    assert conversation_store.get(conv_id)["state"] == "ACTIVA"


def test_a_missing_conversation_is_a_404(auth, assistant) -> None:
    client = auth()
    for path in ("/capture/messages", "/capture/finish", "/capture/activate-manual",
                 "/capture/title"):
        body: dict = {} if path != "/capture/finish" else {"captured": {}}
        if path == "/capture/messages":
            body = {"message": "hola"}
        if path == "/capture/title":
            body = {"action": "accept"}
        assert client.post(path, json=body).status_code == 404


def test_midconversation_fallback_is_prefilled_and_activable(auth, assistant,
                                                             conversation_store) -> None:
    """Case 2: the IA falls mid conversation → 503 with the captured fields,
    and `activate-manual` hands the same fields to the pre-filled form
    (RNF-10)."""
    client = auth()
    start = client.post("/capture/start").json()
    conv_id = start["conversation"]["id"]
    assistant.extract = {"description": "Lo que el usuario ya dijo."}
    client.post("/capture/messages",
                json={"conversationId": conv_id, "message": "mi idea"})
    assistant.make_unavailable()
    response = client.post("/capture/messages",
                           json={"conversationId": conv_id, "message": "y más cosas"})
    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "ASSISTANT_UNAVAILABLE"
    assert body["fallback"]["capturedFields"]["description"] == "Lo que el usuario ya dijo."
    assert conversation_store.get(conv_id)["state"] == "CONTINGENCIA"

    manual = client.post("/capture/activate-manual",
                         json={"conversationId": conv_id})
    assert manual.status_code == 200
    manual_body = manual.json()
    assert manual_body["state"] == "CONTINGENCIA"
    # The partial capture is pre-filled as stored, with nothing lost.
    assert manual_body["capturedFields"]["description"] == "Lo que el usuario ya dijo."
    assert "proponent" in manual_body["capturedFields"]


def test_activate_manual_from_resumen_marks_contingency(auth, assistant) -> None:
    client = auth()
    conv_id = _full_flow(client, assistant)
    response = client.post("/capture/activate-manual",
                           json={"conversationId": conv_id})
    assert response.status_code == 200
    assert response.json()["state"] == "CONTINGENCIA"
    assert len(response.json()["capturedFields"]) == 6
    # The conversation is no longer finishable: its path is the manual form.
    finish = client.post("/capture/finish", json={"conversationId": conv_id,
                                                  "captured": _structure()})
    assert finish.status_code == 409


def test_only_the_owner_can_act_on_a_conversation(auth, assistant) -> None:
    client = auth()
    start = client.post("/capture/start").json()
    conv_id = start["conversation"]["id"]
    # Unauthenticated: the id is useless without a session.
    other = TestClient(main_app)
    assert other.post("/capture/messages",
                      json={"conversationId": conv_id,
                            "message": "hola"}).status_code == 401
    # Another proponent with NO conversation of their own: the id-less
    # resolution finds nothing (404), never Ana's.
    beto = auth(user_id="u_beto")
    assert beto.post("/capture/messages", json={"message": "hola"}).status_code == 404
    assert beto.post("/capture/finish", json={"captured": _structure()}).status_code == 404
    # And holding the id still only reads: he cannot write it (403 in the UC).
    assert beto.post("/capture/messages",
                     json={"conversationId": conv_id, "message": "hola"}).status_code == 403


def test_messages_without_conversation_id_resolves_the_newest(auth, assistant,
                                                              conversation_store) -> None:
    client = auth()
    start = client.post("/capture/start").json()
    conv_id = start["conversation"]["id"]
    assistant.extract = {"description": "Descripción sin id explícito."}
    reply = client.post("/capture/messages", json={"message": "una idea"})
    assert reply.status_code == 200
    assert reply.json()["conversationId"] == conv_id
    assert conversation_store.get(conv_id)["capturedFields"]["description"].startswith(
        "Descripción sin id")


def test_an_empty_message_is_a_400(auth, assistant) -> None:
    client = auth()
    client.post("/capture/start")
    assert client.post("/capture/messages",
                       json={"message": "", "quickOptionSelected": None}).status_code == 400


def test_an_unknown_chip_is_a_400(auth, assistant) -> None:
    """A chip not offered on the turn is rejected (RF-5, D7 replacement)."""
    client = auth()
    start = client.post("/capture/start").json()
    conv_id = start["conversation"]["id"]
    # The opening turn is `description`: no options are offered for it, so any
    # well-formed option — here one for `problem` — is an unknown chip.
    foreign_chip = options_for_label(FIELD_LABELS["problem"])[0]
    reply = client.post("/capture/messages",
                        json={"conversationId": conv_id, "quickOptionSelected": foreign_chip})
    assert reply.status_code == 400
    assert reply.json()["error"]["code"] == "UNKNOWN_QUICK_OPTION"
