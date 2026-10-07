# Grupo 10 — Notificaciones (backend) validación y catálogo

**Vertical (parte 1):** el sistema de notificaciones (solo 4 eventos, fanout a especialistas,
contador, marcar leída) + la cola del especialista (aprobación/rechazo reutilizando el ciclo de
G06, visibilidad sin datos de contacto) + el endpoint del catálogo público.

## Estado

> ✅ **Completado** — 4/4 tareas implementadas (2026-10-07). Nota: el punto de
> emisión `IDEA_REFINED` queda enlazado al caso de uso `refine_manual` de G13
> (T-061); en G10 el emisor está registrado en la composición raíz y ejercitado,
> pero aún sin endpoint que lo dispare.

## Tareas (orden de ejecución)

- [x] **T-032** _(BE)_ — `domain/notification.py` (SOLO `IDEA_REFINED, IDEA_PUBLISHED, IDEA_REJECTED, IDEA_REQUESTED`) + `infrastructure/notification_store.py` (JsonStore, por usuario, leída/no leída) _(T-003 ✓)_
- [x] **T-033** _(BE)_ — `create_notification.py` (eventos del proponente con `ideaId`; fanout `IDEA_REQUESTED` a **todos** los especialistas) + `list_notifications.py` (lista + contador) + `mark_read.py` + `routers/notifications.py` (`GET /notifications`, `POST /notifications/{id}/read` solo destinatario) + puntos de emisión registrados desde `ideas`/`assistant` vía contrato _(T-032, T-021 G06)_
- [x] **T-034** _(BE)_ — `domain/queue_rules.py` (solo SOLICITANDO_PUBLICACION; proponente sin contacto) + `use_cases/review_queue.py` + `routers/validation.py` (`GET /validation/queue`, `POST /validation/{id}/approve`, `POST /validation/{id}/reject`; rol especialista 403) reutilizando `approve_idea`/`reject_idea` _(T-021 G06, T-033, T-013 ✓)_
- [x] **T-035** _(BE)_ — `GET /catalog/public`: solo sesión activa (cualquier rol, 401 sin sesión), ideas `VALIDADA_PUBLICA` con 7 campos, nombre/área del proponente, fechas de registro y publicación; sin `contact` _(T-022 G06)_

## Criterio de salida

* `pytest -q` verde con `tests/unit/infra/test_notification_store.py` (creación, listado por
  usuario, contador), `tests/api/test_notifications_api.py` (los 4 y solo los 4 eventos, fanout,
  contador, marcar leída), `tests/api/test_validation_api.py` (cola sin contacto, rastro,
  notificaciones, rechazo con/sin comentario caso 13) y `tests/api/test_catalog_api.py` (solo
  VALIDADA_PUBLICA, sin contacto, 401).
* `ruff check .` limpio.

## Qué no se rompe

* `validation` no reimplementa la transición: reutiliza `approve_idea`/`reject_idea` (G06),
  preservando el rastro y las notificaciones existentes.
* Las notificaciones se emiten vía contrato compartido (T-008): `ideas`/`assistant` no importan
  de `notifications`.
* Solo 4 tipos de evento: no se añade ningún otro (RF-18).
