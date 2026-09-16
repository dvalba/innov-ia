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
