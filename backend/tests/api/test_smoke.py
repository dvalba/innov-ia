"""Test smoke de base (T-007): la aplicacion responde y las fixtures funcionan."""

import pytest

from shared.exceptions.handlers import AssistantUnavailable


def test_smoke_health(client) -> None:
    respuesta = client.get("/health")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "ok"}


def test_fixture_make_store_roundtrip(make_store) -> None:
    store = make_store()
    store.guardar({"a": 1})
    mutado = store.actualizar(lambda datos: {**datos, "b": 2})
    assert mutado == {"a": 1, "b": 2}
    assert store.cargar() == {"a": 1, "b": 2}


def test_fixture_ollama_mock_disponible_y_caido(ollama_mock) -> None:
    assert ollama_mock.ping() is True
    assert ollama_mock.generate("hola") == "respuesta de prueba"

    ollama_mock.disponible = False
    assert ollama_mock.ping() is False
    with pytest.raises(AssistantUnavailable):
        ollama_mock.generate("hola")
