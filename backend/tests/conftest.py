"""Fixtures de base para las pruebas del backend (T-007, plan §6.4).

- `app` / `client`: instancia de la aplicacion y TestClient. Los stores de
  archivo reales NO se usan en tests: cada test inyecta `InMemoryStore`
  mediante `app.dependency_overrides` (los routers de las features lo apoyan
  exponiendo sus dependencias como `Depends`).
- `make_store`: fabrica stores in-mem a demanda (una por test).
- `ollama_mock`: cliente Ollama simulado y configurable (`disponible`,
  `latencia`, `responder`), sin servicio real.
"""

import sys
import time
from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared.exceptions.handlers import AssistantUnavailable

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


class InMemoryStore:
    """Variante en memoria de `JsonStore` (misma API) para inyectar en tests.

    `cargar()` devuelve una copia profunda para reflejar el comportamiento
    del store por archivo (el dict parseado es nuevo en cada lectura).
    """

    def __init__(self) -> None:
        self._data: dict = {}
        self.path: Path | None = None

    def cargar(self) -> dict:
        import copy

        return copy.deepcopy(self._data)

    def guardar(self, datos: dict) -> dict:
        self._data = dict(datos)
        return self.cargar()

    def actualizar(self, mutator: Callable[[dict], dict]) -> dict:
        nuevo = mutator(self.cargar())
        return self.guardar(nuevo)


class OllamaMock:
    """Cliente Ollama simulado (plan §6.4).

    Configurable por test mediante atributos:
      - `disponible`: True/False (ping y generate).
      - `latencia`: segundos a "consumir" por llamada.
      - `responder(prompt)`: respuesta programable (por defecto fija).
    """

    def __init__(self, disponible: bool = True, latencia: float = 0.0) -> None:
        self.disponible = disponible
        self.latencia = latencia
        self.responder: Callable[[str], str] = self._respuesta_por_defecto
        self.ping_calls = 0
        self.prompts: list[str] = []

    def _respuesta_por_defecto(self, prompt: str) -> str:
        return "respuesta de prueba"

    def ping(self) -> bool:
        self.ping_calls += 1
        if self.latencia:
            time.sleep(self.latencia)
        return self.disponible

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if self.latencia:
            time.sleep(self.latencia)
        if not self.disponible:
            raise AssistantUnavailable("ASSISTANT_UNAVAILABLE", "El asistente no esta disponible (mock).")
        return self.responder(prompt)


@pytest.fixture()
def app() -> FastAPI:
    from app.main import app as app_principal

    return app_principal


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


@pytest.fixture()
def make_store() -> Callable[[], InMemoryStore]:
    creados: list[InMemoryStore] = []

    def _crear() -> InMemoryStore:
        store = InMemoryStore()
        creados.append(store)
        return store

    return _crear


@pytest.fixture()
def ollama_mock() -> OllamaMock:
    return OllamaMock()
