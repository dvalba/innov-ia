"""Base smoke tests (T-007): the application responds and the fixtures work."""

import pytest

from shared.exceptions.handlers import AssistantUnavailable


def test_smoke_health(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_fixture_make_store_roundtrip(make_store) -> None:
    store = make_store()
    store.save({"a": 1})
    updated = store.update(lambda data: {**data, "b": 2})
    assert updated == {"a": 1, "b": 2}
    assert store.load() == {"a": 1, "b": 2}


def test_fixture_ollama_mock_available_and_down(ollama_mock) -> None:
    assert ollama_mock.ping() is True
    assert ollama_mock.generate("hello") == "test response"

    ollama_mock.available = False
    assert ollama_mock.ping() is False
    with pytest.raises(AssistantUnavailable):
        ollama_mock.generate("hello")
