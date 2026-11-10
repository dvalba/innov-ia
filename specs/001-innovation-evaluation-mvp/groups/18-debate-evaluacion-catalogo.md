# Grupo 18 — Debate de ideas publicadas, evaluación IA y catálogo con detalle

**Vertical:** nueva feature `debate` en backend (mensajes, 30 días, @asistant, cierre + resumen)
y evaluación de la IA sobre 5 criterios con decisión del especialista (aceptar/sustituir), +
frontend: catálogo compacto (título, fecha de publicación, descripción) y vista de detalle de la
idea (resumen de los 6 campos, debate y evaluación).

## Estado

> ⏳ **En curso** — 4/5 tareas. Depende de G17 (contexto inyectado en la IA y 6 campos).

## Tareas (orden de ejecución)

- [x] **T-072** _(BE)_ — Feature `debate`: dominio `Debate`/`DebateMessage`, store JSON (`backend/data/debate.json`), rules de creación (publishedAt + 30 días), cierre automático una sola vez, ajuste de deadline por idea auditado (admin), mensajes solo con debate abierto
- [x] **T-073** _(BE)_ — Router del debate: `GET/POST /catalog/{ideaId}/debate`, `PUT /admin/ideas/{ideaId}/debate/deadline` (admin); `@asistant` con mensaje enlazado responde en el hilo (IA + contexto de empresa, RNF-3); cierre genera el resumen de la IA si hubo mensajes (casos 18-21)
- [x] **T-074** _(BE)_ — Evaluación de la IA al cerrarse el debate (5 criterios fijos: claridad del problema, factibilidad, impacto esperado, alineación estratégica, grado de innovación; score 1–10 + justificación; autor "Asistente (IA)"); la publicación no la ejecuta; si la IA cae, `pending` sin bloquear el cierre (caso 22) y reintento en la siguiente verificación; `POST /validation/{ideaId}/evaluation/accept` (409 sin evaluación de la IA) y `POST /validation/{ideaId}/evaluation` (sustitución por especialista sin tocar la instantánea, caso 23), auditados (RNF-8, RNF-11)
- [x] **T-077** _(FE)_ — Catálogo compacto + ruta `/catalogo/publico/{id}`: resumen de los 6 campos (solo lectura), debate (mensajes, input, selector de mensaje enlazado, @asistant, cierre/fecha límite, resumen IA, ajuste admin inline) y evaluación por estados (sin evaluación → aviso de que se generará al cerrarse el debate; PENDING → aviso + solo sustitución; GENERADA → 5 criterios + aceptar/sustituir; ACEPTADA/SUSTITUIDA → juicio final + instantánea IA de solo lectura); responsive y accesible (RNF-6)
- [ ] **T-078** _(E2E)_ — Verificación de los criterios v2.1 del spec §9 (10-14) y casos límite 18, 20, 22 con evidencia: publicar → debate → @asistant → cierre → resumen; evaluación → sustitución; contexto vacío/inyectado; `pytest -q`, `ruff check .` y `ng build` verdes

## Criterio de salida

* Publicar una idea abre su debate (30 días); al llegar la fecha límite el debate cierra (solo una
  vez), el resumen es visible y se genera la evaluación IA (o queda `pending` si la IA cae, con
  reintento).
* Cualquier usuario con sesión escribe en el debate; `@asistant` responde en el hilo.
* El especialista acepta o sustituye la evaluación; queda un único juicio final auditado.
* El catálogo compacto enlaza a la vista de detalle completa.

## Qué no se rompe

* La idea publicada no se edita: el debate y la evaluación son atributos adicionales (D12); la
  máquina de estados no cambia.
* `approve_idea` publica sin ejecutar la evaluación IA (se genera al cerrarse el debate); el cierre
  del debate sigue ocurriendo aunque la IA esté caída (la evaluación queda `pending`, RNF-1).
* El catálogo solo expone VALIDADA_PUBLICA (sin contacto, RNF-7); el debate y la evaluación son
  visibles para toda sesión.
