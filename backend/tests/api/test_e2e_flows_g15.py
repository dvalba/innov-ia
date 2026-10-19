"""Grupo 15: integraciones extremo a extremo (T-063..T-066, spec G15).

Cierra los cuatro viajes completos sobre una única superficie API en vivo
(TestClient + stores en memoria) con el asistente simulado determinista
(`OllamaMock`, T-007) y la cola de refinamiento REAL compuesta por
`get_assistant_check` (como hace `test_assistant_api.py`), sin tocar código de
producción:

  - T-063 captura asistida: nueva idea → conversación (orden fijo, opciones
    rápidas generadas por turno, título con Aceptar/Otra/Escribir) → resumen
    editable → confirmación → idea EN_DESARROLLO `asistida` visible en
    "Mis ideas";
  - T-064 contingencia: IA caída al inicio → manual con aviso (caso 1);
    cayendo a mitad → 503 con `capturedFields` + manual preinada (caso 2);
    el reintento único de 60 s es transparente (RNF-3) y no se expone aquí;
  - T-065 clarificación: idea manual creada con IA caída → al recuperarse, el
    login procesa la cola (más antigua→reciente) + `IDEA_REFINED` → aceptar
    (versión vigente, sigue EN_DESARROLLO) o "Ajustar" (versión pendiente);
    sin caducidad, idea operativa (caso 5);
  - T-066 validación: solicitud → `IDEA_REQUESTED` a los especialistas →
    aprobar con rastro + `IDEA_PUBLISHED` + visible en catálogo, o rechazar
    con comentario + `IDEA_REJECTED`; autovalidación con rastro (caso 9); el
    contador de la campana refleja cada evento y solo esos.

Smoke manual (Ollama corriendo, registrado en la entrega):
  1. `ollama serve` (m modelo del proyecto) + backend con los stores JSON;
  2. login de un proponente → /captura: completar la conversación con la
     narrativa y los chips, probar Aceptar / Otra / Escribir en el turno de
     título y confirmar el resumen corregido;
  3. detener Ollama de forma súbita (y al inicio) y verificar el aviso manual,
     el prellenado y la captura manual completa;
  4. con la IA caída crear una idea manual, levantar Ollama, volver a entrar
     y verificar la notificación `IDEA_REFINED` y el refine-view (aceptar y
     ajustar);
  5. solicitar publicación, validar/rechazar con un especialista (y con
     autovalidación) y comprobar el catálogo público y la campana.
"""

import json
from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import deps as deps_module
from app.main import app as main_app
from features.auth.infrastructure.token_store import TokenStore
from features.capture.infrastructure.conversation_store import ConversationStore
from features.ideas.domain.idea import Idea
from features.ideas.infrastructure.idea_store import IdeaStore
from features.notifications.infrastructure.notification_store import NotificationStore
from features.org.infrastructure.org_store import OrgStore
from shared.utils.password import hash_password
from tests.conftest import InMemoryDirectory, InMemoryStore, OllamaMock, turn_options_json

PROPOSER = "u_ana"
SPECIALIST = "u_esp"
DUAL = "u_dual"
SPECIALIST_2 = "u_esp2"

_PASSWORD = "clave123"


