"""Reusable JSON persistence tests (T-003, decision D1)."""

import json
import pathlib

import pytest

from shared.utils.persistence import JsonStore


@pytest.fixture()
def store_path(tmp_path: pathlib.Path) -> pathlib.Path:
    return tmp_path / "data" / "entity.json"


def test_round_trip(store_path: pathlib.Path) -> None:
    store = JsonStore(store_path)
    data = {"user_1": {"name": "Ana", "roles": ["proponent"]}}
    store.save(data)
    assert store.load() == data
    assert json.loads(store_path.read_text(encoding="utf-8")) == data


def test_load_missing_file_returns_empty(store_path: pathlib.Path) -> None:
    assert JsonStore(store_path).load() == {}


def test_save_creates_directories(store_path: pathlib.Path) -> None:
    JsonStore(store_path).save({"a": 1})
    assert store_path.parent.is_dir() and store_path.is_file()


def test_atomic_save_leaves_no_partial_record(store_path: pathlib.Path, monkeypatch) -> None:
    store = JsonStore(store_path)
    store.save({"v": 1})

    def broken_replace(source: pathlib.Path, destination: pathlib.Path) -> Exception:
        raise OSError("simulated failure while replacing the file")

    monkeypatch.setattr("os.replace", broken_replace)
    with pytest.raises(OSError):
        store.save({"v": 2})
    assert store.load() == {"v": 1}
    assert not (store_path.parent / (store_path.name + ".tmp")).exists()


def test_atomic_save_with_invalid_mutation(store_path: pathlib.Path) -> None:
    store = JsonStore(store_path)
    store.save({"v": 1})

    def failing_mutator(data: dict) -> dict:
        raise ValueError("invalid intermediate data")

    with pytest.raises(ValueError):
        store.update(failing_mutator)
    assert store.load() == {"v": 1}


def test_update_accumulates_changes(store_path: pathlib.Path) -> None:
    store = JsonStore(store_path)
    store.save({"ids": []})
    result = store.update(lambda data: {**data, "ids": data["ids"] + ["x"]})
    assert result["ids"] == ["x"]
    assert store.load()["ids"] == ["x"]


def test_load_corrupt_file_returns_empty(store_path: pathlib.Path) -> None:
    store_path.parent.mkdir(parents=True)
    store_path.write_text("{broken json", encoding="utf-8")
    assert JsonStore(store_path).load() == {}
