"""Punto de entrada de la aplicacion FastAPI (T-001, T-002).

Registra la instancia de la aplicacion, CORS y el manejador global de errores.
Los routers de cada feature se registran a medida que se implementan
(T-013, T-016, T-023, T-031, T-033, T-034, T-035, T-062).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.config.settings import settings
from shared.exceptions.handlers import register_exception_handlers

app = FastAPI(
    title="Innov-IA",
    description="Plataforma de captura, estructuracion y evaluacion de iniciativas de innovacion",
    version="0.1.0",
)

register_exception_handlers(app)

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


# Huecos de registro de routers (se completan en sus respectivas tareas):
#   features.auth.routers.auth.auth_router                 (T-013)
#   features.users.routers.users.users_router              (T-016)
#   features.ideas.routers.ideas.ideas_router              (T-023)
#   features.capture.routers.capture.capture_router        (T-031)
#   features.notifications.routers.notifications.notif_router (T-033)
#   features.validation.routers.validation.validation_router (T-034)
#   features.ideas.routers.catalog.catalog_router          (T-035)
#   features.assistant.routers.assistant.assistant_router  (T-062)
