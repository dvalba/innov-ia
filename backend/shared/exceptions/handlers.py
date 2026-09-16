"""Domain exceptions and global error handlers (T-002).

Unified response format (plan §3.6):
    {"error": {"code": str, "message": str, "details": dict}}

HTTP codes (plan §3.5):
    DomainError -> 409 (or 400 when the rule requires it)
    ValidationFailed -> 422
    AssistantUnavailable -> 503 (with extra fallback payload)
    AuthError -> 401
    Forbidden -> 403

User-facing messages are kept in Spanish (RNF-4, AGENTS.md).
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    """A business rule was violated (plan §3.7). Defaults to 409; 400 allowed."""

    def __init__(self, code: str, message: str, status_code: int = 409, details: dict | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class ValidationFailed(Exception):
    """Invalid data by schema or domain validation rule (422)."""

    def __init__(self, code: str, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


class AssistantUnavailable(Exception):
    """The AI assistant is down or does not respond within the limit (503).

    The fallback payload is added to the response to enable the pre-filled
    manual form (RF-7, RNF-10).
    """

    def __init__(self, code: str, message: str, fallback: dict | None = None, details: dict | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.fallback = fallback or {}
        self.details = details or {}


class AuthError(Exception):
    """Not authenticated or the session has expired (401)."""

    def __init__(self, code: str = "SESSION_REQUIRED", message: str = "No existe una sesión activa.",
                 details: dict | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


class Forbidden(Exception):
    """The session's role is not allowed to perform the action (403)."""

    def __init__(self, code: str = "ROLE_NOT_ALLOWED", message: str = "El rol actual no permite esta acción.",
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
    """Registers the global handlers on the FastAPI instance."""
    app.add_exception_handler(DomainError, _handle_domain_error)
    app.add_exception_handler(ValidationFailed, _handle_validation_failed)
    app.add_exception_handler(AssistantUnavailable, _handle_assistant_unavailable)
    app.add_exception_handler(AuthError, _handle_auth_error)
    app.add_exception_handler(Forbidden, _handle_forbidden)
