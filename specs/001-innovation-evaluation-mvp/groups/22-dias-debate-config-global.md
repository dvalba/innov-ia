# Grupo 22 — Ampliación v2.4: días de debate como configuración global

**Vertical:** backend: registro único `debateDays` (entero 1–90, defecto 30, auditado) con
`GET/PUT /admin/debate-days` + `open_debate` fija `deadline = publishedAt + debateDays` al abrir
(sin recomputación; los debates existentes conservan su fecha) + retirada de `PUT
/admin/ideas/{ideaId}/debate/deadline`, `adjust_deadline` y `Debate.adjustments` ↔
frontend: pestaña **Días de debate** en `/admin` (espejo de Umbrales) + retirada del control
inline de ajuste de fecha límite del panel de debate. RF-24, RNF-11, plan D23.

## Estado

> ✅ **Completado** — 2/2 tareas. Autorizado por el propietario del producto (ampliación de
> alcance v2.4). Verificado: `pytest -q` verde (828), `ruff check .` limpio, `ng build` verde.

## Tareas (orden de ejecución)

- [x] **T-089** _(BE)_ — Días de debate globales: reglas puras en `debate/domain/debate_rules.py` (defecto 30, 1–90, booleanos rechazados → 422), registro único `debate/infrastructure/debate_days_store.py` (JSON, patrón `threshold_store`), use case `debate/use_cases/debate_days.py` (GET → registro o defecto; PUT valida + audit `updatedBy`/`updatedAt`), router `debate/routers/admin.py` con `GET/PUT /admin/debate-days` (admin: 403/401; 422 `DEBATE_DAYS_INVALID`); `open_debate` con `DebateDaysStoreDep` (wiring en `app/deps.py`, sin imports cruzados) fija el deadline con el valor vigente; retirada de `adjust_deadline.py`, del endpoint por idea, de `DebateDeadlineRequest` y de `adjustments`/`deadlineHistory` (`from_payload` tolera el legacy, migración silenciosa); tests unitarios (`test_debate_rules.py`: 1–90, defecto, booleanos, deadline fijo) y API (`test_debate_days_api.py`: GET defecto, PUT auditado, 422/403/401) + `test_debate_api.py` actualizado (apertura con 40 días → `deadline = publishedAt + 40d`); `pytest -q` y `ruff check .` verdes
- [x] **T-090** _(FE)_ — Sección **Días de debate** en `/admin`: `debate-days.service.ts` (espejo de `umbrales.service.ts`), página con input de entero (carga `GET /admin/debate-days`, defecto 30, validación 1–90, aviso ante 422) + nota de que solo afecta a debates nuevos; tab en `admin.html` + ruta child lazy en `app.routes.ts`; retirada del control inline de ajuste de fecha límite en `debate-panel`, de `ajustarFechaLimite` en `catalog.service.ts` y de `AjusteFechaLimite`/`Debate.deadlineHistory` en `shared/types/models.ts` (la fecha límite queda en solo lectura); accesible (teclado/aria, RNF-6); `ng build` verde

## Criterio de salida

* `GET /admin/debate-days` devuelve el valor vigente (defecto 30 si nunca se guardó) y
  `PUT /admin/debate-days` lo actualiza (entero 1–90; 422 si no; auditado quién/cuándo, RNF-11)
  solo para rol admin (403/401).
* Al publicarse una idea, el debate se abre con `deadline = publishedAt + debateDays` del valor
  vigente; cambiar la configuración **no** modifica el deadline de debates ya abiertos/cerrados.
* No existe forma alguna (API ni UI) de ajustar la fecha límite de un debate individual.

## Qué no se rompe

* `POST /validation/{id}/approve` y el resto del flujo de publicación no cambian: solo el
  origen de los días (valor global en vez del defecto 30).
* El cierre automático (primera lectura tras el deadline), el `@asistant`, el resumen al cierre
  y la generación de la evaluación al cerrarse el debate (RF-24/RF-25/RF-26) se conservan.
* `GET /catalog/{ideaId}/debate` sigue devolviendo mensajes + deadline + cerrado + resumen; solo
  deja de exponer el rastro de ajustes.
* Los debates ya persistidos con su deadline no se tocan (sin migración de datos).
