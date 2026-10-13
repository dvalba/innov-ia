"""Native Ollama client over the standard library (T-059, plan D2).

Implements the interface consumed by the assistant use cases (mirrored by
`tests.conftest.OllamaMock` in tests):
  - `ping() -> bool`: availability probe with one transparent retry
    (RNF-3, case 3).
  - `generate(prompt) -> str`: one call to `/api/generate`; on timeout,
    service error or empty/uninterpretable reply, one transparent retry and,
    if the second attempt also fails, `AssistantUnavailable` ("fallo de IA",
    spec case 14: no reply within the limit, service error, or an
    uninterpretable response).

No third-party dependencies (Constitution §6.1): only `urllib`.
"""

import json
import urllib.error
import urllib.request
from typing import Any

from shared.exceptions.handlers import AssistantUnavailable


class _TransientOllamaError(Exception):
    """Internal: a single attempt failed in a retryable way."""


class OllamaClient:
    """Client for a local Ollama service (plan D2).

    `timeout` is the per-attempt limit in seconds (default 60, RNF-3). Every
    public method performs exactly one attempt plus one transparent retry;
    the retry is never observed by the caller (case 3).
    """

    def __init__(self, base_url: str, model: str, timeout: float = 60.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self.model = model

    def ping(self) -> bool:
        """Probes availability (`GET /api/tags`). `False` after the retry fails."""
        for _attempt in range(2):
            try:
                self._request("GET", "/api/tags", body=None)
                return True
            except _TransientOllamaError:
                continue
        return False

    def generate(self, prompt: str) -> str:
        """Generates a response; raises `AssistantUnavailable` after the retry.

        The reply is the `response` field of the `/api/generate` payload. An
        empty or missing field is treated as an uninterpretable reply (case 14)
        and also retried once.
        """
        last_error: Exception | None = None
        for _attempt in range(2):
            try:
                data = self._request(
                    "POST",
                    "/api/generate",
                    body={
                        "model": self._model,
                        "prompt": prompt,
                        "stream": False,
                        # The assistant always parses JSON from the reply, so
                        # thinking models are asked to skip their reasoning
                        # preamble (Ollama `think` flag; ignored by models that
                        # do not think) keeping the response deterministic JSON.
                        "think": False,
                    },
                )
                text = data.get("response")
                if isinstance(text, str) and text.strip():
                    return text
                last_error = _TransientOllamaError("respuesta vacía o no interpretable")
            except _TransientOllamaError as exc:
                last_error = exc
        raise AssistantUnavailable(
            code="ASSISTANT_UNAVAILABLE",
            message="El asistente de IA no está disponible o no respondió a tiempo.",
            details={"cause": str(last_error)},
        )

    def _request(self, method: str, path: str, body: dict[str, Any] | None) -> dict:
        url = self._base_url + path
        payload: bytes | None = None
        headers: dict[str, str] = {}
        if body is not None:
            payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=payload, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            raise _TransientOllamaError(f"error HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise _TransientOllamaError(f"error de red: {exc.reason}") from exc
        except (TimeoutError, OSError) as exc:
            raise _TransientOllamaError(f"sin respuesta dentro del límite: {exc}") from exc
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise _TransientOllamaError("respuesta del servicio no interpretable") from exc
        if not isinstance(parsed, dict):
            raise _TransientOllamaError("respuesta del servicio no interpretable")
        return parsed
