"""Tests de la estructura base del backend (T-001)."""

import pathlib
import sys

FEATURES = ["auth", "capture", "ideas", "assistant", "validation", "users", "notifications"]
LAYERS = ["domain", "use_cases", "infrastructure", "routers"]

BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _ensure_backend_on_path() -> None:
    root = str(BACKEND_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


def test_estructura_de_directorios_existe() -> None:
    for feature in FEATURES:
        for layer in LAYERS:
            paquete = BACKEND_ROOT / "features" / feature / layer
            assert (paquete / "__init__.py").is_file(), f"Falta {paquete}/__init__.py"
    for paquete in [
        "app",
        "shared",
        "shared/config",
        "shared/exceptions",
        "shared/utils",
        "shared/contracts",
    ]:
        assert (BACKEND_ROOT / paquete / "__init__.py").is_file(), f"Falta {paquete}/__init__.py"


def test_app_instancia_fastapi_y_health() -> None:
    _ensure_backend_on_path()
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    respuesta = client.get("/health")
    assert respuesta.status_code == 200
    assert respuesta.json()["status"] == "ok"


def test_settings_lee_variables_de_entorno(monkeypatch) -> None:
    _ensure_backend_on_path()
    from shared.config.settings import Settings

    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama.interno:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "mistral")
    monkeypatch.setenv("OLLAMA_TIMEOUT", "45")
    settings = Settings()
    assert settings.ollama_base_url == "http://ollama.interno:11434"
    assert settings.ollama_model == "mistral"
    assert settings.ollama_timeout == 45


def test_settings_valores_por_defecto() -> None:
    _ensure_backend_on_path()
    from shared.config.settings import Settings

    settings = Settings()
    assert settings.ollama_timeout == 60
    assert settings.ollama_base_url.endswith(":11434")
    assert isinstance(settings.ollama_model, str) and settings.ollama_model
