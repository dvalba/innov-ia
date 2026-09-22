# Grupo 06 — Idea: casos de uso, router y mejora asistida (backend)

**Vertical (parte 2 de la entidad central):** creación/edición, el ciclo de publicación
(solicitar/aprobar/rechazar con rastro y autovalidación), listados (mis ideas / público) y el
router `/ideas` completo, incluida la orquestación backend de `improve_idea` y `adjust_in_chat`
(que inyecta el cliente IA del grupo 04).

## Estado

> ⬜ **Pendiente** — 0/5 tareas implementadas.

## Tareas (orden de ejecución)

- [ ] **T-020** _(BE)_ — `create_idea.py` (7 obligatorios + origen + ownerId; `ValidationFailed` si faltan) + `edit_idea.py` (solo EN_DESARROLLO y dueño; `DomainError` 409 si hay generación en curso) _(T-019 G05)_
- [ ] **T-021** _(BE)_ — `request_publication.py` / `approve_idea.py` (permiso especialista o autovalidación caso 9; rastro `publishedBy`/`publishedAt` + notificaciones vía contrato) / `reject_idea.py` (comentario obligatorio 400 caso 13, rastro del emisor) _(T-020, T-008 ✓)_
- [ ] **T-022** _(BE)_ — `list_my_ideas.py` (solo del usuario) + `list_public.py` (SOLO `VALIDADA_PUBLICA`, sin `contact`) _(T-021)_
- [ ] **T-023** _(BE)_ — `routers/ideas.py`: `POST /ideas` (201/422), `GET /ideas/me`, `GET /ideas/{id}` (403 no dueño), `PUT /ideas/{id}` (409 generando), `POST /ideas/{id}/improve`, `POST /ideas/{id}/versions/{vid}/decide`, `POST /ideas/{id}/request-publication`; esquemas Pydantic solo aquí _(T-022)_
- [ ] **T-024** _(BE)_ — `improve_idea.py` (versión PENDIENTE `requestedBy=improvement`, `reviewedByAI=true`, bloquea edición; sin IA → solicitud pendiente + aviso, caso 10) + `decide` (aceptar → vigente manteniendo EN_DESARROLLO; descartar → conserva) + `adjust_in_chat` (contrato de conversación precontextualizada sobre la idea, RF-2; sin IA → edición manual) _(T-023, cliente IA G04)_

## Criterio de salida

* `pytest -q` verde con `tests/unit/use_cases/test_edit_idea.py`, `test_publication.py` (3 flujos,
  autovalidación, rechazo sin comentario, doble transición 409), `test_listings.py` (filtro por
  dueño/estado, supresión de contacto) y `tests/api/test_ideas_api.py` (201/422/403/409, decide) +
  `test_refinement.py` (bloque RF-8/RF-13: mejora con/sin IA, decisión, ajuste sin IA → manual).
* `ruff check .` limpio.

## Qué no se rompe

* La notificación (IDEA_PUBLISHED/IDEA_REJECTED/IDEA_REQUESTED) se emite vía contrato compartido
  (G12); aquí solo se registran los puntos de emisión, no el store.
* Sin IA disponible, `improve_idea` guarda solicitud pendiente (caso 10) y no lanza error; la
  conversión a real la hace `run_refinement_queue` (G15) al recuperar la IA.
* El router no reimplementa lógica de dominio: transición y validación viven en G05/T-020/T-021.
  `adjust_in_chat` expose un contrato que la UI de G09 consume sin acoplar a `capture`.
