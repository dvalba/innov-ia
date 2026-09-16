"""Global exception handling and unified error format tests (T-002).

Note: error messages stay in Spanish (RNF-4, user-facing); identifiers and
codes are in English.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared.exceptions.handlers import (
    AssistantUnavailable,
    AuthError,
    DomainError,
    Forbidden,
    ValidationFailed,
    register_exception_handlers,
)


@pytest.fixture()
def client() -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom/domain")
    def boom_domain() -> None:
        raise DomainError(
            "TRANSITION_NOT_ALLOWED",
            "La transición solicitada no es válida para el estado vigente."
        )

    @app.get("/boom/domain-400")
    def boom_domain_400() -> None:
        raise DomainError("REJECT_WITHOUT_COMMENT", "El rechazo requiere un comentario.", status_code=400)

    @app.get("/boom/validation")
    def boom_validation() -> None:
        raise ValidationFailed("INCOMPLETE_FIELDS", "La idea se registró con campos vacíos u omitidos.")

    @app.get("/boom/auth")
    def boom_auth() -> None:
        raise AuthError(code="SESSION_REQUIRED", message="No existe una sesión activa.")

    @app.get("/boom/forbidden")
    def boom_forbidden() -> None:
        raise Forbidden(code="ROLE_NOT_ALLOWED", message="El rol actual no permite esta acción.")

    @app.get("/boom/assistant")
    def boom_assistant() -> None:
        raise AssistantUnavailable(
            "ASSISTANT_UNAVAILABLE",
            "El asistente de IA no está disponible.",
            fallback={"capturedFields": {"description": "texto capturado"}},
        )

    return TestClient(app)


def test_unified_error_format(client: TestClient) -> None:
    response = client.get("/boom/domain")
    assert response.status_code == 409
    body = response.json()
    assert set(body["error"].keys()) == {"code", "message", "details"}
    assert body["error"]["code"] == "TRANSITION_NOT_ALLOWED"
    assert isinstance(body["error"]["message"], str) and body["error"]["message"]
    assert isinstance(body["error"]["details"], dict)


def test_domain_error_supports_400(client: TestClient) -> None:
    response = client.get("/boom/domain-400")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "REJECT_WITHOUT_COMMENT"


def test_validation_failed_422(client: TestClient) -> None:
    response = client.get("/boom/validation")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INCOMPLETE_FIELDS"


def test_auth_error_401(client: TestClient) -> None:
    response = client.get("/boom/auth")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "SESSION_REQUIRED"


def test_forbidden_403(client: TestClient) -> None:
    response = client.get("/boom/forbidden")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ROLE_NOT_ALLOWED"


def test_assistant_unavailable_503_with_fallback(client: TestClient) -> None:
    response = client.get("/boom/assistant")
    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "ASSISTANT_UNAVAILABLE"
    assert body["fallback"] == {"capturedFields": {"description": "texto capturado"}}


def test_main_app_registers_handlers() -> None:
    from app.main import app

    for exc in (DomainError, ValidationFailed, AssistantUnavailable, AuthError, Forbidden):
        assert exc in app.exception_handlers
