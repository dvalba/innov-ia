"""Excepciones de dominio y manejadores globales de errores (T-002).

Formato unificado de respuesta (plan §3.6):
    {"error": {"code": str, "message": str, "details": dict}}

Codigos HTTP (plan §3.5):
    DomainError -> 409 (o 400 cuando la regla lo exige)
    ValidationFailed -> 422
    AssistantUnavailable -> 503 (con payload de contingencia extra)
    AuthError -> 401
    Forbidden -> 403
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    """Regla de negocio violada (plan §3.7). Por defecto 409; admite 400."""

    def __init__(self, code: str, message: str, status_code: int = 409, details: dict | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class ValidationFailed(Exception):
    """Dato invalido por esquema o regla de validacion de dominio (422)."""

    def __init__(self, code: str, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


class AssistantUnavailable(Exception):
    """El asistente de IA ha caido o no responde dentro del limite (503).

    El payload de contingencia (`fallback`) se anade a la respuesta para
    habilitar el formulario manual prellenado (RF-7, RNF-10).
    """

    def __init__(self, code: str, message: str, fallback: dict | None = None, details: dict | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.fallback = fallback or {}
        self.details = details or {}


class AuthError(Exception):
    """No autenticado o sesion caducada (401)."""

    def __init__(self, code: str = "SESION_REQUERIDA", message: str = "No existe una sesion activa.",
                 details: dict | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


class Forbidden(Exception):
    """El rol de la sesion no permite la accion (403)."""

    def __init__(self, code: str = "ROL_NO_PERMITIDO", message: str = "El rol actual no permite esta accion.",
                 details: dict | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def _error_payload(code: str, message: str, details: dict, extra: dict | None = None) -> dict:
    body: dict = {"error": {"code": code, "message": message, "details": details}}
    if extra:
        body.update(extra)
    return body


async def _handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code,
                        content=_error_payload(exc.code, exc.message, exc.details))


async def _handle_validation_failed(request: Request, exc: ValidationFailed) -> JSONResponse:
    return JSONResponse(status_code=422,
                        content=_error_payload(exc.code, exc.message, exc.details))


async def _handle_assistant_unavailable(request: Request, exc: AssistantUnavailable) -> JSONResponse:
    return JSONResponse(status_code=503,
                        content=_error_payload(exc.code, exc.message, exc.details,
                                               extra={"fallback": exc.fallback}))


async def _handle_auth_error(request: Request, exc: AuthError) -> JSONResponse:
    return JSONResponse(status_code=401, content=_error_payload(exc.code, exc.message, exc.details))


async def _handle_forbidden(request: Request, exc: Forbidden) -> JSONResponse:
    return JSONResponse(status_code=403, content=_error_payload(exc.code, exc.message, exc.details))


def register_exception_handlers(app: FastAPI) -> None:
    """Registra los manejadores globales sobre la instancia de FastAPI."""
    app.add_exception_handler(DomainError, _handle_domain_error)
    app.add_exception_handler(ValidationFailed, _handle_validation_failed)
    app.add_exception_handler(AssistantUnavailable, _handle_assistant_unavailable)
    app.add_exception_handler(AuthError, _handle_auth_error)
    app.add_exception_handler(Forbidden, _handle_forbidden)
