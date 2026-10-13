"""Application settings: reads environment variables via the standard library (Constitution §6.1).

Precedence per variable (highest wins):
  1. the real process environment (`os.environ`),
  2. `backend/.env` when present (a minimal `KEY=VALUE` file: `#` comments, blank
     lines, optional quotes — no dependency),
  3. the built-in default.

The `.env` file keeps local deployment configuration (the Ollama address/model,
the admin seed, CORS) so the application runs on any machine without exporting
variables; the real environment (and the test `monkeypatch`/subprocess envs)
always wins over it.
"""

import os
import pathlib

# `backend/.env` resolved from this file (…/shared/config/settings.py → backend/).
_ENV_FILE = pathlib.Path(__file__).resolve().parents[2] / ".env"


def _read_env_file(path: pathlib.Path) -> dict[str, str]:
    """Parses a minimal `KEY=VALUE` `.env` file into a dict (stdlib only)."""
    values: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return values
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


_ENV_FILE_VALUES = _read_env_file(_ENV_FILE)


def _lookup(name: str) -> str | None:
    """The non-empty value of `name`: real environment first, then `.env`."""
    raw = os.environ.get(name)
    if raw is not None and raw.strip() != "":
        return raw
    file_raw = _ENV_FILE_VALUES.get(name)
    if file_raw is not None and file_raw.strip() != "":
        return file_raw
    return None


def _read_int(name: str, default: int) -> int:
    raw = _lookup(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _read_str(name: str, default: str) -> str:
    return _lookup(name) if _lookup(name) is not None else default


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
        self.data_dir = pathlib.Path(data_dir) if data_dir is not None else pathlib.Path(
            _read_str("INNOV_DATA_DIR", "data")
        )
        if cors_origins is not None:
            self.cors_origins = cors_origins
        else:
            raw = _read_str("CORS_ORIGINS", "")
            self.cors_origins = [o.strip() for o in raw.split(",") if o.strip()]
        self.session_ttl_minutes = session_ttl_minutes if session_ttl_minutes is not None else _read_int(
            "INNOV_SESSION_TTL_MINUTES", 480
        )
        self.admin_username = admin_username if admin_username is not None else _read_str("INNOV_ADMIN_USERNAME", "admin")
        # Optional: only used at first initialization (plan T-011). Unlike the
        # others it has no default — when unset the seed is a no-op.
        self.admin_password = admin_password if admin_password is not None else _lookup("INNOV_ADMIN_PASSWORD")


settings = Settings()
