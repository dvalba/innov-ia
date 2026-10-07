"""FastAPI application entry point (T-001, T-002, T-015).

Registers the application instance, CORS and the global error handler.
On startup it seeds the first administrator from the environment (plan
§5 / RF-17, decision #6). Feature routers are registered as each one is
implemented (T-013, T-016, T-023, T-031, T-033, T-034, T-035, T-062).
"""

from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.deps import get_user_directory
from features.auth.infrastructure.token_store import seed_first_admin
from features.auth.routers.auth import auth_router
from features.capture.routers.capture import capture_router
from features.ideas.routers.catalog import catalog_router
from features.ideas.routers.ideas import ideas_router
from features.notifications.routers.notifications import notifications_router
from features.users.routers.users import users_router
from features.validation.routers.validation import validation_router
from shared.config.settings import settings
from shared.exceptions.handlers import register_exception_handlers


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Seeds the first administrator once, idempotently (RF-17, decision #6)."""
    with suppress(Exception):  # pragma: no cover - defensive: the app must still boot
        seed_first_admin(get_user_directory(), settings.admin_username, settings.admin_password)
    yield


app = FastAPI(
    title="Innov-IA",
    description="Plataforma de captura, estructuración y evaluación de iniciativas de innovación",
    version="0.1.0",
    lifespan=lifespan,
)

register_exception_handlers(app)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(ideas_router)
app.include_router(capture_router)
app.include_router(notifications_router)
app.include_router(validation_router)
app.include_router(catalog_router)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# Router registration (auth — T-013, ideas — T-023, capture — T-031,
# notifications/validation/catalog — T-033/T-034/T-035) completed above.
# Placeholder for the remaining feature (wired by its task):
#   features.assistant.routers.assistant.assistant_router  (T-062)
