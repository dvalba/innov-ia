# Grupo 15 — Integración E2E con Ollama real (captura, contingencia, clarificación, validación)

**Vertical:** las 4 integraciones extremo a extremo con **Ollama corriendo** (no mock) sobre el
sistema montado en G01–G14: captura asistida completa, contingencia (IA caída al inicio y a
mitad), clarificación (refinamiento manual con notificación) y validación (publicación/rechazo +
notificaciones). Solo añade tests + smoke manual; no toca producción.

## Estado

> ✅ **Completado** — 4/4 tareas implementadas y verificadas (2026-10-13). `pytest -q` verde
> (468 tests) y `ruff check .` limpio. Smoke real de Ollama contra el modelo
> `qwen38-27b-112k:latest` registrado abajo; el primer smoke (con el código anterior) expuso un
> bug real de producción (replies de modelos con "thinking" rompían el contrato JSON) que se
> corrigió en G04/G08 y se revalidó aquí — ver "Registro de verificación".

## Tareas (orden de ejecución)

- [x] **T-063** _(E2E)_ — Captura asistida e2e: nueva idea → conversación (orden fijo, opciones rápidas generadas por turno D7, título con Aceptar/Otra/Escribir) → resumen editable → confirmación → idea EN_DESARROLLO `asistida` visible en "Mis ideas"; tests API con `ollama_mock` determinista; smoke manual con capturas _(T-062 G13, T-043 G09)_
- [x] **T-064** _(E2E)_ — Contingencia e2e: IA caída al inicio → UI muestra manual con aviso (caso 1); cayendo a mitad → chat ofrece manual preinada con `capturedFields` y el registro crea idea `manual` (caso 2); reintento único 60 s no expuesto (RNF-3); mock de caída + smoke _(T-063, T-045 G09)_
- [x] **T-065** _(E2E)_ — Clarificación e2e: idea manual con IA caída → al recuperarse, login procesa la cola (más antigua→reciente) + `IDEA_REFINED` con acceso directo → `refine-view` → aceptar (versión vigente, sigue EN_DESARROLLO) o "Ajustar" abre el chat precontextualizado; sin caducidad, idea operativa (caso 5); mock + smoke _(T-064, T-049 G11)_
- [x] **T-066** _(E2E)_ — Validación e2e: solicitud → `IDEA_REQUESTED` a especialistas → aprobar con rastro + `IDEA_PUBLISHED` + visible en catálogo, o rechazar con comentario + `IDEA_REJECTED` visible; autovalidación con rastro (caso 9); el contador de la campana refleja cada evento y solo esos; mock + smoke _(T-065, T-051 G12, T-055 G12)_

## Criterio de salida

* Smoke manual con Ollama real registrado con capturas/pasos en cada tarea.
* `pytest -q` verde (tests con `ollama_mock` siguen deterministas); `ruff check .` limpio.

## Qué no se rompe

* **No añade código de producción.** Un fallo del smoke señala un bug real: se corrige en el grupo
  de origen (G04/G06/G08/G09/G10/G11/G12/G13) y se revalida aquí.
* La doble pata se mantiene: `ollama_mock` para CI (determinista, T-007) y smoke con IA real.

## Registro de verificación (2026-10-13)

**Automatizado** — `pytest -q` en `backend/`: **468 passed**, incluyendo
`tests/api/test_e2e_flows_g15.py` (4 e2e deterministas con `ollama_mock`):

| Paso | Verificación | Resultado |
|---|---|---|
| T-063 | Captura asistida completa (orden fijo `description`→…→`proponent`, opciones rápidas por turno D7, título Aceptar/Otra/Escribir, resumen editable) → confirmación → idea `asistida`/`EN_DESARROLLO` en "Mis ideas"; el reintento único (RNF-3) queda interno | ✅ |
| T-064 | Contingencia: IA caída al inicio → `mode: manual` + aviso (caso 1); cayendo a mitad → 503 `ASSISTANT_UNAVAILABLE` + `capturedFields` de pre-lleno (RNF-10, caso 2); registro manual crea idea `manual` | ✅ |
| T-065 | Idea manual + IA disponible → `POST /assistant/check` procesa la cola (más antigua→reciente) → versión refinada + `IDEA_REFINED`; aceptar → versión vigente, idea sigue `EN_DESARROLLO` (caso 5, sin caducidad) | ✅ |
| T-066 | Solicitud de publicación → fanout `IDEA_REQUESTED` a especialistas → aprobar con rastro → `IDEA_PUBLISHED` + visible en catálogo (y rama de rechazo `IDEA_REJECTED`); la campana cuenta solo estos eventos (caso 9) | ✅ |

