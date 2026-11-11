# Grupo 20 — Frontend: ficha de calificación, decisión, zonas y reevaluación

**Vertical:** frontend: cola de validación en dos etapas + **ficha de calificación** (6 campos,
debate compactado, calificación IA vigente, formulario de decisión final con promedio/banda en
vivo + diálogo de confirmación), umbrales administrables, catálogo en **4 zonas**, detalle con
estado final + decisión, debate compactado con enlace a solo lectura y reevaluación en **Mis
ideas**. + E2E v2.2.

## Estado

> ⏳ **En curso** — 1/3 tareas. T-084 completada; T-085/T-086 pendientes.

## Tareas (orden de ejecución)

- [x] **T-084** _(FE)_ — Ficha de calificación + decisión final + umbrales admin: selector de etapa en `/validacion` (publicación / calibración); la entrada de calibración abre la ficha completa (6 campos, debate compactado, calificación IA con aceptar/sustituir) y el **formulario de decisión final** con **promedio** y **banda** en vivo (misma regla pura que el backend), validación de coincidencia (aviso 409), motivo obligatorio para archivada/rechazada (aviso 400), **diálogo de confirmación** con aviso de consecuencia; pestaña admin **Umbrales de calificación** (dos enteros 1–10, `rechazo < aceptación`, guardado auditado)
- [ ] **T-085** _(FE)_ — Catálogo por 4 zonas + debate compactado + reevaluación: `/catalogo/publico` en 4 pestañas (En proceso / Aceptadas / Rechazadas / Archivadas, `?zone=`); detalle de estado final con estado + decisión (resultado, motivo, promedio, especialista, fecha) en solo lectura; debate cerrado **compactado** (resumen IA o aviso sin debate) con enlace a vista **solo lectura** del chat completo; **Mis ideas** muestra los estados finales y, en `ARCHIVADA`, la acción **Solicitar reevaluación** (confirmación); sin acción en `ACEPTADA`/`RECHAZADA` (caso 29)
- [ ] **T-086** _(E2E)_ — Verificación de la ampliación v2.2 (spec §9 + casos 26–31): publicar → debate → cierre → evaluación IA → cola de calificación + notificación a especialistas → calificación → decisión (409/400) → estado final + zona + notificación al creador; reevaluación de `ARCHIVADA` (conserva debate cerrado + evaluación IA, limpia `decision`) y no-reevaluación de `ACEPTADA`/`RECHAZADA`; umbrales defecto 4/7, cambio auditado, inválidos 422 y sin recálculo; `pytest -q`, `ruff check .` y `ng build` verdes

## Criterio de salida

* El especialista ve la cola en dos etapas; en calificación, la ficha completa muestra promedio y
  banda en vivo mientras puntúa y le obliga a confirmar con el aviso de consecuencia antes de
  decidir (coincidencia obligatoria, motivo según resultado).
* El catálogo público se navega por 4 zonas; el detalle muestra estado final + decisión en solo
  lectura y el debate cerrado compactado con acceso al chat completo (solo lectura).
* El dueño reevalúa una `ARCHIVADA` desde Mis ideas y ve desaparecer la acción en los estados
  terminales; el admin ajusta los umbrales desde la sección de administración.

## Qué no se rompe

* La etapa de **publicación** y su panel (T-051/T-052) se conservan: la UI de validación se
  extiende, no se reemplaza.
* El debate y la evaluación de G18 se reutilizan en la ficha de calificación (aceptar/sustituir
  sigue operando igual).
* `ng build` verde tras cada feature; accesibilidad (teclado/aria, RNF-6) en las nuevas vistas.