@pytest.fixture()
def env():
    """Environment for the e2e: in-memory stores + deterministic assistant.

    The on-demand triggers (login / capture start / improve) use the REAL
    `get_assistant_check` composed from the in-memory leaves below, so the
    refinement queue runs end to end over the API.
    """
    directory = InMemoryDirectory()
    directory.create({
        "id": PROPOSER, "username": "ana", "name": "Ana Torres",
        "area": "Compras", "contact": "ana.torres@innov-ia.local",
        "roles": ["proponente"], "active": True,
        "passwordHash": hash_password(_PASSWORD), "shouldChangePassword": False,
    })
    directory.create({
        "id": SPECIALIST, "username": "esp", "name": "Eva Especialista",
        "area": "Calidad", "contact": "eva@innov-ia.local",
        "roles": ["especialista"], "active": True,
        "passwordHash": hash_password(_PASSWORD), "shouldChangePassword": False,
    })
    directory.create({
        "id": DUAL, "username": "dual", "name": "Dario Dual",
        "area": "Operaciones", "contact": "dario@innov-ia.local",
        "roles": ["proponente", "especialista"], "active": True,
        "passwordHash": hash_password(_PASSWORD), "shouldChangePassword": False,
    })
    directory.create({
        "id": SPECIALIST_2, "username": "esp2", "name": "Sofia Segunda",
        "area": "Calidad", "contact": "sofia@innov-ia.local",
        "roles": ["especialista"], "active": True,
        "passwordHash": hash_password(_PASSWORD), "shouldChangePassword": False,
    })
    ledger = IdeaStore(InMemoryStore(), InMemoryStore())
    notifications = NotificationStore(InMemoryStore())
    mock = OllamaMock()
    token_store = TokenStore(InMemoryStore(), ttl_minutes=480, now_factory=datetime.now)
    conversations = ConversationStore(InMemoryStore())
    org_store = OrgStore(InMemoryStore())
    main_app.dependency_overrides[deps_module.get_user_directory] = lambda: directory
    main_app.dependency_overrides[deps_module.get_token_store] = lambda: token_store
    main_app.dependency_overrides[deps_module.get_idea_ledger] = lambda: ledger
    main_app.dependency_overrides[deps_module.get_conversation_store] = (
        lambda: conversations
    )
    main_app.dependency_overrides[deps_module.get_assistant_client] = lambda: mock
    main_app.dependency_overrides[deps_module.get_notification_store] = lambda: notifications
    main_app.dependency_overrides[deps_module.get_org_store] = lambda: org_store
    # The real check (no no-op shield): the triggers run the genuine pass over
    # the in-memory ledger + notification store.
    main_app.dependency_overrides.pop(deps_module.get_assistant_check, None)
    return SimpleNamespace(
        directory=directory, ledger=ledger, notifications=notifications,
        mock=mock, token_store=token_store, conversations=conversations,
        org_store=org_store,
    )


@pytest.fixture()
def api_client(env) -> TestClient:
    with TestClient(main_app) as client:
        yield client  # guarantees the dependency_overrides reset


def _headers(env, user_id: str) -> dict:
    session = env.token_store.issue(
        user_id, tuple(env.directory.get(user_id)["roles"])
    )
    return {"Authorization": f"Bearer {session.token}"}


def _idea_payload(owner_id: str, *, title: str, created_at: str) -> dict:
    return {
        "id": f"idea_{owner_id[2:]}_{created_at[:10]}_{title[:6]}",
        "title": title,
        "proponent": {"name": "Manual", "area": "Area", "contact": "m@innov-ia.local"},
        "description": f"Descripción de {title}.",
        "problem": f"Problema de {title}.",
        "expectedBenefit": f"Beneficio de {title}.",
        "strategicAlignment": f"Alineación de {title}.",
        "ownerId": owner_id, "origin": "manual", "state": "EN_DESARROLLO",
        "createdAt": created_at,
    }


# ------------------------------------------------------------------------
# T-063 — assisted capture e2e
# ------------------------------------------------------------------------


