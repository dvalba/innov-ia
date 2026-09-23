"""Ollama client tests over a simulated HTTP server (T-059, plan §6.3).

Covers: ping OK; timeout with exactly one transparent retry; service error
leading to contingency; and the uninterpretable-reply case (case 14).
"""

import json
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

from features.assistant.infrastructure.ollama_client import OllamaClient
from shared.exceptions.handlers import AssistantUnavailable


class _Handler(BaseHTTPRequestHandler):
    behavior: Callable[[str, bytes | None], tuple[int, dict | None]] = staticmethod(
        lambda path, body: (200, {"ok": True})
    )

    def _respond(self, code: int, payload: dict | None) -> None:
        raw = b"" if payload is None else json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        code, payload = type(self).behavior(self.path, None)
        self._respond(code, payload)

    def do_POST(self) -> None:  # noqa: N802 (http.server API)
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else None
        code, payload = type(self).behavior(self.path, body)
        self._respond(code, payload)

    def log_message(self, *args: Any) -> None:
        return


@pytest.fixture()
def server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    port = httpd.server_address[1]
    yield f"http://127.0.0.1:{port}"
    httpd.shutdown()
    httpd.server_close()


def test_ping_ok_and_tags_shape(server: str) -> None:
    _Handler.behavior = staticmethod(lambda path, body: (200, {"models": []}))
    client = OllamaClient(server, "test-model", timeout=2)
    assert client.ping() is True


def test_generate_returns_response_field(server: str) -> None:
    def behavior(path: str, body: bytes | None):
        if path != "/api/generate":
            return 200, {"models": []}
        assert json.loads(body)["model"] == "test-model"
        return 200, {"response": "Hola, título propuesto"}

    _Handler.behavior = staticmethod(behavior)
    client = OllamaClient(server, "test-model", timeout=2)
    assert client.generate("hola") == "Hola, título propuesto"


def test_ping_down_returns_false_after_single_retry(server: str) -> None:
    calls = {"n": 0}

    def behavior(_path: str, body: bytes | None):
        calls["n"] += 1
        return 500, None

    _Handler.behavior = staticmethod(behavior)
    client = OllamaClient(server, "test-model", timeout=2)
    assert client.ping() is False
    assert calls["n"] == 2  # one attempt plus exactly one retry


def test_timeout_retries_once_then_raises_contingency(server: str) -> None:
    calls = {"n": 0}

    def behavior(path: str, _body: bytes | None):
        if path == "/api/generate":
            calls["n"] += 1
            import time

            time.sleep(1.5)
            return 200, {"response": "tarde de más"}
        return 200, {"models": []}

    _Handler.behavior = staticmethod(behavior)
    client = OllamaClient(server, "test-model", timeout=0.3)
    with pytest.raises(AssistantUnavailable) as excinfo:
        client.generate("hola")
    assert excinfo.value.code == "ASSISTANT_UNAVAILABLE"
    assert calls["n"] == 2  # the single transparent retry is exhausted before failing


def test_service_error_leads_to_contingency(server: str) -> None:
    calls = {"n": 0}

    def behavior(_path: str, _body: bytes | None):
        calls["n"] += 1
        return 502, None

    _Handler.behavior = staticmethod(behavior)
    client = OllamaClient(server, "test-model", timeout=2)
    with pytest.raises(AssistantUnavailable) as excinfo:
        client.generate("hola")
    assert excinfo.value.code == "ASSISTANT_UNAVAILABLE"
    assert calls["n"] == 2


def test_uninterpretable_reply_is_a_failure(server: str) -> None:
    def behavior(_path: str, _body: bytes | None):
        return 200, {"response": ""}

    _Handler.behavior = staticmethod(behavior)
    client = OllamaClient(server, "test-model", timeout=2)
    with pytest.raises(AssistantUnavailable):
        client.generate("hola")


def test_unreachable_service_is_contingency() -> None:
    # Nothing listens on this port: the connection fails immediately.
    client = OllamaClient("http://127.0.0.1:1", "test-model", timeout=0.5)
    assert client.ping() is False
    with pytest.raises(AssistantUnavailable):
        client.generate("hola")
