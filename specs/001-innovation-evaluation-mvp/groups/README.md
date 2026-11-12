# Grupos de desarrollo vertical — Innov-IA MVP

Organización de las **57 tareas** del MVP v2.0 (G01–G16, todas completadas) más las **10 tareas
de la ampliación de alcance v2.1** (G17–G18), las **5 tareas backend de la ampliación v2.2**
(G19) y las **3 tareas frontend/E2E de la v2.2** (G20) en **20 grupos de desarrollo vertical**,
cada uno con **máximo 5 tareas**, conectando el backend con su respectiva vista de frontend de
extremo a extremo.

## Orden recomendado (secuencia crítica)

> **Estado:** las tareas de cada grupo son checkboxes marcables (`- [x]` / `- [ ]`) en su
> archivo; el estado se actualiza al verificar la implementación contra el código y los tests.

| Orden | Archivo | Vertical (BE ↔ FE) | Tareas | # | Hechas | Estado |
|-------|---------|--------------------|--------|---|--------|--------|
| 01 | [`01-nucleo-frontend.md`](01-nucleo-frontend.md) | Shell Angular, interceptores, sesión, modelos TS | T-004, T-005, T-006, T-009 | 4 | 4/4 | ✅ |
| 02 | [`02-autenticacion-e2e.md`](02-autenticacion-e2e.md) | Router `/users` + login, cambio forzado, cierre, guards por rol | T-016, T-037, T-038, T-039 | 4 | 4/4 | ✅ |
| 03 | [`03-admin-usuarios-e2e.md`](03-admin-usuarios-e2e.md) | Panel `/admin` + matriz de roles + e2e usuarios/roles | T-053, T-054, T-067 | 3 | 3/3 | ✅ |
| 04 | [`04-motor-ollama.md`](04-motor-ollama.md) | Cliente Ollama stdlib + prompts/reglas (solo BE; puede ir en paralelo) | T-059, T-060 | 2 | 2/2 | ✅ |
| 05 | [`05-idea-dominio-y-store.md`](05-idea-dominio-y-store.md) | `Idea` + validación + máquina de estados + `idea_store` | T-017, T-018, T-019 | 3 | 3/3 | ✅ |
| 06 | [`06-idea-casos-uso-y-router.md`](06-idea-casos-uso-y-router.md) | UC crear/editar/publicar/listar + router `/ideas` + mejora asistida | T-020, T-021, T-022, T-023, T-024 | 5 | 5/5 | ✅ |
| 07 | [`07-captura-dominio-y-procesamiento.md`](07-captura-dominio-y-procesamiento.md) | Conversación: reglas, store, inicio, procesamiento, título | T-025, T-026, T-027, T-028, T-029 | 5 | 5/5 | ✅ |
| 08 | [`08-captura-final-y-router-ui-arranque.md`](08-captura-final-y-router-ui-arranque.md) | Finalización/contingencia + router `/capture` + `new-idea` + chat | T-030, T-031, T-040, T-041, T-042 | 5 | 5/5 | ✅ |
| 09 | [`09-captura-resumen-manual-contingencia.md`](09-captura-resumen-manual-contingencia.md) | Resumen editable + formulario manual + contingencia 503 | T-043, T-044, T-045 | 3 | 3/3 | ✅ |
| 10 | [`10-notificaciones-validacion-catalogo.md`](10-notificaciones-validacion-catalogo.md) | Notificaciones (4 eventos) + cola especialista + `/catalog/public` | T-032, T-033, T-034, T-035 | 4 | 4/4 | ✅ |
| 11 | [`11-mis-ideas-ui.md`](11-mis-ideas-ui.md) | Listado, detalle+edición, mejoras IA, refinamiento, nota de rechazo | T-046, T-047, T-048, T-049, T-050 | 5 | 5/5 | ✅ |
| 12 | [`12-validacion-catalogo-campana.md`](12-validacion-catalogo-campana.md) | Cola+panel validar/rechazar + catálogo público + campana | T-051, T-052, T-055 | 3 | 3/3 | ✅ |
| 13 | [`13-asistente-check.md`](13-asistente-check.md) | UC asistente (refinamiento, cola) + `/assistant/check` + disparadores | T-061, T-062 | 2 | 2/2 | ✅ |
| 14 | [`14-cierre-backend-components.md`](14-cierre-backend-components.md) | Verificación transversal BE + `confirm-dialog` + `idea-card` en shared | T-036, T-056 | 2 | 2/2 | ✅ |
| 15 | [`15-e2e-ollama-real.md`](15-e2e-ollama-real.md) | E2E con Ollama real: captura, contingencia, clarificación, validación | T-063, T-064, T-065, T-066 | 4 | 4/4 | ✅ |
| 16 | [`16-accesibilidad-build-cierre.md`](16-accesibilidad-build-cierre.md) | Accesibilidad + build/guías + verificación spec §9 | T-057, T-058, T-068 | 3 | 3/3 | ✅ |
| 17 | [`17-contexto-recursos.md`](17-contexto-recursos.md) | Contexto de empresa administrable + inyección en todos los prompts + retirada de *Recursos estimados* (6 campos, D11) | T-069, T-070, T-071, T-075, T-076 | 5 | 5/5 | ✅ |
| 18 | [`18-debate-evaluacion-catalogo.md`](18-debate-evaluacion-catalogo.md) | Debate (30 días, @asistant, cierre+resumen) + evaluación IA 5 criterios al cerrarse el debate + catálogo compacto con detalle | T-072, T-073, T-074, T-077, T-078 | 5 | 5/5 | ✅ |
| 19 | [`19-decision-final-umbrales.md`](19-decision-final-umbrales.md) | Estados finales + reglas promedio/banda/decisión + umbrales (4/7) + endpoint decisión + reevaluación + cola en dos etapas + notificación calibración + catálogo por zonas (BE) | T-079, T-080, T-081, T-082, T-083 | 5 | 5/5 | ✅ |
| 20 | [`20-frontend-calificacion-zonas.md`](20-frontend-calificacion-zonas.md) | Ficha de calificación + decisión final en vivo + umbrales admin + catálogo 4 zonas + debate compactado + reevaluación + E2E v2.2 (FE) | T-084, T-085, T-086 | 3 | 3/3 | ✅ |

