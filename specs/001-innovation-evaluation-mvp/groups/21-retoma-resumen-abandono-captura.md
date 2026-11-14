# Grupo 21 — Corrección de captura v2.3: retoma RESUMEN y abandono explícito

**Vertical:** backend: `POST /capture/abandon` + retoma de la conversación en `RESUMEN` con su
resumen editable en `POST /capture/start` (prioridad ACTIVA → RESUMEN → nueva/manual) ↔
frontend: el inicio retoma la RESUMEN en la vista de resumen editable y el chat asistido expone
la acción **Abandonar captura** (confirmación + aviso de pérdida). Casos 7 y 8, RF-2/RF-6,
plan D22.

## Estado

> ✅ **Completado** — 2/2 tareas. Autorizado por el propietario del producto (corrección de
> alcance v2.3). Backend verificado: `pytest -q` 804 passed, `ruff check .` limpio; frontend
> `ng build` verde.

## Tareas (orden de ejecución)

- [x] **T-087** _(BE)_ — `POST /capture/abandon` + retoma RESUMEN: `ConversationStore.list_in_progress(user_id)` (ACTIVA/RESUMEN); `start_conversation.py` retoma primero la ACTIVA (contrato invariante) y, si no, la RESUMEN más reciente con `state: RESUMEN` + `summary` (resumen editable, los campos ya capturados no se pierden); use case `abandon_conversation.py` + endpoint `POST /capture/abandon` (conversationId opcional, por defecto la en curso): ACTIVA/RESUMEN/CONTINGENCIA → TERMINADA sin guardar nada (sin borradores, caso 7), idempotente, 404/403; tests unitarios + API (`test_abandon_closes_the_capture_without_saving`, `test_abandon_is_idempotent_and_handles_missing_or_foreign`, `test_start_after_summary_resumes_with_the_editable_summary`, prioridad ACTIVA sobre RESUMEN); `pytest -q` y `ruff check .` verdes
- [x] **T-088** _(FE)_ — Retoma RESUMEN + abandono: `capture.service.ts` extiende `StartResult` (`state`/`summary`) y añade `abandon()`; `new-idea.ts`/`chat-assist.ts` al recibir `state: RESUMEN` inicializan el resumen editable con los campos ya capturados (sin reiniciar la conversación); el chat asistido muestra **Abandonar captura** con confirmación y aviso de pérdida (se pierde todo lo capturado) que llama a `abandon()` y limpia el estado local; accesible (teclado/aria, RNF-6); `ng build` verde

## Criterio de salida

* Al volver a `POST /capture/start` con una conversación en RESUMEN, el proponente retoma la
  misma conversación y ve su resumen editable (los campos ya capturados no se pierden); si
  existe una ACTIVA, se retoma la ACTIVA (caso 8).
* El proponente puede abandonar la captura en cualquier momento (ACTIVA/RESUMEN/CONTINGENCIA)
  tras confirmar con el aviso de pérdida: la conversación termina sin guardar nada (sin
  borradores, caso 7) y el límite de una conversación a la vez queda liberado.

## Qué no se rompe

* El contrato de `POST /capture/start` para conversaciones nuevas/ACTIVA y para la contingencia
  manual (RF-7) se conserva: los nuevos campos (`state`/`summary`) son aditivos.
* `finish_capture` (RESUMEN → TERMINADA con idea registrada) y `activate_manual` (CONTINGENCIA)
  no cambian de comportamiento.
* `pytest -q` y `ruff check .` verdes tras el bloque backend; `ng build` verde tras el frontend.
