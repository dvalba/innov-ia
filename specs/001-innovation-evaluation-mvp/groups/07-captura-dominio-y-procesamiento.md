# Grupo 07 — Captura: dominio, store, inicio y procesamiento (backend)

**Vertical (parte 1 de la captura asistida):** el motor de la conversación — modelo y reglas
(orden fijo RF-3, chips fijos D7, clarificación, una conversación activa), `conversation_store`
(sin pérdida de campos parciales, RNF-10) e inicio/retoma + procesamiento de mensajes con
sugerencia de título.

## Estado

> ⬜ **Pendiente** — 0/5 tareas implementadas.

## Tareas (orden de ejecución)

- [ ] **T-025** _(BE)_ — `domain/conversation.py` (esquema §2.4: ACTIVA/RESUMEN/TERMINADA/CONTINGENCIA) + `capture_rules.py` (orden exacto RF-3, catálogo fijo de chips D7, chip = respuesta completa, `needsClarification` sin avanzar, 1 ACTIVA por usuario) _(T-007 ✓)_
- [ ] **T-026** _(BE)_ — `infrastructure/conversation_store.py` (JsonStore): obtener ACTIVA, crear, actualizar campos sin perder existentes, marcar CONTINGENCIA/TERMINADA; RNF-10 _(T-025, T-003 ✓)_
- [ ] **T-027** _(BE)_ — `start_conversation.py`: retoma ACTIVA (no crea segunda, caso 8); si IA disponible inicia con saludo + pregunta campo 1 + chips; si no, señal de formulario manual vacío _(T-026, T-008 ✓, cliente IA G04)_
- [ ] **T-028** _(BE)_ — `process_message.py`: aplica texto o chip al campo en curso; extractor IA asigna narrativa multi-campo (cada fragmento marca su campo, no se re-pregunta); aclaración si insuficiente; avanza al siguiente incompleto; al completar 7 → RESUMEN _(T-027)_
- [ ] **T-029** _(BE)_ — `suggest_title.py`: tras 1ª respuesta sustantiva propone título (`accept`/`another`/`manual`); "another" genera alternativa distinta (intentos persistentes); el texto manual se guarda sin modificar _(T-028)_

## Criterio de salida

* `pytest -q` verde con `tests/unit/domain/test_capture_rules.py` (orden, salto de capturados,
  aclaración, límite 1 ACTIVA), `tests/unit/infra/test_conversation_store.py` (RNF-10),
  `tests/unit/use_cases/test_capture_flow.py` (bloque inicio: retoma, inicio, contingencia al
  iniciar) y tests de `process_message` (narrativa multi-campo, chip, aclaración, salto) y de
  `suggest_title` (propuesta, alternativa distinta, manual).
* `ruff check .` limpio.

## Qué no se rompe

* Sin endpoint aún (el router llega en G08); solo domina la conversación en `domain`/
  `infrastructure`/`use_cases`.
* El extractor de IA se inyecta (G04); si no está disponible, `process_message` ofrece la vía
  manual (no rompiendo el chat).
* No toca `ideas`; la creación de la idea al finalizar usa `create_idea` (G06), que aquí aún no se
  invoca.