**Total: 4+4+3+2+3+5+5+5+3+4+5+3+2+2+4+3+5+5+5+3 = 75 tareas** (57 del v2.0 + 10 de la ampliación
v2.1 + 8 de la ampliación v2.2). ✓ (una por grupo, sin huecos ni duplicados). **Progreso: 75/75
tareas implementadas** (G01 ✅ … G20 ✅ — todas las ampliaciones de alcance acordadas con el
propietario; 86 tareas en total, T-001..T-086).
**MVP v2.0 cerrado**: `pytest -q` 468 verdes, `ruff check .` limpio, `ng build` verde.

## Criterio de la secuencia

1. **G01–G02 antes:** entregan el shell usable (login, sesión, guards) y el API de usuarios que
   libera toda la UI posterior. G01 además da `T-009` (modelos/badge) que consumen G08, G11.
2. **G04 en paralelo:** el motor IA solo depende del núcleo ya hecho (T-001/002/007); no bloquea
   el path crítico FE mientras se avanzan G02/G03, pero debe cerrarse **antes de G06/T-024 y G08**
   (los únicos que inyectan el cliente real).
3. **G05–G06 (núcleo de la idea):** columnata vertebral: dominio/estados/persistencia y luego
   casos de uso + router. G10 (validación/campana) y G08 (`finish_capture`) consumen T-020/T-021.
4. **G07–G09 (captura):** dominio de conversación → router/UI de arranque → resumen/manual/
   contingencia. Produce las ideas `asistida` que caen en el núcleo (G05/G06).
5. **G10/G12 (ciclo de publicación del especialista + campana):** consume approve/reject (G06) y
   las notificaciones; la UI (G12) lo cierra.
6. **G11 (Mis ideas):** consume todo el backend de ideas/captura/refinamiento y el chat (G08).
7. **G13 (asistente UC + check):** consume G04 (IA), G06 (`improve`/`adjust_in_chat`) y G10
   (notificaciones); alimenta `refine-view` (G11) que lo dispara.
8. **G14 (cierres transversales):** verificación **antes** de G15; `T-036` solo tiene sentido con
   todas las features de backend presentes (G06, G08, G10, G13).
9. **G15/G16 (E2E real + cierre de spec):** último. No añaden producción: ejercitan con Ollama
   real y certifican los 13 criterios del spec §9.

## Riesgos de secuencia

* **G11/T-049 reutiliza `chat-message` de G08** ("ajustar en chat"): G08 debe cerrarse antes.
* **G15/T-063 depende de G13 (T-062)** para el disparador de check en login/capture.
* **T-067 (G03)** es autocontenida (solo G02): puede ejecutarse al terminar G02, antes que el
  resto.
* **G14/T-036** puede detectar bug de integración cross-feature: el fix va al grupo de origen y
  se revalida en G14.
* **G15/G16** no tocan producción: un fallo del smoke apunta a un bug real (G04..G13).

## Reglas operativas (de `tasks.md` y Constitución)

* **BE:** `pytest -q` + `ruff check .` verdes tras cada bloque completo. Solo stdlib (§6.1).
* **FE:** `ng build` verde tras cada feature. Sin tests automatizados (§6.2).
* **Sin acoplar features:** lectura/escritura de ideas solo vía `IdeaLedger` (T-008); emisión de
  notificaciones vía contrato compartido.
* **Idioma:** UI y mensajes en español; identificadores en inglés (RNF-4).
* **No romper lo previo:** cada grupo se construye sobre lo ya hecho (marcado ✓) y su sección
  "Qué no se rompe" lista los contratos reutilizados sin modificar.
* `tasks.md` se mantiene intacto como registro maestro; estos archivos `groups/` son el desdoblamiento.
