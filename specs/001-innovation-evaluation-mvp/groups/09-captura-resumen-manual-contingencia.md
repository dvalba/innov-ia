# Grupo 09 — Captura: resumen editable, formulario manual y contingencia (UI)

**Vertical:** cierra la captura por el lado de la UI — el resumen editable con confirmación (que
produce la idea asistida), el formulario manual de 7 campos con prellenado por contingencia y el
flujo 503 a mitad de conversación (los campos capturados no se pierden, RNF-10).

## Estado

> ✅ **Completado** — 3/3 tareas implementadas (2026-10-07). `ng build` verde,
> `pytest -q` verde (374 tests) y `ruff check .` limpio.

## Tareas (orden de ejecución)

- [x] **T-043** _(FE)_ — `field-summary`: al llegar `state: RESUMEN`, muestra los 7 campos editables; "Confirmar" → `POST /capture/finish` y con 201 navega a Mis ideas; si el backend rechaza (campos incompletos), muestra errores y permanece en el resumen _(T-042 G08)_
- [x] **T-044** _(FE)_ — `manual-form` + `manual-fields`: 7 obligatorios (proponente prellenado de la cuenta y corregible), validación de no-vacío + formato de contacto (caso 12) antes de habilitar el envío, `POST /ideas` origen `manual`; acepta `prellenado` de ruta; en fallo de envío los datos permanecen (caso 17) _(T-041 G08, T-043)_
- [x] **T-045** _(FE)_ — Contingencia a mitad: 503 `ASSISTANT_UNAVAILABLE` en `POST /capture/messages` → aviso de interrupción + "Continuar en formulario manual" pasando `fallback.capturedFields` al manual prellenado; 503 en el reinicio → reintento único (RNF-3) antes de contingencia _(T-042 G08, T-044)_

> **Decisión T-045 (RNF-3):** el reintento único (60 s) reside en el cliente Ollama del backend
> (`ollama_client.py`, T-059), de forma transparente. El frontend no hace reintentos: al recibir
> el 503 final muestra un único aviso de contingencia y ofrece el manual prellenado con
> `fallback.capturedFields` (nada se pierde, RNF-10).

## Flujo extremo a extremo

1. Al completar los 7 campos por chat (G08) llega `RESUMEN`: `field-summary` (T-043) los muestra
   editables; "Confirmar" → `POST /capture/finish` (G08) → 201 → idea EN_DESARROLLO `asistida`
   visible en "Mis ideas" (G10/G11).
2. Sin confirmar no se guarda nada (caso 7). Si faltan campos, el resumen muestra los errores.
3. El formulario manual (T-044) cubre la captura sin IA (caso 1, G08) y la contingencia a mitad
   (T-045): llega un 503 → el chat ofrece "Continuar en formulario manual" con los campos
   ya capturados preinados (RNF-10) y el registro final crea una idea `manual`.
4. En cualquier fallo de envío, los datos permanecen en pantalla (caso 17).

## Criterio de salida

* `ng build` verde.
* Manual (mock): chat completo → resumen → confirmar → 201 en Mis ideas; chat completo → caída 503
  a mitad → manual preinada → fin; sin IA → manual directa (caso 1). (El e2e con Ollama real lo
  certifica G15.)

## Qué no se rompe

* `manual-form` envía a `POST /ideas` (G06): la validación de campos vive en el dominio de ideas;
  la UI solo valida no-vacío/formato para habilitar el envío.
* El reintento único (RNF-3) es transparente: el usuario ve un único aviso de contingencia, no los
  intentos de red.