def test_t063_assisted_capture_end_to_end(env, api_client: TestClient) -> None:
    """New idea → conversation (fixed order, per-turn quick options,
    Aceptar/Otra/Escribir) → editable summary → confirm → EN_DESARROLLO
    `asistida` in "Mis ideas"."""
    headers = _headers(env, PROPOSER)
    # "another" requires a candidate distinct from the earlier ones (RF-4), so
    # the mock offers one distinct title per title prompt.
    _titles = iter(("Otro flujo de compras", "Flujo automatizado de compras"))

    def respond(prompt: str) -> str:
        # The per-turn quick options (and any captured compaction) are driven
        # by the field in course named in the prompt itself (D7 replacement).
        if 'JSON esperado: {"options' in prompt:
            return turn_options_json(prompt)
        if "JSON esperado: {\"title" in prompt:
            return json.dumps(
                {"title": next(_titles, None)}, ensure_ascii=False
            )
        return json.dumps(
            {"description": "Digitalizar el flujo de compras de proveedores."},
            ensure_ascii=False,
        )

    env.mock.respond = respond

    status = api_client.get("/capture/assistant-status", headers=headers)
    assert status.status_code == 200
    assert status.json() == {"status": "OK"}

    start = api_client.post("/capture/start", headers=headers)
    assert start.status_code == 200
    start_body = start.json()
    assert start_body["mode"] == "assistant" and start_body["resumed"] is False
    conv_id = start_body["conversation"]["id"]
    # The fixed order starts at `description` (RF-3) and the proponent data
    # comes already prefilled from the account (spec §5.2). `description` is
    # never chip-eligible, so the opening turn offers no quick options and
    # performs no model call.
    assert start_body["assistant"]["currentField"] == "description"
    assert start_body["assistant"]["quickOptions"] == []
    assert list(env.mock.prompts) == [], "the probe never generates"

    reply = api_client.post(
        "/capture/messages",
        json={"conversationId": conv_id,
              "message": "Quiero digitalizar el flujo de compras de proveedores."},
        headers=headers,
    )
    assert reply.status_code == 200
    # RF-4: the turn lands on the title suggestion (fixed actions only).
    assert reply.json()["assistant"]["currentField"] == "title"
    suggestion = reply.json()["assistant"]["titleSuggestion"]
    assert suggestion["actions"] == ["accept", "another", "manual"]

    # "Otra": the new candidate differs from the first, and the turn stays
    # on the title (RF-4).
    other = api_client.post("/capture/title",
                            json={"conversationId": conv_id, "action": "another"},
                            headers=headers)
    assert other.status_code == 200
    assert other.json()["state"] == "ACTIVA"
    assert other.json()["assistant"]["currentField"] == "title"
    assert other.json()["assistant"]["titleSuggestion"]["text"] != suggestion["text"]

    # "Escribir": the typed title is stored UNMODIFIED (RF-4) and the turn
    # advances to the next chip field.
    written = api_client.post(
        "/capture/title",
        json={"conversationId": conv_id, "action": "manual",
              "manualText": "Proceso digital de compras de proveedores"},
        headers=headers,
    )
    assert written.status_code == 200
    assert written.json()["assistant"]["currentField"] == "problem"

    # Each remaining field in course gets its own per-turn quick options
    # (D7 replacement); `proponent` was prefilled, so three chip turns remain,
    # each one answering with the first option OFFERED by that same turn.
    for current in ("problem", "expectedBenefit", "strategicAlignment"):
        turn = written.json() if current == "problem" else reply.json()
        chip = turn["assistant"]["quickOptions"][0]
        reply = api_client.post(
            "/capture/messages",
            json={"conversationId": conv_id, "quickOptionSelected": chip},
            headers=headers,
        )
        assert reply.status_code == 200
    summary = reply.json()
    assert summary["state"] == "RESUMEN"
    assert len(summary["summary"]) == 6

    # RF-6: the summary is EDITABLE before the confirmation — a free
    # correction wins over the chip in the confirmed payload.
    finish = api_client.post(
        "/capture/finish",
        json={"conversationId": conv_id, "captured": {
            "strategicAlignment": "Alineación revisada en el resumen",
        }},
        headers=headers,
    )
    assert finish.status_code == 201
    finish_body = finish.json()
    assert finish_body["state"] == "EN_DESARROLLO"
    assert finish_body["origin"] == "asistida"
    payload = env.ledger.get(finish_body["ideaId"])
    assert payload["title"] == "Proceso digital de compras de proveedores"
    assert payload["strategicAlignment"] == "Alineación revisada en el resumen"
    assert payload["ownerId"] == PROPOSER
    assert env.ledger.list() == [payload], "one idea, no partial records"

    # "Mis ideas" entry (RF-19) with the exact registered data.
    mine = api_client.get("/ideas/me", headers=headers)
    assert mine.status_code == 200
    entries = mine.json()
    assert [(e["id"], e["origin"], e["state"]) for e in entries] == [
        (finish_body["ideaId"], "asistida", "EN_DESARROLLO")]
    assert entries[0]["title"] == "Proceso digital de compras de proveedores"


