# Grupo 06 — Idea: casos de uso, router y mejora asistida (backend)

**Vertical (parte 2 de la entidad central):** creación/edición, el ciclo de publicación
(solicitar/aprobar/rechazar con rastro y autovalidación), listados (mis ideas / público) y el
router `/ideas` completo, incluida la orquestación backend de `improve_idea` y `adjust_in_chat`
(que inyecta el cliente IA del grupo 04).

## Estado

> ⬜ **Pendiente** — 3/5 tareas implementadas.

## Tareas (orden de ejecución)

- [x] **T-020** _(BE)_ — `create_idea.py` (7 obligatorios + origen + ownerId; `ValidationFailed` si faltan) + `edit_idea.py` (solo EN_DESARROLLO y dueño; `DomainError` 409 si hay generación en curso) _(T-019 G05)_
- [x] **T-021** _(BE)_ — `request_publication.py` / `approve_idea.py` (permiso especialista o autovalidación caso 9; rastro `publishedBy`/`publishedAt` + notificaciones vía contrato) / `reject_idea.py` (comentario obligatorio 400 caso 13, rastro del emisor) _(T-020, T-008 ✓)_
- [x] **T-022** _(BE)_ — `list_my_ideas.py` (solo del usuario) + `list_public.py` (SOLO `VALIDADA_PUBLICA`, sin `contact`) _(T-021 ✓)_
- [ ] **T-023** _(BE)_ — `routers/ideas.py`: `POST /ideas` (201/422), `GET /ideas/me`, `GET /ideas/{id}` (403 no dueño), `PUT /ideas/{id}` (409 generando), `POST /ideas/{id}/improve`, `POST /ideas/{id}/versions/{vid}/decide`, `POST /ideas/{id}/request-publication`; esquemas Pydantic solo aquí _(T-022 ✓)_
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

## Registro de verificación (G06, 2026-09-23)

**Automatizado** — `pytest -q` en `backend/`: 213 passed; `ruff check .` limpio. Uno por
tarea (commits separados):

| Tarea | Verificación | Resultado |
|---|---|---|
| T-020 | `create_idea.py`: 7 campos + origen (`asistida`/`manual`) + `ownerId` en `EN_DESARROLLO`; `ValidationFailed` 422 si faltan campos o el contacto es inválido (RNF-5, caso 12) sin registro parcial (caso 17), origen desconocido 400. `edit_idea.py`: solo dueño (403, RNF-7) y solo `EN_DESARROLLO` (409; §8.8), 404 inexistente, 409 `generando` con aviso (RF-9), 422 campos incompletos; persistencia por CAS `update_state` (RNF-9). Bandera `generando` en `Idea` (round-trip sin pérdida) y en `IdeaStore.add_version(generating=...)`; `decide()` la libera cuando no queda versión PENDIENTE | ✅ 17 tests (`test_edit_idea.py` 12 + `test_idea_store.py` 5 nuevos) |
| T-021 | `request_publication.py`: EN_DESARROLLO→SOLICITANDO_PUBLICACION (única vía, §4.6) fijando `requestDate`; 404 inexistente, 403 no-proponente (RNF-7/RF-10); emite el punto `IDEA_REQUESTED` vía emisor inyectado (fanout a especialistas, RF-18; G10 lo resuelve). `approve_idea.py`: 403 sin rol especialista; autovalidación caso 9 permitida con rastro obligatorio; SOLICITANDO→VALIDADA_PUBLICA registrando `publishedBy`/`publishedAt` (RNF-8); emite `IDEA_PUBLISHED`. `reject_idea.py`: 400 sin comentario (caso 13); SOLICITANDO→EN_DESARROLLO con `rejectionNote` (by/byName/comment/at, RNF-8); conserva `requestDate`; emite `IDEA_REJECTED`. Transición doble (RNF-9, caso 11): la segunda acción se descarta con 409 `INVALID_TRANSITION` y nada queda inconsistente (CAS `update_state`). Contrato de roles compartido `shared/contracts/roles.py` (nombres de rol + `list_specialists`) sin importar `features/`; `features.users` ahora lo reutiliza (una sola fuente) | ✅ 19 tests (`test_publication.py`) — suite 232 passed, `ruff check .` limpio |
| T-022 | `list_my_ideas.py`: solo las ideas del solicitante (RNF-7), en cualquier estado (RF-11), con el resumen RF-19 (`id`, `title`, `createdAt`, `origin`, `state`), más recientes primero. `list_public.py`: SOLO `VALIDADA_PUBLICA` de cualquier dueño (RF-20, decisión #2 — nada menos aparece); 7 campos con el proponente reducido a `name`/`area` (`contact` suprimido, RNF-7, §5.9), `createdAt` y `publishedAt`, más recientes primero; vacío cuando no hay publicadas | ✅ 8 tests (`test_listings.py`) — suite 240 passed, `ruff check .` limpio |