**Smoke manual (Ollama real)** — `uvicorn app.main:app --port 8032` contra
`OLLAMA_BASE_URL=http://172.18.201.201:11434` con `OLLAMA_MODEL=qwen38-27b-112k:latest`,
`INNOV_DATA_DIR=/tmp/opencode/smoke_g15_re/data`, `OLLAMA_TIMEOUT=180`; driver
`/tmp/opencode/smoke_g15_re/drive_re_smoke.py`, salida en
`/tmp/opencode/smoke_g15_re/RE_SMOKE_OUTPUT.txt` y servidor en `uvicorn.log`. Flujos reales en
verde:

| Paso | Verificación (modelo real) | Resultado |
|---|---|---|
| T-063 | `assistant-status: OK`; `POST /capture/start` → `mode: assistant`, turno `description`; 1 turno narrativo captura `description` (+`problem`) y pasa a `title`; título generado y aceptado; opciones rápidas por turno para `problem`/`expectedBenefit`/`strategicAlignment`/`estimatedResources` (D7); `RESUMEN`; confirmación → `POST /capture/finish` 201 `{state: EN_DESARROLLO, origin: asistida}`; 1 idea en `/ideas/me` | ✅ |
| T-065 | Idea manual creada → `POST /assistant/check` 200 `{status: OK, refined: 1, failed: 0, pending: 0}`; versión `requestedBy: refinement` + `IDEA_REFINED`; `decide accept` → versión vigente, idea sigue `EN_DESARROLLO` | ✅ |
| T-066 | `request-publication` → `IDEA_REQUESTED` (fanout al especialista) → cola de validación → `approve` → `IDEA_PUBLISHED` + visible en `/catalog/public` | ✅ |

* La contingencia (T-064) se certifica por la e2e determinista (casos 1/2): el escenario de IA
  caída en un modelo real no es reproducible a demanda; la rama de recuperación y el pre-lleno
  quedan fijados por el mock (RNF-3/RNF-10) y el camino "IA disponible" se revalida en el smoke real.

**Bug de producción detectado por el primer smoke y corregido (G04/G08):** el primer smoke real
exponía que, con el modelo con "thinking", la respuesta del motor llegaba envuelta en un
párrafo de razonamiento (a veces con objetos de ejemplo embebidos y marcas `</thinking>`), de modo
que el contrato "solo JSON" se rompía: la extracción de campos (T-063) fallaba al 503 de
contingencia y el refinamiento (T-065) era no determinista. Por la regla "no añade producción", se
corrigió en los grupos de origen y se revalidó aquí:

* **G04** (`ollama_client.py`): el cuerpo de `/api/generate` incluye `think: false` — el
  asistente siempre parsea JSON, así que se pide a los modelos con "thinking" que omitan el
  razonamiento (la flag la ignoran los que no piensan). Regression: `test_ollama_client.py::
  test_generate_disables_thinking_in_request_body`.
* **G08** (`refinement.py`): `extract_json_object` público y robusto — parse estricto primero,
  recorte de vallas de razonamiento (`</thinking>`/`</think>`) y barrido que conserva el último
  objeto bien formado, de modo que un ejemplo embebido nunca eclipsa el payload real; lo consumen
  ahora `interpret_fields`, `process_message` y `suggest_title`. Regression:
  `test_refinement.py::test_extracts_object_after_reasoning_preamble_with_embedded_example`.

* Nota de alcance: el modelo real devuelve claves en inglés (`title`, `description`, …) — las
  mismas que exige el contrato — por lo que no se usa `format: json` (que forzaba claves en
  español como `descripcion` y las validaciones las rechazarían).