# ------------------------------------------------------------------------
# T-064 — contingency e2e (RF-7, cases 1 and 2, RNF-3/RNF-10)
# ------------------------------------------------------------------------


def test_t064_contingency_end_to_end(env, api_client: TestClient) -> None:
    """Case 1: IA down at start → manual with the notice, nothing persisted.
    Case 2: IA down mid conversation → 503 + pre-filled manual, and the
    manual registration creates a `manual` idea."""
    headers = _headers(env, PROPOSER)

    # -- Case 1 ------------------------------------------------------------
    env.mock.available = False
    status = api_client.get("/capture/assistant-status", headers=headers)
    assert status.json() == {"status": "UNAVAILABLE"}
    start = api_client.post("/capture/start", headers=headers)
    assert start.status_code == 200
    start_body = start.json()
    assert start_body["mode"] == "manual"
    assert start_body["conversation"] is None
    assert "asistente no está disponible" in start_body["manual"]["notice"]
    proponent = json.loads(start_body["manual"]["capturedFields"]["proponent"])
    assert proponent["name"] == "Ana Torres"
    assert api_client.get("/ideas/me", headers=headers).json() == []
    # The single transparent retry (RNF-3) is internal: never exposed.
    assert "retry" not in json.dumps(start_body).lower()
    env.mock.available = True

    # -- Case 2 ------------------------------------------------------------
    env.mock.respond = lambda prompt: json.dumps(
        {"description": "Reducir los tiempos de compra con un flujo digital."},
        ensure_ascii=False,
    )
    start = api_client.post("/capture/start", headers=headers)
    assert start.json()["mode"] == "assistant"
    conv_id = start.json()["conversation"]["id"]
    reply = api_client.post(
        "/capture/messages",
        json={"conversationId": conv_id,
              "message": "Quiere reducir los tiempos de compra."},
        headers=headers,
    )
    assert reply.status_code == 200
    assert reply.json()["assistant"]["currentField"] == "title"

    env.mock.available = False
    down = api_client.post(
        "/capture/messages",
        json={"conversationId": conv_id, "message": "y más detalles del proceso"},
        headers=headers,
    )
    assert down.status_code == 503
    down_body = down.json()
    assert down_body["error"]["code"] == "ASSISTANT_UNAVAILABLE"
    # RF-7 case 2: the captured fields travel as the pre-fill (RNF-10).
    assert down_body["fallback"]["conversationId"] == conv_id
    assert down_body["fallback"]["capturedFields"]["description"].startswith("Reducir los tiempos")

    # The conversation is now in contingency: the next message never reaches
    # the assistant (no hidden retry is exposed to the client).
    again = api_client.post(
        "/capture/messages",
        json={"conversationId": conv_id, "message": "otra vez"},
        headers=headers,
    )
    assert again.status_code == 503
    assert again.json()["fallback"]["capturedFields"] == down_body["fallback"]["capturedFields"]

    manual = api_client.post("/capture/activate-manual",
                             json={"conversationId": conv_id}, headers=headers)
    assert manual.status_code == 200
    manual_body = manual.json()
    assert manual_body["state"] == "CONTINGENCIA"
    assert manual_body["capturedFields"]["description"].startswith("Reducir los tiempos")
    assert "proponent" in manual_body["capturedFields"]
    # Nothing is lost: the prefill contains exactly the partial capture.
    assert set(manual_body["capturedFields"]) >= {"description", "proponent"}

    # The proponent continues on the MANUAL form (RF-6/G06): the registration
    # creates the idea with origin `manual`.
    created = api_client.post(
        "/ideas",
        json={"origin": "manual",
              "title": "Registro manual tras la contingencia",
              "description": manual_body["capturedFields"]["description"],
              "problem": "Tarea manual repetitiva",
              "expectedBenefit": "Ahorro de tiempo operativo",
              "strategicAlignment": "Agilizar procesos internos",
              "proponent": {"name": "Ana Torres", "area": "Compras",
                            "contact": "ana.torres@innov-ia.local"}},
        headers=headers,
    )
    assert created.status_code == 201
    created_idea = created.json()
    assert created_idea["origin"] == "manual"
    assert created_idea["state"] == "EN_DESARROLLO"
    mine = api_client.get("/ideas/me", headers=headers).json()
    assert mine == [{
        "id": created_idea["id"], "title": created_idea["title"],
        "createdAt": created_idea["createdAt"], "origin": "manual",
        "state": "EN_DESARROLLO",
    }]


