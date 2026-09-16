"""Persistencia JSON por ruta (T-003, decision D1 del plan).

Un archivo JSON por coleccion de registros. La escritura es atomica:
se escribe en un archivo temporal del mismo directorio y se reemplaza el
destino (`os.replace`), de manera que un fallo nunca deja un registro
parcial (spec §7, caso 17; RNF-9 para transiciones).
"""

import json
import os
import pathlib
from collections.abc import Callable


class JsonStore:
    """Almacena un dict `str -> registro (dict)` en un archivo JSON."""

    def __init__(self, path: str | pathlib.Path) -> None:
        self._path = pathlib.Path(path)

    @property
    def path(self) -> pathlib.Path:
        return self._path

    def cargar(self) -> dict:
        """Devuelve los registros persistidos; `{}` si no existe o esta corrupto."""
        try:
            with open(self._path, encoding="utf-8") as archivo:
                datos = json.load(archivo)
        except (OSError, json.JSONDecodeError):
            return {}
        return datos if isinstance(datos, dict) else {}

    def guardar(self, datos: dict) -> dict:
        """Sustituye la coleccion completa de forma atomica."""
        self._escribir_atomico(datos)
        return datos

    def actualizar(self, mutator: Callable[[dict], dict]) -> dict:
        """Lee, aplica `mutator` y persiste el resultado de forma atomica.

        Si `mutator` lanza, el archivo previo no se toca.
        """
        datos = self.cargar()
        nuevo = mutator(datos)
        self.guardar(nuevo)
        return nuevo

    def _escribir_atomico(self, datos: dict) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporal = self._path.with_name(self._path.name + ".tmp")
        try:
            with open(temporal, "w", encoding="utf-8") as archivo:
                json.dump(datos, archivo, ensure_ascii=False, indent=2)
                archivo.write("\n")
                archivo.flush()
                os.fsync(archivo.fileno())
            os.replace(temporal, self._path)
        except BaseException:
            if temporal.exists():
                temporal.unlink()
            raise
