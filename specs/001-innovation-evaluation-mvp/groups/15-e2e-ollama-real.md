# Grupo 15 — Integración E2E con Ollama real (captura, contingencia, clarificación, validación)

**Vertical:** las 4 integraciones extremo a extremo con **Ollama corriendo** (no mock) sobre el
sistema montado en G01–G14: captura asistida completa, contingencia (IA caída al inicio y a
mitad), clarificación (refinamiento manual con notificación) y validación (publicación/rechazo +
notificaciones). Solo añade tests + smoke manual; no toca producción.

## Estado

> ⬜ **Pendiente** — 0/4 tareas implementadas.

## Tareas (orden de ejecución)

- [ ] **T-063** _(E2E)_ — Captura asistida e2e: nueva idea → conversación (orden fijo, chips, título con Aceptar/Otra/Escribir) → resumen editable → confirmación → idea EN_DESARROLLO `asistida` visible en "Mis ideas"; tests API con `ollama_mock` determinista; smoke manual con capturas _(T-062 G13, T-043 G09)_
- [ ] **T-064** _(E2E)_ — Contingencia e2e: IA caída al inicio → UI muestra manual con aviso (caso 1); cayendo a mitad → chat ofrece manual preinada con `capturedFields` y el registro crea idea `manual` (caso 2); reintento único 60 s no expuesto (RNF-3); mock de caída + smoke _(T-063, T-045 G09)_
- [ ] **T-065** _(E2E)_ — Clarificación e2e: idea manual con IA caída → al recuperarse, login procesa la cola (más antigua→reciente) + `IDEA_REFINED` con acceso directo → `refine-view` → aceptar (versión vigente, sigue EN_DESARROLLO) o "Ajustar" abre el chat precontextualizado; sin caducidad, idea operativa (caso 5); mock + smoke _(T-064, T-049 G11)_
- [ ] **T-066** _(E2E)_ — Validación e2e: solicitud → `IDEA_REQUESTED` a especialistas → aprobar con rastro + `IDEA_PUBLISHED` + visible en catálogo, o rechazar con comentario + `IDEA_REJECTED` visible; autovalidación con rastro (caso 9); el contador de la campana refleja cada evento y solo esos; mock + smoke _(T-065, T-051 G12, T-055 G12)_

## Criterio de salida

* Smoke manual con Ollama real registrado con capturas/pasos en cada tarea.
* `pytest -q` verde (tests con `ollama_mock` siguen deterministas); `ruff check .` limpio.

## Qué no se rompe

* **No añade código de producción.** Un fallo del smoke señala un bug real: se corrige en el grupo
  de origen (G04/G06/G08/G09/G10/G11/G12/G13) y se revalida aquí.
* La doble pata se mantiene: `ollama_mock` para CI (determinista, T-007) y smoke con IA real.