# ------------------------------------------------------------------------
# T-065 — clarification / refinement e2e (RF-11/RF-12/RF-13, cases 5, 6)
# ------------------------------------------------------------------------


def _refined_reply(prompt: str) -> str:
    """The deterministic refined version of the idea found in the prompt."""
    for title in ("Idea manual antigua", "Idea manual reciente"):
        if title in prompt:
            return json.dumps({
                "title": f"Refinada: {title}",
                "proponent": {"name": "Ana Torres", "area": "Compras",
                              "contact": "ana.torres@innov-ia.local"},
                "description": f"Descripción profesional de {title}.",
                "problem": f"Problema profesional de {title}.",
                "expectedBenefit": f"Beneficio profesional de {title}.",
                "strategicAlignment": f"Alineación profesional de {title}.",
            }, ensure_ascii=False)
    return "respuesta sin JSON interpretable"


def test_t065_refinement_queue_login_recovery_end_to_end(env, api_client: TestClient) -> None:
    """Manual ideas born during the outage → the login (IA back) runs the
    queue oldest-first + IDEA_REFINED; accepting makes the version VIGENTE
    and the idea stays EN_DESARROLLO (case 5, no expiration)."""
    headers = _headers(env, PROPOSER)
    env.mock.available = False

    idea_a = _idea_payload(PROPOSER, title="Idea manual antigua",
                           created_at="2026-01-01T00:00:00")
    idea_b = _idea_payload(PROPOSER, title="Idea manual reciente",
                           created_at="2026-01-02T00:00:00")
    env.ledger.create(Idea.from_payload(idea_a))
    env.ledger.create(Idea.from_payload(idea_b))

    # While the IA is down the ideas keep operating (case 5): the check
    # short-circuits and touches nothing.
    down = api_client.post("/assistant/check", headers=headers)
    assert down.status_code == 200
    assert down.json() == {"status": "UNAVAILABLE", "refined": 0, "failed": 0, "pending": 2}
    assert env.ledger.versions_of(idea_a["id"]) == []
    assert env.ledger.versions_of(idea_b["id"]) == []

    # The IA is back; the proponent logs in again (RF-11 decision #4): the
    # on-demand pass runs in the background after the response.
    env.mock.available = True
    env.mock.respond = _refined_reply
    login = api_client.post("/auth/login",
                            json={"username": "ana", "password": _PASSWORD})
    assert login.status_code == 200
    assert login.json()["user"]["roles"] == ["proponente"]

    # The whole queue was processed oldest→recent (no expiration, case 5).
    assert idea_a["title"] in env.mock.prompts[0]
    assert idea_b["title"] in env.mock.prompts[1]
    for idea in (idea_a, idea_b):
        versions = env.ledger.versions_of(idea["id"])
        assert [v["requestedBy"] for v in versions] == ["refinement"]
        assert versions[0]["status"] == "PENDIENTE"
        assert versions[0]["fields"]["title"] == f"Refinada: {idea['title']}"
        payload = env.ledger.get(idea["id"])
        assert payload["reviewedByAI"] is True
        assert payload["state"] == "EN_DESARROLLO", "the idea keeps operating"
        assert payload["title"] == idea["title"], "current fields are never overwritten"

    # RF-12/RF-18: one IDEA_REFINED per idea (direct access by ideaId),
    # newest first, all unread (the bell counter = 2, only these events).
    bell = api_client.get("/notifications", headers=headers)
    assert bell.status_code == 200
    bell_body = bell.json()
    assert bell_body["unread"] == 2
    assert [n["ideaId"] for n in bell_body["notifications"]] == [idea_b["id"], idea_a["id"]]
    for notice in bell_body["notifications"]:
        assert notice["type"] == "IDEA_REFINED"
        assert notice["message"] == f"La IA refinó tu idea ({notice['ideaId']})."
        assert notice["read"] is False

    # An explicit verification right after is already empty (idempotence).
    again = api_client.post("/assistant/check", headers=headers)
    assert again.json() == {"status": "OK", "refined": 0, "failed": 0, "pending": 0}

    # refine-view: the pending version is visible in the idea detail...
    detail = api_client.get(f"/ideas/{idea_a['id']}", headers=headers)
    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["idea"]["state"] == "EN_DESARROLLO"
    assert [v["id"] for v in detail_body["versions"]] == [
        env.ledger.versions_of(idea_a["id"])[0]["id"]]

    # ...and accepting it makes the version VIGENTE: the idea adopts the
    # refined fields and stays EN_DESARROLLO (decision #1).
    version_id = env.ledger.versions_of(idea_a["id"])[0]["id"]
    decide = api_client.post(
        f"/ideas/{idea_a['id']}/versions/{version_id}/decide",
        json={"decision": "accept"}, headers=headers,
    )
    assert decide.status_code == 200
    decided = decide.json()
    assert decided["title"] == "Refinada: Idea manual antigua"
    assert decided["state"] == "EN_DESARROLLO"
    assert decided["currentVersionId"] == version_id
    assert decided["reviewedByAI"] is True
    assert env.ledger.versions_of(idea_a["id"])[0]["status"] == "VIGENTE"
    # Marking the notification read leaves the counter at the other only.
    read = api_client.post(f"/notifications/{bell_body['notifications'][1]['id']}/read",
                           headers=headers)
    assert read.status_code == 200
    assert read.json()["read"] is True
    assert api_client.get("/notifications", headers=headers).json()["unread"] == 1

    # "Ajustar": for the other idea, the pending version stays pending while
    # it is reworked (the second decision is the discard; here the refine-view
    # is open with the version still PENDIENTE and usable).
    detail_b = api_client.get(f"/ideas/{idea_b['id']}", headers=headers).json()
    assert detail_b["idea"]["state"] == "EN_DESARROLLO"
    assert detail_b["versions"][0]["status"] == "PENDIENTE"
    assert detail_b["versions"][0]["fields"]["title"] == "Refinada: Idea manual reciente"


