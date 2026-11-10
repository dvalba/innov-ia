"""FastAPI application entry point (T-001, T-002, T-015).

Registers the application instance, CORS and the global error handler.
On startup it seeds the first administrator from the environment (plan
§5 / RF-17, decision #6). Feature routers are registered as each one is
implemented (T-013, T-016, T-023, T-031, T-033, T-034, T-035, T-062).
"""

from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.deps import get_org_store, get_user_directory
from features.assistant.routers.assistant import assistant_router
from features.auth.infrastructure.token_store import seed_first_admin
from features.auth.routers.auth import auth_router
from features.capture.routers.capture import capture_router
from features.debate.routers.debate import debate_router
from features.ideas.routers.catalog import catalog_router
from features.ideas.routers.ideas import ideas_router
from features.notifications.routers.notifications import notifications_router
from features.org.routers.org import org_router
from features.users.routers.users import users_router
from features.validation.routers.admin import admin_thresholds_router
from features.validation.routers.validation import validation_router
from shared.config.settings import settings
from shared.exceptions.handlers import register_exception_handlers


def _seed_org_profile() -> None:
    """Seeds the company-context document once, idempotently (D7 replacement).

    The `INNOV_ORG_*` values (v2.0 compatibility) become the `profile` section
    of the single document; the guide text starts empty. When the administrator
    did not provide them the context starts empty and is completed through the
    panel (RF-21).
    """
    store = get_org_store()
    if store.has():
        return
    if not settings.org_name:
        return
    store.seed({
        "profile": {
            "name": settings.org_name,
            "sector": settings.org_sector,
            "description": settings.org_description,
            "mission": settings.org_mission,
            "strategicObjectives": list(settings.org_objectives),
        },
        "guideText": "",
        "updatedAt": "",
    })


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Seeds the first administrator and the organization profile once,
    idempotently (RF-17 decision #6 / D7 replacement)."""
    with suppress(Exception):  # pragma: no cover - defensive: the app must still boot
        seed_first_admin(get_user_directory(), settings.admin_username, settings.admin_password)
        _seed_org_profile()
    yield


app = FastAPI(
    title="Innov-IA",
    description="Plataforma de captura, estructuración y evaluación de iniciativas de innovación",
    version="0.1.0",
    lifespan=lifespan,
)

register_exception_handlers(app)

app.include_router(auth_router)
app.include_router(assistant_router)
app.include_router(users_router)
app.include_router(ideas_router)
app.include_router(capture_router)
app.include_router(notifications_router)
app.include_router(validation_router)
app.include_router(catalog_router)
app.include_router(debate_router)
app.include_router(org_router)
app.include_router(admin_thresholds_router)

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


# Router registration completed above: auth (T-013), assistant (T-062),
# users, ideas (T-023), capture (T-031), notifications/validation/catalog
# (T-033/T-034/T-035).
