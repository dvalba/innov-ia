# Grupo 12 — Validación, catálogo y campana (UI)

**Vertical:** cierra el ciclo de publicación en frontend — cola del especialista con panel
validar/rechazar (comentario obligatorio), página de catálogo público de solo lectura y la campana
de notificaciones (contador, lista, navegación por `ideaId`, marcar leída).

## Estado

> ⬜ **Pendiente** — 0/3 tareas implementadas.

## Tareas (orden de ejecución)

- [ ] **T-051** _(FE)_ — `validation/pages/queue` (7 campos, proponente nombre/área, fecha de solicitud, `httpResource`) + `validate-panel` ("Validar" → approve; "Rechazar" con comentario obligatorio, botón bloqueado sin comentario, caso 13); estados se refrescan tras la acción con confirmación ES _(T-039 G02, T-034 G10)_
- [ ] **T-052** _(FE)_ — `catalog/pages/public`: ideas `VALIDADA_PUBLICA` (7 campos, nombre/área, fechas de registro y publicación, `httpResource`), sin datos de contacto y sin botones de edición; accesible con cualquier sesión _(T-039 G02, T-035 G10)_
- [ ] **T-055** _(FE)_ — `notification-bell` (en el layout, G01): contador de no leídas (polling `GET /notifications`), lista con mensaje ES y fecha, navegación al objeto por `ideaId` (detalle de idea, G11) y marcar leída al consultar (POST read); sin notificaciones fuera de la app _(T-006 G01, T-033 G10)_

## Flujo extremo a extremo

1. Un proponente solicita publicación (G06/G11) → backend fanoutea `IDEA_REQUESTED` a todos los
   especialistas (G10).
2. El especialista entra a `/validacion` (guard de G02): la cola lista las ideas
   SOLICITANDO_PUBLICACION sin datos de contacto (G10/T-034). "Validar" → VALIDADA_PUBLICA con
   rastro + `IDEA_PUBLISHED` al proponente; "Rechazar" exige comentario (400 sin él, caso 13) →
   EN_DESARROLLO + `IDEA_REJECTED`.
3. La idea aprobada aparece en `/catalogo` para cualquier usuario (T-052, solo lectura).
4. La campana (T-055) lleva el contador de no leídas, permite navegar al detalle de la idea
   (`ideaId`, G11) y la marca leída al consultar el objeto. Solo refleja los 4 eventos.

## Criterio de salida

* `ng build` verde.
* Manual (mock): solicitud → cola del especialista → aprobar → visible en catálogo + notificación
  al proponente; rechazar con comentario → nota visible (G11) + notificación.

## Qué no se rompe

* Los endpoints (G10) se consumen tal cual; la UI no reimplementa reglas (403/400/409 del backend).
* La campana vive en `shared/components` (G01) y navega a las features sin imports cruzados.
