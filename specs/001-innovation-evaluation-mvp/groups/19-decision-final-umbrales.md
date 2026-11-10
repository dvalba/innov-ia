# Grupo 19 — Decisión final de calificación, umbrales y cola de calificación

**Vertical:** backend: estados finales `ACEPTADA`/`ARCHIVADA`/`RECHAZADA` en la máquina de
estados, reglas puras de promedio/banda/decisión (RF-27/RF-28), umbrales administrables
(defecto 4/7, RF-28), endpoint de decisión final, reevaluación de `ARCHIVADA` (RF-29), cola de
validación en dos etapas (RF-14) y notificación de calificación pendiente + catálogo por zonas
(RF-20).

## Estado

> ⏳ **En curso** — 3/5 tareas (T-079, T-080, T-081 completadas). Depende de G18 (debate cerrado + evaluación IA vigente).

## Tareas (orden de ejecución)

- [x] **T-079** _(BE)_ — Estados finales y máquina de estados: `ACEPTADA`/`ARCHIVADA`/`RECHAZADA` en `Idea.STATES`, contrato `idea_ledger.py` y `state_machine.py` (transiciones `decide-*` desde `VALIDADA_PUBLICA` y `reevaluate` desde `ARCHIVADA`); estados terminales; `idea.decision` escrito al decidir y limpiado al reevaluar; 409 transición inválida (RNF-9)
- [x] **T-080** _(BE)_ — Reglas puras `validation/domain/decision_rules.py`: `PROMEDIO` (suma/5, 2 decimales), `BANDA` (promedio < X → RECHAZADA; X ≤ promedio < Z → ARCHIVADA; promedio ≥ Z → ACEPTADA, caso 26) y validación de decisión (motivo obligatorio → 400; `outcome` ≠ banda → 409 `DECISION_MISMATCH` con `score`/`band`; no `VALIDADA_PUBLICA` → 409)
- [x] **T-081** _(BE)_ — Umbrales administrables (RF-28): `threshold_store.py` (JSON, un registro) + `GET/PUT /admin/calibration-thresholds` (defecto 4/7, 422 `THRESHOLDS_INVALID` si no enteros 1–10 o `rejection >= acceptance`, auditado `updatedBy`/`updatedAt`, RNF-8; caso 31: sin recálculo de decisiones previas)
- [ ] **T-082** _(BE)_ — Decisión final + reevaluación + cola de calificación: `POST /validation/{id}/decision` (especialista; 409 `DECISION_MISMATCH`, 400 `DECISION_REASON_REQUIRED`; audita + notifica al creador), `POST /ideas/{id}/request-reevaluation` (dueño; 403/409, conserva debate cerrado + evaluación IA, limpia `decision`, notifica `IDEA_REEVALUATED`) y `GET /validation/queue?stage=publicacion|calibracion` (calibración = `VALIDADA_PUBLICA` con debate cerrado, evaluación ≠ PENDING y `decision == null`)
- [ ] **T-083** _(BE)_ — Notificación de calificación pendiente + catálogo por zonas: `EVENT_TYPES` ampliada a 8 eventos; al cerrar el debate y generarse la evaluación IA, `IDEA_CALIBRATION_PENDING` a todos los especialistas (idempotente); `IDEA_REJECTED` reutilizada en calificación (motivo incluido); `GET /catalog/public?zone=en-proceso|aceptadas|rechazadas|archivadas` y detalle con `state` + `decision` en los 4 estados

## Criterio de salida

* Al cerrarse el debate y generarse la evaluación IA, la idea aparece en la etapa de
  **calibración** de la cola de validación y todos los especialistas reciben
  `IDEA_CALIBRATION_PENDING` (una vez).
* El especialista decide aceptada/archivada/rechazada: el resultado debe coincidir con la banda
  del promedio (409 si no) y el motivo es obligatorio para archivada/rechazada (400 si no); la
  decisión queda auditada (quién/cuándo) y el creador es notificado.
* Una `ARCHIVADA` puede reevaluar (conserva debate cerrado + evaluación IA, limpia `decision`);
  `ACEPTADA` y `RECHAZADA` no admiten más transiciones (caso 29).
* Los umbrales (defecto 4/7) se leen y actualizan solo por admin, auditados; el catálogo público
  responde por las 4 zonas.

## Qué no se rompe

* La etapa de **publicación** de la cola y el flujo `approve_idea`/`reject_idea` (RF-14 v1) no
  cambian: la v2.2 añade la segunda etapa, no la sustituye.
* El debate (G18) y la evaluación IA (RF-26) se conservan intactos en la reevaluación: solo se
  limpia `decision` (RF-29).
* El contrato `IdeaLedger` se extiende con constantes nuevas; los existentes no cambian de
  significado.
