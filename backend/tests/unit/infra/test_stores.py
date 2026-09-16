"""Tests de la persistencia JSON reutilizable (T-003, decision D1)."""

import json
import pathlib

import pytest

from shared.utils.persistence import JsonStore


@pytest.fixture()
def ruta(tmp_path: pathlib.Path) -> pathlib.Path:
    return tmp_path / "datos" / "entidad.json"


def test_round_trip(ruta: pathlib.Path) -> None:
    store = JsonStore(ruta)
    datos = {"usuario_1": {"nombre": "Ana", "roles": ["proponente"]}}
    store.guardar(datos)
    assert store.cargar() == datos
    assert json.loads(ruta.read_text(encoding="utf-8")) == datos


def test_cargar_archivo_inexistente_devuelve_vacio(ruta: pathlib.Path) -> None:
    assert JsonStore(ruta).cargar() == {}


def test_guardado_crea_directorios(ruta: pathlib.Path) -> None:
    JsonStore(ruta).guardar({"a": 1})
    assert ruta.parent.is_dir() and ruta.is_file()


def test_guardado_atomo_no_deja_registro_parcial(ruta: pathlib.Path, monkeypatch) -> None:
    store = JsonStore(ruta)
    store.guardar({"v": 1})

    def romper_reemplazo(origen: pathlib.Path, destino: pathlib.Path) -> Exception:
        raise OSError("fallo simulado al momento de reemplazar el archivo")

    monkeypatch.setattr("os.replace", romper_reemplazo)
    with pytest.raises(OSError):
        store.guardar({"v": 2})
    assert store.cargar() == {"v": 1}
    assert not (ruta.parent / (ruta.name + ".tmp")).exists()


def test_guardado_atomo_con_mutacion_inválida(ruta: pathlib.Path) -> None:
    store = JsonStore(ruta)
    store.guardar({"v": 1})

    def mutar_fallido(datos: dict) -> dict:
        raise ValueError("dato intermedio no valido")

    with pytest.raises(ValueError):
        store.actualizar(mutar_fallido)
    assert store.cargar() == {"v": 1}


def test_actualizar_acumula_cambios(ruta: pathlib.Path) -> None:
    store = JsonStore(ruta)
    store.guardar({"ids": []})
    resultado = store.actualizar(lambda datos: {**datos, "ids": datos["ids"] + ["x"]})
    assert resultado["ids"] == ["x"]
    assert store.cargar()["ids"] == ["x"]


def test_cargar_archivo_corrupto_devuelve_vacio(ruta: pathlib.Path) -> None:
    ruta.parent.mkdir(parents=True)
    ruta.write_text("{json roto", encoding="utf-8")
    assert JsonStore(ruta).cargar() == {}