# ------------------------------------------------------------------------
# T-066 — validation e2e (RF-14..RF-20, cases 9, 13, bell counter)
# ------------------------------------------------------------------------


def test_t066_validation_end_to_end(env, api_client: TestClient) -> None:
    """Request → IDEA_REQUESTED fanout → approve (trail + IDEA_PUBLISHED +
    catalog) or reject (comment + IDEA_REJECTED); the self-validation (case
    9) keeps the trail; the bell reflects each event and only those."""
    proposer = _headers(env, PROPOSER)
    esp = _headers(env, SPECIALIST)
    dual = _headers(env, DUAL)
    ana = env.directory.get(PROPOSER)

    idea_a = {
        "id": "idea_t066_a", "title": "Aprobar y publicar",
        "proponent": {"name": ana["name"], "area": ana["area"],
                      "contact": ana["contact"]},
        "description": "Descripción A.", "problem": "Problema A.",
        "expectedBenefit": "Beneficio A.",
        "strategicAlignment": "Alineación A.",
        "ownerId": PROPOSER, "origin": "asistida",
        "state": "EN_DESARROLLO", "createdAt": "2026-01-01T00:00:00",
    }
    idea_b = {
        "id": "idea_t066_b", "title": "Rechazar con comentario",
        "proponent": {"name": ana["name"], "area": ana["area"],
                      "contact": ana["contact"]},
        "description": "Descripción B.", "problem": "Problema B.",
        "expectedBenefit": "Beneficio B.",
        "strategicAlignment": "Alineación B.",
        "ownerId": PROPOSER, "origin": "manual",
        "state": "EN_DESARROLLO", "createdAt": "2026-01-02T00:00:00",
    }
    idea_c = {
        "id": "idea_t066_c", "title": "Autovalidación del proponente",
        "proponent": {"name": "Dario Dual", "area": "Operaciones",
                      "contact": "dario@innov-ia.local"},
        "description": "Descripción C.", "problem": "Problema C.",
        "expectedBenefit": "Beneficio C.",
        "strategicAlignment": "Alineación C.",
        "ownerId": DUAL, "origin": "manual",
        "state": "EN_DESARROLLO", "createdAt": "2026-01-03T00:00:00",
    }
    for idea_payload in (idea_a, idea_b, idea_c):
        env.ledger.create(Idea.from_payload(idea_payload))

    # The proponent requests publication of A (RF-10: the only way).
    request_a = api_client.post(f"/ideas/{idea_a['id']}/request-publication",
                                headers=proposer)
    assert request_a.status_code == 200
    assert request_a.json()["state"] == "SOLICITANDO_PUBLICACION"

    # RF-18: the IDEA_REQUESTED fanout reaches EVERY active specialist, and
    # never the proponent.
    for target in (SPECIALIST, SPECIALIST_2):
        target_body = api_client.get("/notifications",
                                     headers=_headers(env, target)).json()
        assert [n["ideaId"] for n in target_body["notifications"]] == [idea_a["id"]]
        assert all(n["type"] == "IDEA_REQUESTED" for n in target_body["notifications"])
        assert target_body["unread"] == 1
    assert api_client.get("/notifications", headers=proposer).json()["unread"] == 0

    # The specialist's review queue (RF-14): the 7 fields, proponent without
    # contact, ordered by request date.
    queue = api_client.get("/validation/queue", headers=esp)
    assert queue.status_code == 200
    assert [entry["id"] for entry in queue.json()] == [idea_a["id"]]
    assert "contact" not in queue.json()[0]["fields"]["proponent"]
    assert queue.json()[0]["origin"] == "asistida"

    # Approve: VALIDADA_PUBLICA + mandatory trail (RNF-8) + IDEA_PUBLISHED.
    approve = api_client.post(f"/validation/{idea_a['id']}/approve", headers=esp)
    assert approve.status_code == 200
    approved = approve.json()
    assert approved["state"] == "VALIDADA_PUBLICA"
    assert approved["publishedBy"] == SPECIALIST
    assert approved["publishedBy"] != PROPOSER
    assert approved["publishedAt"]
    published = [n for n in api_client.get("/notifications", headers=proposer).json()["notifications"]
                 if n["type"] == "IDEA_PUBLISHED"]
    assert [n["ideaId"] for n in published] == [idea_a["id"]]
    assert published[0]["message"] == f"Tu idea ({idea_a['id']}) fue publicada."

    # Catalog (RF-20): the published idea is visible; the contact is never
    # exposed. The other ideas (EN_DESARROLLO) are NOT in the catalog.
    catalog = api_client.get("/catalog/public", headers=esp)
    assert catalog.status_code == 200
    entries = catalog.json()
    assert [entry["id"] for entry in entries] == [idea_a["id"]]
    assert "contact" not in entries[0]["fields"]["proponent"]
    assert entries[0]["fields"]["title"] == "Aprobar y publicar"
    assert entries[0]["fields"]["proponent"]["name"] == ana["name"]
    assert entries[0]["publishedAt"] == approved["publishedAt"]

    # Reject: the request → the mandatory comment (case 13) → EN_DESARROLLO
    # with the issuer's identity + IDEA_REJECTED.
    request_b = api_client.post(f"/ideas/{idea_b['id']}/request-publication",
                                headers=proposer)
    assert request_b.status_code == 200
    empty_comment = api_client.post(f"/validation/{idea_b['id']}/reject",
                                    json={"comment": "   "}, headers=esp)
    assert empty_comment.status_code == 400
    assert env.ledger.get(idea_b["id"])["state"] == "SOLICITANDO_PUBLICACION"
    reject = api_client.post(f"/validation/{idea_b['id']}/reject",
                             json={"comment": "Falta evidencia de adopción."}, headers=esp)
    assert reject.status_code == 200
    rejected = reject.json()
    assert rejected["state"] == "EN_DESARROLLO"
    note = rejected["rejectionNote"]
    assert note["by"] == SPECIALIST
    assert note["byName"] == "Eva Especialista"
    assert note["comment"] == "Falta evidencia de adopción."
    rejected_events = [n for n in api_client.get("/notifications",
                                                 headers=proposer).json()["notifications"]
                       if n["type"] == "IDEA_REJECTED"]
    assert [n["ideaId"] for n in rejected_events] == [idea_b["id"]]
    assert api_client.get("/catalog/public", headers=esp).json() == entries, \
        "the rejected idea never reached the catalog"

    # Case 9: the proponent who is also a specialist self-validates, and the
    # trail stays mandatory (RNF-8) — publisher is the proponent themself.
    request_c = api_client.post(f"/ideas/{idea_c['id']}/request-publication",
                                headers=dual)
    assert request_c.status_code == 200
    approve_c = api_client.post(f"/validation/{idea_c['id']}/approve", headers=dual)
    assert approve_c.status_code == 200
    approved_c = approve_c.json()
    assert approved_c["state"] == "VALIDADA_PUBLICA"
    assert approved_c["publishedBy"] == DUAL
    assert approved_c["publishedAt"]
    # The self-validator is ALSO an active specialist: the fanout of A and B
    # reached them too, on top of their own request + publication.
    dual_events = api_client.get("/notifications", headers=dual).json()["notifications"]
    assert [n["type"] for n in dual_events] == [
        "IDEA_PUBLISHED", "IDEA_REQUESTED", "IDEA_REQUESTED", "IDEA_REQUESTED"]
    assert [n["ideaId"] for n in dual_events] == [
        idea_c["id"], idea_c["id"], idea_b["id"], idea_a["id"]]

    # Catalog with the self-published idea; the rejected one still excluded.
    final_catalog = api_client.get("/catalog/public", headers=esp).json()
    assert [entry["id"] for entry in final_catalog] == [idea_c["id"], idea_a["id"]]

    # Bell (RF-18): each event and ONLY those — Ana: published + rejected;
    # dual: requested + published. Unread markers move only by read actions.
    ana_events = api_client.get("/notifications", headers=proposer).json()
    assert [(n["type"], n["ideaId"]) for n in ana_events["notifications"]] == [
        ("IDEA_REJECTED", idea_b["id"]),
        ("IDEA_PUBLISHED", idea_a["id"]),
    ]
    assert ana_events["unread"] == 2
    api_client.post(f"/notifications/{ana_events['notifications'][0]['id']}/read",
                    headers=proposer)
    assert api_client.get("/notifications", headers=proposer).json()["unread"] == 1
    assert api_client.get("/notifications", headers=dual).json()["unread"] == 4
