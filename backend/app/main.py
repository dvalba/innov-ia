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


# Router registration (auth — T-013) completed above. Placeholders for the
# remaining features (wired by their respective tasks):
#   features.users.routers.users.users_router              (T-016)
#   features.ideas.routers.ideas.ideas_router              (T-023)
#   features.capture.routers.capture.capture_router        (T-031)
#   features.notifications.routers.notifications.notif_router (T-033)
#   features.validation.routers.validation.validation_router (T-034)
#   features.ideas.routers.catalog.catalog_router          (T-035)
#   features.assistant.routers.assistant.assistant_router  (T-062)
