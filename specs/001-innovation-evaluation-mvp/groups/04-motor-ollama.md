# Grupo 04 — Motor de IA: cliente Ollama y prompts (solo backend)

**Vertical:** el motor que genera todo el texto del sistema — cliente nativo (stdlib) a Ollama con
timeout/reintento y el dominio de prompts y reglas de refinamiento. Backend puro, testeable en
aislamiento con un servidor HTTP simulado; desbloquea captura (G08), mejora (G06), asistente
(G13) y el E2E real (G15).

> Puede ejecutarse en paralelo desde ya: solo depende de núcleo ya hecho (T-001, T-002, T-007).

## Estado

> ✅ **Completado** — 2/2 tareas implementadas (2026-09-23).

## Tareas (orden de ejecución)

- [x] **T-059** _(BE)_ — `ollama_client.py` (stdlib `urllib`/`http.client`): `ping()`, `generate(prompt)`, timeout 60 s (RNF-3), reintento único transparente; "fallo de IA" (sin respuesta a tiempo, error de servicio, respuesta no interpretable, caso 14) → `AssistantUnavailable` _(T-001 ✓)_
- [x] **T-060** _(BE)_ — `prompts.py` (extracción de campos RF-3, sugerencia de título RF-4 con intentos a evitar, refinamiento 7 campos, mejora bajo instrucción RF-8) + `refinement.py` (cola: manual + EN_DESARROLLO + sin refinada, más antigua→reciente; interpretación de respuesta → fallo si no interpretable) _(T-059)_

## Criterio de salida

* `pytest -q` verde con `tests/unit/infra/test_ollama_client.py` (ping OK, timeout con reintento
  único, error de servicio → contingencia) y `tests/unit/domain/test_refinement.py` (filtro de
  cola, orden, interpretación inválida → fallo), vía servidor HTTP simulado.
* `ruff check .` limpio.

## Qué no se rompe

* Sin endpoint ni router: solo añade `features/assistant/infrastructure/ollama_client.py` y
  `features/assistant/domain/{prompts,refinement}.py`. Sin dependencias externas (Constitución
  §6.1). En tests se usa `ollama_mock` (T-007); el cliente real queda listo para el smoke de G15.
