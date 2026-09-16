# Grupo 05 — Idea: dominio, máquina de estados y persistencia (backend)

**Vertical (parte 1 de la entidad central):** el dominio completo de `Idea` — entidad con sus 7
campos, validación, la máquina de estados del plan §4.6 y la persistencia JSON con `IdeaVersion`
(vía el contrato `IdeaLedger` de T-008). Es cimiento de todo lo posterior de ideas/captura/
validación.

## Tareas (orden de ejecución)

| # | ID | Capa | Tarea | Dependencias |
|---|------|------|-------|--------------|
| 1 | T-017 | BE | `domain/idea.py`: `Idea` (7 campos, `ownerId`, `origin`, `state`, `reviewedByAI`, `currentVersionId`, timestamps) + `validate.py` (`campos_completos`, formato de contacto, caso 12) | T-007 ✓ |
| 2 | T-018 | BE | `domain/state_machine.py`: tabla de transiciones exacta §4.6 (EN_DESARROLLO→SOLICITANDO solo por request-publication; SOLICITANDO→VALIDADA por approve; SOLICITANDO→EN_DESARROLLO por reject; VALIDADA terminal); `DomainError` ante transición inválida | T-017 |
| 3 | T-019 | BE | `infrastructure/idea_store.py`: persiste `Idea` + `IdeaVersion` con `JsonStore`, sin registro parcial (caso 17), expone operaciones vía `IdeaLedger` (T-008 ✓) | T-018, T-003 ✓ |

## Criterio de salida

* `pytest -q` verde con `tests/unit/domain/test_idea_validation.py` (completos/parciales,
  contacto inválido caso 12), `tests/unit/domain/test_state_machine.py` (todas las transiciones
  válidas y cada inválida) y `tests/unit/infra/test_idea_store.py` (guardado, carga, listado por
  estado, fallo sin registro parcial).
* `ruff check .` limpio.

## Qué no se rompe

* Reutiliza `JsonStore` (T-003) y el Protocolo `IdeaLedger` (T-008) sin modificarlos.
* Capas `domain` sin FastAPI/Pydantic (Constitución: dominio puro), `infrastructure` solo persiste.
