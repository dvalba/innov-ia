# Grupo 17 — Contexto de empresa administrable y retirada de *Recursos estimados*

**Vertical:** backend `org` (documento de contexto: plantilla/edición/subida) inyectado en todos
los prompts del asistente (captura, título, mejora, refinamiento — y de forma premisas para
G18: debate y evaluación), + eliminación completa del campo *Recursos estimados* (6 campos,
decisión D11) en backend y frontend.

## Estado

> ⏳ **En curso** — 2/5 tareas completadas. Depende del cierre de G16.

## Tareas (orden de ejecución)

- [x] **T-069** _(BE+FE)_ — Retirar `estimatedResources` de todo el backend y frontend (dominio, validación, schemas, FIELD_ORDER, preguntas, chips, prompts, formularios, labels); migración silenciosa de ideas antiguas al leer
 - [x] **T-070** _(BE)_ — Contexto de empresa como único documento administrable: plantilla descargable (`GET /admin/contexto/plantilla`), lectura (`GET /admin/contexto`), edición (`PUT /admin/contexto`), subida de archivo (`POST /admin/contexto/subida`); seed desde `INNOV_ORG_*` conservado; casos 24 y 25
- [ ] **T-071** _(BE)_ — Inyección del contexto de empresa en TODAS las operaciones de la IA (extract, título, refinamiento, mejora, turn_options); aviso "(sin contexto de empresa definido)" cuando el documento está vacío (RNF-12)
- [ ] **T-075** _(FE)_ — Captura y formularios con 6 campos: manual, resumen editable del chat, detalle/edición de Mis ideas, contingencia de new-idea y labels; validación 6/6
- [ ] **T-076** _(FE)_ — Sección **Contexto de empresa** en administración: descargar plantilla, editar en línea, subir archivo, aviso de contexto vacío

## Criterio de salida

* `grep -rn estimatedResources backend frontend/src` → 0 coincidencias; `pytest -q` y `ng build` verdes.
* Cada prompt del asistente incluye el contexto vigente o el aviso de vacío (tests unitarios).
* Los 4 endpoints de contexto funcionan solo con rol admin (403 sin él) y la plantilla se descarga.

## Qué no se rompe

* La feature `org` existente (perfil de organización) se **extiende**, no se reemplaza: el perfil
  queda como sección del documento de contexto y la compatibilidad con `INNOV_ORG_*` se conserva.
* El flujo de captura no cambia de forma: solo pasan a ser 6 las preguntas (D11).
* RNF-5 pasa a exigir 6 campos completos.
