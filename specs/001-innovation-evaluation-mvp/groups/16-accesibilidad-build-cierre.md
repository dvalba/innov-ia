# Grupo 16 — Accesibilidad transversal, build final y cierre de especificación

**Vertical:** el cierre final del MVP — accesibilidad completa (teclado + lectores de pantalla,
UI al 100% en español), build de verificación de guías (Constitución: sin `*ngIf`/`*ngFor`/
`@Input`/`@Output`, `inject()`, `httpResource`, sin sufijo `Component`, sin imports cruzados
entre features) y la verificación de los 13 criterios de finalización del spec §9 con casos
límite.

## Tareas (orden de ejecución)

| # | ID | Capa | Tarea | Dependencias |
|---|------|------|-------|--------------|
| 1 | T-057 | FE | Accesibilidad transversal: chat, chips, formularios, notificaciones y catálogos operables solo con teclado (orden de foco lógico, `aria-expanded`/`aria-live`, labels, ARIA en diálogos); toda la UI en español (RNF-4); recorrido manual documentado por feature | T-042 (G08), T-044 (G09), T-055 (G12) |
| 2 | T-058 | FE | `ng build` sin errores; estructura = plan §1.1 (6 features + shared); grep de patrones vacía (`*ngIf`/`*ngFor`/`@Input`/`@Output`); se usa `inject()`, `httpResource` en lecturas, `input()/output()/signal()`; sin sufijo `Component`; ningún componente de feature importa de otra; rutas lazy activas | T-037..T-057 (todos los grupos) |
| 3 | T-068 | E2E | Verificación de los 13 criterios de finalización del spec §9 con evidencia: (1) login/logout; (2) captura asistida e2e; (3) captura manual e2e; (4) contingencia preinada; (5) clarificación completa; (6) mejora aceptada/descartada + edición manual; (7) validación e2e con notificación; (8) usuarios/roles; (9) notificaciones (4 eventos, contador, navegación, leída); (10) catálogo solo VALIDADA_PUBLICA sin contacto; (11) casos límite 1,2,5,6,7,13,16,17; (12) `pytest -q` completo; (13) estructura por features + guías Angular/Tailwind; `ruff check .` limpio | T-058, T-063..T-066 (G15), T-067 (G03) |

## Criterio de salida

* Recorrido de accesibilidad documentado (criterio manual firmado).
* `ng build` verde + checklist de guías Angular/Tailwind/Constitución cumplida.
* Checklist del spec §9 completado: 13 criterios + 8 casos límite con evidencia.

## Qué no se rompe

* T-057 es ajuste fino sobre componentes ya construidos (labels, aria, foco); no hace rediseño.
* T-058 es build/estática: si detecta import cruzado o patrón prohibido, se corrige en el feature
  afectado sin tocar lógica.
* T-068 no modifica producción: solo verifica y documenta evidencia.
