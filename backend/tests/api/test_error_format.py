"""Tests del manejo global de excepciones y formato unificado de errores (T-002)."""

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
        raise DomainError("TRANSICION_NO_PERMITIDA", "La transicion solicitada no es valida para el estado vigente.")

    @app.get("/boom/domain-400")
    def boom_domain_400() -> None:
        raise DomainError("REJECT_WITHOUT_COMMENT", "El rechazo requiere un comentario.", status_code=400)

    @app.get("/boom/validation")
    def boom_validation() -> None:
        raise ValidationFailed("CAMPOS_INCOMPLETOS", "La idea se registro con campos vacios u omitidos.")

    @app.get("/boom/auth")
    def boom_auth() -> None:
        raise AuthError("SESION_REQUERIDA", "No existe una sesion activa.")

    @app.get("/boom/forbidden")
    def boom_forbidden() -> None:
        raise Forbidden("ROL_NO_PERMITIDO", "El rol actual no permite esta accion.")

    @app.get("/boom/assistant")
    def boom_assistant() -> None:
        raise AssistantUnavailable(
            "ASSISTANT_UNAVAILABLE",
            "El asistente de IA no esta disponible.",
            fallback={"capturedFields": {"description": "texto capturado"}},
        )

    return TestClient(app)


def test_formato_unificado_error(client: TestClient) -> None:
    respuesta = client.get("/boom/domain")
    assert respuesta.status_code == 409
    cuerpo = respuesta.json()
    assert set(cuerpo["error"].keys()) == {"code", "message", "details"}
    assert cuerpo["error"]["code"] == "TRANSICION_NO_PERMITIDA"
    assert isinstance(cuerpo["error"]["message"], str) and cuerpo["error"]["message"]
    assert isinstance(cuerpo["error"]["details"], dict)


def test_domain_error_admite_estado_400(client: TestClient) -> None:
    respuesta = client.get("/boom/domain-400")
    assert respuesta.status_code == 400
    assert respuesta.json()["error"]["code"] == "REJECT_WITHOUT_COMMENT"


def test_validation_failed_422(client: TestClient) -> None:
    respuesta = client.get("/boom/validation")
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["code"] == "CAMPOS_INCOMPLETOS"


def test_auth_error_401(client: TestClient) -> None:
    respuesta = client.get("/boom/auth")
    assert respuesta.status_code == 401
    assert respuesta.json()["error"]["code"] == "SESION_REQUERIDA"


def test_forbidden_403(client: TestClient) -> None:
    respuesta = client.get("/boom/forbidden")
    assert respuesta.status_code == 403
    assert respuesta.json()["error"]["code"] == "ROL_NO_PERMITIDO"


def test_assistant_unavailable_503_con_fallback(client: TestClient) -> None:
    respuesta = client.get("/boom/assistant")
    assert respuesta.status_code == 503
    cuerpo = respuesta.json()
    assert cuerpo["error"]["code"] == "ASSISTANT_UNAVAILABLE"
    assert cuerpo["fallback"] == {"capturedFields": {"description": "texto capturado"}}


def test_app_principal_registra_manejadores() -> None:
    from app.main import app

    for exc in (DomainError, ValidationFailed, AssistantUnavailable, AuthError, Forbidden):
        assert exc in app.exception_handlers

