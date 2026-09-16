"""JSON persistence per file path (T-003, plan decision D1).

One JSON file per collection of records. Writes are atomic: a temporary
file in the same directory is written and then swapped into the target
(`os.replace`), so a failure never leaves a partial record (spec §7, case 17;
RNF-9 for transitions).
"""

import json
import os
import pathlib
from collections.abc import Callable


class JsonStore:
    """Stores a `str -> record (dict)` mapping in a JSON file."""

    def __init__(self, path: str | pathlib.Path) -> None:
        self._path = pathlib.Path(path)

    @property
    def path(self) -> pathlib.Path:
        return self._path

    def load(self) -> dict:
        """Returns persisted records; `{}` if the file is missing or corrupt."""
        try:
            with open(self._path, encoding="utf-8") as file_handle:
                data = json.load(file_handle)
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def save(self, data: dict) -> dict:
        """Atomically replaces the whole collection."""
        self._write_atomic(data)
        return data

    def update(self, mutator: Callable[[dict], dict]) -> dict:
        """Loads, applies `mutator` and atomically persists the result.

        If `mutator` raises, the previous file is left untouched.
        """
        data = self.load()
        new_data = mutator(data)
        self.save(new_data)
        return new_data

    def _write_atomic(self, data: dict) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = self._path.with_name(self._path.name + ".tmp")
        try:
            with open(tmp_file, "w", encoding="utf-8") as file_handle:
                json.dump(data, file_handle, ensure_ascii=False, indent=2)
                file_handle.write("\n")
                file_handle.flush()
                os.fsync(file_handle.fileno())
            os.replace(tmp_file, self._path)
        except BaseException:
            if tmp_file.exists():
                tmp_file.unlink()
            raise
