"""Base fixtures for the backend test suite (T-007, plan §6.4).

- `app` / `client`: application instance and TestClient. Real file-based
  stores are NOT used in tests: each test injects `InMemoryStore` via
  `app.dependency_overrides` (feature routers support this by exposing
  their dependencies through `Depends`).
- `make_store`: factory for in-memory stores (one per test).
- `ollama_mock`: simulated Ollama client, configurable (`available`,
  `latency`, `respond`), with no real service involved.
"""

import copy
import json
import sys
import time
import uuid
from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared.exceptions.handlers import AssistantUnavailable, DomainError

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


class InMemoryStore:
    """In-memory variant of `JsonStore` (same API) for test injection.

    `load()` returns a deep copy to mirror the file-store behavior (the
    parsed dict is fresh on every read).
    """

    def __init__(self) -> None:
        self._data: dict = {}
        self.path: Path | None = None

    def load(self) -> dict:
        return copy.deepcopy(self._data)

    def save(self, data: dict) -> dict:
        self._data = dict(data)
        return self.load()

    def update(self, mutator: Callable[[dict], dict]) -> dict:
        new_data = mutator(self.load())
        return self.save(new_data)


class InMemoryDirectory:
    """In-memory user directory satisfying the `UserDirectory` contract.

    User payload keys: `id`, `username`, `name`, `area`, `contact`, `roles`
    (list), `active` (bool), `passwordHash`, `shouldChangePassword`
    (bool), `createdAt`.
    """

    def __init__(self) -> None:
        self.users: dict[str, dict] = {}

    def get(self, user_id: str) -> dict | None:
        user = self.users.get(user_id)
        return copy.deepcopy(user) if user is not None else None

    def get_by_username(self, username: str) -> dict | None:
        for user in self.users.values():
            if user["username"] == username:
                return copy.deepcopy(user)
        return None

    def create(self, payload: dict) -> dict:
        payload = dict(payload)
        payload.setdefault("id", "u_" + uuid.uuid4().hex[:8])
        self.users[payload["id"]] = payload
        return self.get(payload["id"])

    def update(self, user_id: str, changes: dict) -> dict:
        if user_id not in self.users:
            raise DomainError("USER_NOT_FOUND", "El usuario no existe.", status_code=404)
        self.users[user_id].update(copy.deepcopy(changes))
        return self.users[user_id]

    def list(self) -> list[dict]:
        return [copy.deepcopy(user) for user in self.users.values()]


class OllamaMock:
    """Simulated Ollama client (plan §6.4).

    Configurable per test through attributes:
      - `available`: True/False (ping and generate).
      - `latency`: seconds "consumed" per call.
      - `respond(prompt)`: programmable reply (fixed by default).
    """

    def __init__(self, available: bool = True, latency: float = 0.0) -> None:
        self.available = available
        self.latency = latency
        self.respond: Callable[[str], str] = self._default_response
        self.ping_calls = 0
        self.prompts: list[str] = []

    def _default_response(self, prompt: str) -> str:
        return "test response"

    def ping(self) -> bool:
        self.ping_calls += 1
        if self.latency:
            time.sleep(self.latency)
        return self.available

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if self.latency:
            time.sleep(self.latency)
        if not self.available:
            raise AssistantUnavailable(
                "ASSISTANT_UNAVAILABLE",
                "El asistente de IA no está disponible (mock).",
            )
        return self.respond(prompt)


def options_for_label(label: str) -> list[str]:
    """Deterministic turn options a mock returns for a field label."""
    return [f"Opción A de {label}", f"Opción B de {label}"]


def turn_options_json(prompt: str, *, compact: dict | None = None) -> str:
    """Mock reply for a turn-options prompt (plan §6.4).

    Extracts the in-progress field from the prompt (`Campo en curso: X.`)
    and answers with options labeled after it, so every field in a flow
    gets distinct, predictable options.
    """
    label = "campo"
    marker = "Campo en curso: "
    if marker in prompt:
        label = prompt.split(marker, 1)[1].split("\n", 1)[0].rstrip(".")
    return json.dumps(
        {"options": options_for_label(label), "compact": compact or {}},
        ensure_ascii=False,
    )


@pytest.fixture()
def app() -> FastAPI:
    from app.main import app as main_app

    return main_app


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


@pytest.fixture()
def make_store() -> Callable[[], InMemoryStore]:
    created: list[InMemoryStore] = []

    def _create() -> InMemoryStore:
        store = InMemoryStore()
        created.append(store)
        return store

    return _create


@pytest.fixture()
def ollama_mock() -> OllamaMock:
    return OllamaMock()


@pytest.fixture()
def make_directory() -> Callable[[], InMemoryDirectory]:
    created: list[InMemoryDirectory] = []

    def _create() -> InMemoryDirectory:
        directory = InMemoryDirectory()
        created.append(directory)
        return directory

    return _create


@pytest.fixture(autouse=True)
def debate_store():
    """Keeps the published-idea debate store in memory for every test.

    Publishing an idea opens its debate (T-073); without this override the
    debate router would fall back to the file-backed store and write to
    `backend/data/debate.json` during the API/e2e suites. One `DebateStore` is
    created per test and shared by every request of the test (the override must
    NOT create a new store per request or the debate opened at approval would
    vanish); tests that exercise the debate can inspect it through this
    fixture.
    """
    from app import deps as deps_module
    from app.main import app as main_app
    from features.debate.infrastructure.debate_store import DebateStore

    store = DebateStore(InMemoryStore())
    main_app.dependency_overrides[deps_module.get_debate_store] = lambda: store
    yield store
    main_app.dependency_overrides.pop(deps_module.get_debate_store, None)


@pytest.fixture(autouse=True)
def debate_days_store():
    """Keeps the global debate-days store in memory for every test (T-089).

    Opening a debate reads the global debate-days setting (RF-24, v2.4); without
    this override the debate opener would fall back to the file-backed store and
    read/write `backend/data/debate_days.json` during the API/e2e suites. One
    `DebateDaysStore` is created per test and shared by every request of the
    test (same reason as the `debate_store` fixture); tests that exercise the
    debate-days endpoints can inspect and configure it through this fixture.
    """
    from app import deps as deps_module
    from app.main import app as main_app
    from features.debate.infrastructure.debate_days_store import DebateDaysStore

    store = DebateDaysStore(InMemoryStore())
    main_app.dependency_overrides[deps_module.get_debate_days_store] = lambda: store
    yield store
    main_app.dependency_overrides.pop(deps_module.get_debate_days_store, None)
