# Grupo 14 — Cierre de backend y componentes frontend transversales

**Vertical:** la verificación transversal de todo el backend (pytest completo, ruff, arranque,
humo por endpoint) más los componentes compartidos del frontend (`confirm-dialog` + `idea-card`
promovido a `shared`) que varias features van a reutilizar.

## Estado

> ⬜ **Pendiente** — 0/2 tareas implementadas.

## Tareas (orden de ejecución)

- [ ] **T-036** _(BE)_ — `pytest -q` al completo sin errores ni saltos; `ruff check .` limpio; `uvicorn app.main:app` arranca y `GET /health` 200; todos los endpoints del plan §3.1 presentes y respondiendo con humo en `tests/api/test_endpoints_present.py` _(T-031..T-035 G08/G10 + T-024 G06)_
- [ ] **T-056** _(FE)_ — `shared/components/confirm-dialog` (usado p. ej. en "Solicitar publicación" y en el abandono de captura, caso 7; operable con teclado, RNF-6) + `idea-card` promovido a `shared/components` (Constitución §3.2) y usado en my-ideas (G11), validation (G12) y catalog (G12) sin imports cruzados entre features _(T-046 G11, T-051 G12, T-052 G12)_

## Criterio de salida

* `pytest -q` al completo verde; `ruff check .` limpio; `GET /health` 200 en servidor real arrancado.
* `ng build` verde; `confirm-dialog` y `idea-card` en `shared/components` y consumidos por las 3
  features sin imports cruzados.

## Qué no se rompe

* T-036 no modifica producción: solo añade `tests/api/test_endpoints_present.py`. Si detecta un
  fallo de integración cross-feature, el fix va al grupo de origen (G06/G10) y se revalida aquí.
* La promoción de `idea-card` no cambia su API: solo mueve el archivo y ajusta los imports.
