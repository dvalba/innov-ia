# Grupo 08 — Captura: finalización, router `/capture` y UI de arranque

**Vertical:** remata la captura en backend (finalización a idea asistida + activación manual
prefinada) y expone el router `/capture`; en frontend construye la base de captura (`fieldsMeta`
+ `CaptureService`) y decide en `new-idea` entre asistida vs manual (con retoma de conversación).

## Tareas (orden de ejecución)

| # | ID | Capa | Tarea | Dependencias |
|---|------|------|-------|--------------|
| 1 | T-030 | BE | `finish_capture.py` (valida 7 completos RNF-5 desde el resumen confirmado → idea EN_DESARROLLO origen `asistida`, termina conversación; sin confirmar no queda nada, caso 7) + `activate_manual.py` (marca CONTINGENCIA y devuelve `capturedFields` para prellenar sin pérdida) | T-029 (G07), T-020 (G06) |
| 2 | T-031 | BE | `routers/capture.py`: `POST /capture/start`, `POST /capture/messages` (200; 503 `{code: ASSISTANT_UNAVAILABLE, fallback:{capturedFields}}` si la IA cae a mitad), `POST /capture/finish` (201), `POST /capture/activate-manual`, `GET /capture/assistant-status`; rol proponente | T-030, T-013 ✓ |
| 3 | T-040 | FE | `fieldsMeta.ts` (orden fijo de los 7, pregunta ES por campo, chips fijos en espejo de D7) + `CaptureService` (`/capture/start`, `/capture/messages`, `/assistant-status` con carga visible, RNF-3) | T-009 (G01), T-031 |
| 4 | T-041 | FE | `pages/new-idea`: consulta `assistant-status` → OK abre asistida; UNAVAILABLE desplega manual con aviso (caso 1); si hay ACTIVA ofrece "Retomar conversación" (caso 8) | T-040 |
| 5 | T-042 | FE | `chat-assist`: burbujas `chat-message` (usuario/asistente), chips del campo en curso (selección = respuesta completa, se mantienen hasta responder), `title-suggestion` (Aceptar/Otra/Escribir, texto sin modificar); carga visible por llamada IA (RNF-3) | T-041 |

## Criterio de salida

* `pytest -q` verde con `tests/unit/use_cases/test_capture_flow.py` (bloques finalización +
  manual) y `tests/api/test_capture_api.py` (flujo inicio→mensajes→resumen→finish 201, fallback
  503 prellenado, casos 1 y 2).
* `ruff check .` limpio; `ng build` verde.
* Manual (mock): nueva idea → `new-idea` decide asistida → chat con chips y título. (El resumen,
  el manual y la contingencia continúan en G09/G10.)

## Qué no se rompe

* `finish_capture` reutiliza `create_idea` (G06) para la creación validada; no duplica RNF-5.
* `assistant-status` expone la disponibilidad sin disparar el refinamiento (eso es `POST
  /assistant/check`, G15); aquí solo consulta el `ping` del cliente (G04).
* La UI de `new-idea` rellena la ruta `/captura` ya reservada en G01; el chat reutilizará
  `chat-message` en G09 (refinamiento "ajustar en chat") sin obligación de modificarlo.
