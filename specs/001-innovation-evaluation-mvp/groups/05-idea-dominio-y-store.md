# Grupo 05 — Idea: dominio, máquina de estados y persistencia (backend)

**Vertical (parte 1 de la entidad central):** el dominio completo de `Idea` — entidad con sus 7
campos, validación, la máquina de estados del plan §4.6 y la persistencia JSON con `IdeaVersion`
(vía el contrato `IdeaLedger` de T-008). Es cimiento de todo lo posterior de ideas/captura/
validación.

## Estado

> ✅ **Completado** — 3/3 tareas implementadas y verificadas (2026-09-23).

## Tareas (orden de ejecución)

- [x] **T-017** _(BE)_ — `domain/idea.py`: `Idea` (7 campos, `ownerId`, `origin`, `state`, `reviewedByAI`, `currentVersionId`, timestamps) + `validate.py` (`campos_completos`, formato de contacto, caso 12) _(T-007 ✓)_
- [x] **T-018** _(BE)_ — `domain/state_machine.py`: tabla de transiciones exacta §4.6 (EN_DESARROLLO→SOLICITANDO solo por request-publication; SOLICITANDO→VALIDADA por approve; SOLICITANDO→EN_DESARROLLO por reject; VALIDADA terminal); `DomainError` ante transición inválida _(T-017)_
- [x] **T-019** _(BE)_ — `infrastructure/idea_store.py`: persiste `Idea` + `IdeaVersion` con `JsonStore`, sin registro parcial (caso 17), expone operaciones vía `IdeaLedger` (T-008 ✓) _(T-018, T-003 ✓)_

## Criterio de salida

* `pytest -q` verde con `tests/unit/domain/test_idea_validation.py` (completos/parciales,
  contacto inválido caso 12), `tests/unit/domain/test_state_machine.py` (todas las transiciones
  válidas y cada inválida) y `tests/unit/infra/test_idea_store.py` (guardado, carga, listado por
  estado, fallo sin registro parcial).
* `ruff check .` limpio.

## Qué no se rompe

* Reutiliza `JsonStore` (T-003) y el Protocolo `IdeaLedger` (T-008) sin modificarlos.
* Capas `domain` sin FastAPI/Pydantic (Constitución: dominio puro), `infrastructure` solo persiste.

## Registro de verificación (G05, 2026-09-23)

**Automatizado** — `pytest -q` en `backend/`: 196 passed; `ruff check .` limpio. Uno por
tarea (commits separados):

| Tarea | Verificación | Resultado |
|---|---|---|
| T-017 | `Idea` (7 campos + `ownerId`/`origin`/`state`/`reviewedByAI`/`currentVersionId` + rastro, esquema §2.2 camelCase sin pérdida); `validate.py`: no-vacío por campo (RNF-5), sub-partes de `proponent`/`estimatedResources`, contacto correo/teléfono (caso 12) | ✅ 27 tests `test_idea_validation.py` |
| T-018 | Tabla §4.6 exacta (parametrizada por estado×acción); `DomainError` 409 ante inválida (RNF-9, caso 11); rastro approve (quién/cuándo, autovalidación caso 9); rechazo exige comentario (400, caso 13) y adjunta `rejectionNote` con identidad (RNF-8) | ✅ `test_state_machine.py` |
| T-019 | `IdeaStore` = `IdeaLedger` de referencia; guardado/carga entre instancias; listado por estado/origen/propietario (RF-19, cola RF-11, RF-14); CAS por estado (el retardo se descarta, nada de intermedio); fallo simulado de `os.replace` → sin registro parcial (caso 17); versiones §2.5 numeradas, decisión única aceptar (vigente + rastro + idea sigue en su estado, decisión #1) / descartar | ✅ 22 tests `test_idea_store.py` |
