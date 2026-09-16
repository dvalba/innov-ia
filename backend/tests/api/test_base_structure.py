"""Backend base structure tests (T-001)."""

import pathlib
import sys

FEATURES = ["auth", "capture", "ideas", "assistant", "validation", "users", "notifications"]
LAYERS = ["domain", "use_cases", "infrastructure", "routers"]

BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _ensure_backend_on_path() -> None:
    root = str(BACKEND_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


def test_directory_structure_exists() -> None:
    for feature in FEATURES:
        for layer in LAYERS:
            package = BACKEND_ROOT / "features" / feature / layer
            assert (package / "__init__.py").is_file(), f"Missing {package}/__init__.py"
    for package in [
        "app",
        "shared",
        "shared/config",
        "shared/exceptions",
        "shared/utils",
        "shared/contracts",
    ]:
        assert (BACKEND_ROOT / package / "__init__.py").is_file(), f"Missing {package}/__init__.py"


def test_app_fastapi_instance_and_health() -> None:
    _ensure_backend_on_path()
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_settings_reads_environment_variables(monkeypatch) -> None:
    _ensure_backend_on_path()
    from shared.config.settings import Settings

    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama.internal:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "mistral")
    monkeypatch.setenv("OLLAMA_TIMEOUT", "45")
    settings = Settings()
    assert settings.ollama_base_url == "http://ollama.internal:11434"
    assert settings.ollama_model == "mistral"
    assert settings.ollama_timeout == 45


def test_settings_default_values() -> None:
    _ensure_backend_on_path()
    from shared.config.settings import Settings

    settings = Settings()
    assert settings.ollama_timeout == 60
    assert settings.ollama_base_url.endswith(":11434")
    assert isinstance(settings.ollama_model, str) and settings.ollama_model
