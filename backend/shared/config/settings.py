"""Application settings: reads environment variables via the standard library (Constitution §6.1)."""

import os


def _read_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _read_str(name: str, default: str) -> str:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw


class Settings:
    """Typed configuration values.

    The no-argument constructor reads the environment (default: local Ollama).
    Any field can be explicitly overridden for tests and initialization.
    """

    def __init__(
        self,
        ollama_base_url: str | None = None,
        ollama_model: str | None = None,
        ollama_timeout: int | None = None,
        data_dir: str | None = None,
        cors_origins: list[str] | None = None,
        session_ttl_minutes: int | None = None,
        admin_username: str | None = None,
        admin_password: str | None = None,
    ) -> None:
        self.ollama_base_url = ollama_base_url if ollama_base_url is not None else _read_str(
            "OLLAMA_BASE_URL", "http://localhost:11434"
        )
        self.ollama_model = ollama_model if ollama_model is not None else _read_str(
            "OLLAMA_MODEL", "llama3.2"
        )
        self.ollama_timeout = ollama_timeout if ollama_timeout is not None else _read_int(
            "OLLAMA_TIMEOUT", 60
        )
        self.data_dir = data_dir if data_dir is not None else _read_str("INNOV_DATA_DIR", "data")
        if cors_origins is not None:
            self.cors_origins = cors_origins
        else:
            raw = os.environ.get("CORS_ORIGINS", "")
            self.cors_origins = [o.strip() for o in raw.split(",") if o.strip()]
        self.session_ttl_minutes = session_ttl_minutes if session_ttl_minutes is not None else _read_int(
            "INNOV_SESSION_TTL_MINUTES", 480
        )
        self.admin_username = admin_username if admin_username is not None else _read_str("INNOV_ADMIN_USERNAME", "admin")
        self.admin_password = admin_password  # optional: only used at first initialization (plan T-011)


settings = Settings()
