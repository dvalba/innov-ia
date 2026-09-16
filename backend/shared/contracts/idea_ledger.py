"""Contrato compartido de lectura/escritura de ideas (T-008).

Resuelve el acoplamiento entre features (plan §1.2, nota de acoplamiento):
las features `assistant` y `validation` consumen ideas SOLO a través de este
Protocolo, inyectado por la composición de dependencias; ninguna feature
importa de otra.

Los payloads son dicts con la forma de los esquemas JSON del plan §2
(`Idea` y `IdeaVersion`). El campo `campos` es el dict de los 7 campos de la
idea (esquema `Idea` §2.2).
"""

from collections.abc import Iterable
from typing import Protocol, runtime_checkable

# Los 7 campos de una idea (spec §1.1). El dict `campos` de un payload de idea
# contiene siempre estas claves.
CAMPOS_DE_LA_IDEA: tuple[str, ...] = (
    "title",
    "proponent",
    "description",
    "problem",
    "expectedBenefit",
    "strategicAlignment",
    "estimatedResources",
)

# Estados de la máquina (plan §4.6).
ESTADO_EN_DESARROLLO = "EN_DESARROLLO"
ESTADO_SOLICITANDO_PUBLICACION = "SOLICITANDO_PUBLICACION"
ESTADO_VALIDADA_PUBLICA = "VALIDADA_PUBLICA"

# Origenes de la idea (spec RF-2/RNF-2).
ORIGEN_ASISTIDA = "asistida"
ORIGEN_MANUAL = "manual"


@runtime_checkable
class IdeaLedger(Protocol):
    """Expediente de ideas compartido entre features.

    La implementación de referencia es `features.ideas.infrastructure.idea_store`
    (T-019). Las features `assistant` y `validation` solo dependen de este
    Protocolo.
    """

    def obtener(self, idea_id: str) -> dict | None:
        """Devuelve el payload completo de la idea por id, o `None` si no existe."""
        ...

    def listar_por_estado(self, estado: str, owner_id: str | None = None) -> Iterable[dict]:
        """Lista ideas en `estado`. Si `owner_id` se pasa, filtra por dueño (RF-19)."""
        ...

    def listar_por_origen(self, origen: str, estado: str, owner_id: str | None = None) -> Iterable[dict]:
        """Lista ideas con `origen` y `estado` (cola de refinamiento, RF-11)."""
        ...

    def guardar_campos_vigentes(self, idea_id: str, campos: dict) -> dict:
        """Aplica campos vigentes a la idea (aceptación de versión, RF-8/RF-13).

        Devuelve el payload actualizado. Lanza `DomainError` si la idea no existe.
        """
        ...

    def obtener_version(self, idea_id: str, version_id: str) -> dict | None:
        """Devuelve el payload de la versión `IdeaVersion` o `None`."""
        ...
