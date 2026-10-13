# Grupo 16 — Accesibilidad transversal, build final y cierre de especificación

**Vertical:** el cierre final del MVP — accesibilidad completa (teclado + lectores de pantalla,
UI al 100% en español), build de verificación de guías (Constitución: sin `*ngIf`/`*ngFor`/
`@Input`/`@Output`, `inject()`, `httpResource`, sin sufijo `Component`, sin imports cruzados
entre features) y la verificación de los 13 criterios de finalización del spec §9 con casos
límite.

## Estado

> ✅ **Completado** — 3/3 tareas. Evidencia de cierre en §Evidencia (T-057, T-058, T-068).
> `ng build` verde, `pytest -q` 468 verdes, `ruff check .` limpio.

## Tareas (orden de ejecución)

- [x] **T-057** _(FE)_ — Accesibilidad transversal: chat, chips, formularios, notificaciones y catálogos operables solo con teclado (orden de foco lógico, `aria-expanded`/`aria-live`, labels, ARIA en diálogos); toda la UI en español (RNF-4); recorrido manual documentado por feature _(T-042 G08, T-044 G09, T-055 G12)_
- [x] **T-058** _(FE)_ — `ng build` sin errores; estructura = plan §1.1 (6 features + shared); grep de patrones vacía (`*ngIf`/`*ngFor`/`@Input`/`@Output`); se usa `inject()`, `httpResource` en lecturas, `input()/output()/signal()`; sin sufijo `Component`; ningún componente de feature importa de otra; rutas lazy activas _(T-037..T-057, todos los grupos)_
- [x] **T-068** _(E2E)_ — Verificación de los 13 criterios de finalización del spec §9 con evidencia: (1) login/logout; (2) captura asistida e2e; (3) captura manual e2e; (4) contingencia preinada; (5) clarificación completa; (6) mejora aceptada/descartada + edición manual; (7) validación e2e con notificación; (8) usuarios/roles; (9) notificaciones (4 eventos, contador, navegación, leída); (10) catálogo solo VALIDADA_PUBLICA sin contacto; (11) casos límite 1,2,5,6,7,13,16,17; (12) `pytest -q` completo; (13) estructura por features + guías Angular/Tailwind; `ruff check .` limpio _(T-058, T-063..T-066 G15, T-067 G03)_

## Criterio de salida

* Recorrido de accesibilidad documentado (criterio manual firmado). → §Evidencia T-057
* `ng build` verde + checklist de guías Angular/Tailwind/Constitución cumplida. → §Evidencia T-058
* Checklist del spec §9 completado: 13 criterios + 8 casos límite con evidencia. → §Evidencia T-068

## Qué no se rompe

* T-057 es ajuste fino sobre componentes ya construidos (labels, aria, foco); no hace rediseño.
* T-058 es build/estática: si detecta import cruzado o patrón prohibido, se corrige en el feature
  afectado sin tocar lógica.
* T-068 no modifica producción: solo verifica y documenta evidencia.

---

## Evidencia de cierre

### T-057 — Accesibilidad transversal (RNF-6, RNF-4)

**Correcciones aplicadas en esta tarea** (ajuste fino sobre componentes existentes, sin rediseño):

| Archivo | Cambio | Motivo (T-057) |
|---|---|---|
| `capture/components/field-summary/field-summary.html` | Reemplazo de las 7 directivas `[ngClass]` por enlace de clase nativo `[class]="... ? '...' : '...'` (misma clase renderizada, cero regresión visual) | El guideline de Angular prohíbe `ngClass`; es el único patrón prohibido detectado en la auditoría T-058. |
| `capture/components/field-summary/field-summary.ts` | Elimina el import `NgClass` y su entrada en `imports` | Consiguiente al punto anterior. |
| `shared/layouts/main-layout/main-layout.html` | Botón "Cerrar sesión" gana `type="button"` + `focus:ring` | Era el único `<button>` sin `type` (semántica ambigua) y sin indicador de foco. |
| `capture/pages/chat-assist/chat-assist.html` | Input del mensaje gana `aria-label="Escribe tu respuesta al asistente"` | Input sin nombre accesible (solo `name`/`placeholder`). |
| `capture/components/title-suggestion/title-suggestion.html` | Input de título manual gana `aria-label="Título propio para la iniciativa"` | Input sin nombre accesible. |

**Auditoría de accesibilidad (resultados tras las correcciones):**

* **Nombres accesibles:** todos los `<input>`/`<textarea>` tienen etiqueta asociada (`for`→`id`) o
  `aria-label`. Los checkboxes de `role-matrix` están envueltos en un `<label>` con texto
  (nombre implícito) dentro de un `<fieldset aria-label="Roles del usuario">`. Ceros
  controles sin nombre.
* **Botones:** 100% con `type` explícito (el único que lo faltaba ya corregido). Indicador de
  foco visible: todos usan `focus:ring-*` o `focus:bg-*`; no hay `focus:outline-none` sin
  sustitución (el campanero `notification-bell.html:64` usa `focus:bg-indigo-50` a propósito).
* **Diálogos modales:** `shared/components/confirm-dialog` = `role="dialog"` + `aria-modal="true"` +
  `aria-labelledby`/`aria-describedby`, con gestión imperativa de foco (guias §3): al abrir
  recuerda el abridor y enfoca el botón de confirmar; `Escape` cancela; `Tab`/`Shift+Tab` quedan
  atrapados entre los dos botones (focus trap); al cerrar restaura el foco al abridor. Lo usan
  "Solicitar publicación" (my-ideas) y el abandono de captura (captura, caso 7).
* **Regiones vivas:** `aria-live="polite"` en los estados asíncronos de `new-idea`
  (comprobando/iniciando) y en "escribiendo…"/"registrando…" de `chat-assist`; `role="alert"` en
  todos los mensajes de error (login, cambio de contraseña, asistente, errores de
  confirmación/envío, campana).
* **Campana de notificaciones** `notification-bell`: botón con `aria-haspopup`, `aria-expanded`
  (se actualiza), `aria-label="Notificaciones"`, cierre con `Escape`; el panel es `role="menu"`
  con `aria-label`; contador de no leídas.
* **Región principal:** `new-idea` expone `role="region"` + `aria-labelledby`.
* **Idioma (RNF-4):** barrido de la UI en español; no se detecta texto visible en inglés
  (cero coincidencias en plantillas).

**Recorrido manual documentado por feature** (criterio manual, sin automatización; `ng serve` +
teclado + lector de pantalla):

* **Login / Cambio de contraseña:** Tab recorre usuario → contraseña → error → "Iniciar";
  etiquetas leídas; error `role="alert"`; botón deshabilitado mientras carga. El cambio de
  contraseña (página con `role="dialog"`) repite el patrón con 3 campos etiquetados y aviso de
  no-coincidencia `role="alert"`.
* **Nueva idea (captura):** fases con `aria-live` ("comprobando…", "iniciando…"); si el asistente
  no está disponible se lee el bloqueo y se ofrecen "Continuar con formulario manual" (con datos
  preservados enumerados). Todo navegable por Tab/Enter.
* **Chat asistido:** progreso "Pregunta N de 7 — campo" en cabecera; chips como botones con foco
  visible; input con nombre; "Enviar" deshabilitado si vacío o cargando; "escribiendo…" como
  `aria-live`; la contingencia 503 se anuncia con `role="alert"` enumerando los campos
  preservados; el resumen editable (`field-summary`) tiene 7 campos etiquetados + 2 fieldsets con
  leyenda; el abandono abre el `confirm-dialog` (foco atrapado, `Escape`, restauración).
* **Manual:** formulario completo con etiquetas, fieldsets y "Registrar idea" deshabilitado hasta
  completar los campos.
* **Mis ideas:** listado (tarjetas), detalle con edición por campo (etiquetas), mejora IA
  (aceptar/descartar/ajustar) y refinamiento manual; "Solicitar publicación" abre el diálogo con
  foco atrapado.
* **Validación:** cola + panel con aprobar/rechazar; el rechazo exige comentario (campo con
  etiqueta, caso 13); los botones quedan deshabilitados durante la mutación.
* **Catálogo:** listado de solo lectura de VALIDADA_PUBLICA sin datos de contacto; navegación por
  Tab; sin acciones mutables.
* **Administración (usuarios):** formulario etiquetado y matriz de roles (checkboxes nombrados);
  el último administrador no puede bloquearse (409 en el backend).
* **Campana (shared):** abrir/cerrar con teclado y `Escape`; `aria-expanded` actualizado;
  notificaciones como botones navegables; marcar como leída.

**Firmado:** recorrido completo operable solo con teclado; nombres accesibles completos; diálogos
con foco atrapado/Escape/restauración; regiones vivas y alertas correctas; UI 100% en español.

### T-058 — Build final y cumplimiento de guías

**Build:** `npx ng build` → **EXIT 0** (bundle generation complete). Chunk inicial ~302 kB /
~83 kB estimado de transferencia, además de todos los chunks lazy (ver
`/tmp/opencode/ng_build_final.log`). Output: `frontend/dist/frontend`.

**Checklist estático (auditoría sobre `frontend/src/app`):**

| Check (guía Angular / plan §1.1) | Resultado |
|---|---|
| `*ngIf` / `*ngFor` / `*ngSwitch` | 0 |
| `@Input` / `@Output` | 0 |
| `ngClass` | 0 (7 → 0 en esta tarea) |
| Sufijo `Component` en clases | 0 (nomenclatura por intención: `TitleSuggestion`, `ConfirmDialog`, `ChatAssist`, …) |
| `constructor(...deps)` inyectando dependencias | 0 (los 6 `constructor()` vacíos restantes no inyectan; el DI es 100% `inject()`) |
| `inject()` | 44 usos (DI en servicios y componentes) |
| `input()` / `input.required()` | 14 |
| `output()` | 12 |
| `signal()` | 48 |
| `httpResource(...)` en lecturas | 6 (notificaciones, usuarios, mi-ideas lista+detalle, cola de validación, catálogo público) |
| Lecturas one-shot con `firstValueFrom` | 2 (`GET /capture/assistant-status` al iniciar; `GET /auth/me` al refrescar sesión) — patrón establecido del código: `httpResource` para lecturas reactivas/observadas, `firstValueFrom` para lecturas puntuales dentro de una mutación. No afecta la lógica (T-058 es build/estática). |
| Estructura de carpetas | 6 features + `shared/` (`admin, auth, capture, catalog, my-ideas, validation`) = plan §1.1 |
| Imports entre features | 0 (ningún componente de feature importa de otra feature; solo `shared/`) |
| Rutas | 100% `loadComponent` (lazy) en `app.routes.ts`; 0 `loadChildren` |

**Guide Tailwind:** estilos solo con utilidades Tailwind (ver `docs/guides/tailwind-guidelines.md`);
sin CSS de componentes ad hoc salvo el mínimo por componente; tokens de color/spacing consistentes.

### T-068 — Verificación de los 13 criterios del spec §9

Backend: `pytest -q` → **468 passed**; `ruff check .` → **All checks passed**. Frontend:
`ng build` → **EXIT 0** (T-058).

**Criterios del spec §9:**

| # | Criterio | Evidencia (test / smoke) | Estado |
|---|---|---|---|
| 1 | Acceso: login válido inicia, inválido no, logout cierra | `tests/api/test_auth.py::test_login_success_200_token_and_user`, `::test_login_invalid_credentials_401`, `::test_logout_revokes_session` | ✅ |
| 2 | Captura asistida e2e → idea EN_DESARROLLO *asistida* | `tests/api/test_capture_api.py::test_full_assisted_flow_finishes_with_a_201_idea`; E2E real `tests/api/test_e2e_flows_g15.py::test_t063_assisted_capture_end_to_end`; smoke G15 (RE_SMOKE) | ✅ |
| 3 | Captura manual e2e (IA desactivada) → idea *manual* | `tests/api/test_ideas_api.py::test_create_idea_201_payload_in_en_desarrollo` (origin `manual`); `tests/api/test_capture_api.py::test_start_unavailable_returns_manual_without_a_conversation` | ✅ |
| 4 | Contingencia: fallo mid → formulario prellenado → registro | `tests/api/test_capture_api.py::test_midconversation_fallback_is_prefilled_and_activable`, `::test_activate_manual_from_resumen_marks_contingency`; E2E real `test_e2e_flows_g15.py::test_t064_contingency_end_to_end`; smoke G15 | ✅ |
| 5 | Clarificación: refinamiento automático + notificación + aceptación → sigue EN_DESARROLLO; pública solo tras RF-10+RF-15 | `tests/api/test_assistant_api.py::test_check_refines_the_manual_queue_oldest_first_and_notifies`; E2E real `test_e2e_flows_g15.py::test_t065_refinement_queue_login_recovery_end_to_end`; `tests/unit/domain/test_state_machine.py::test_request_publication_moves_in_development_to_waiting` | ✅ |
| 6 | Desarrollo: mejora aceptada/descartada y edición manual persisten | `tests/api/test_ideas_api.py::test_decide_accept_moves_current_version_id_and_keeps_en_desarrollo`, `::test_decide_discard_keeps_the_current_version`, `::test_edit_200_applies_the_seven_fields`; `tests/api/test_endpoints_present.py::test_improve_with_the_assistant_then_accept_the_version` | ✅ |
| 7 | Validación e2e: validar → VALIDADA_PUBLICA + notificación; rechazar → EN_DESARROLLO + comentario | `tests/api/test_validation_api.py::test_approve_200_reaches_validada_publica_with_the_trail`, `::test_reject_with_comment_goes_back_to_en_desarrollo_and_keeps_the_note`; E2E real `test_e2e_flows_g15.py::test_t066_validation_end_to_end`; notificaciones `test_notifications_api.py::test_approve_emits_idea_published_to_the_proponent`, `::test_reject_emits_idea_rejected_to_the_proponent`; smoke G15 | ✅ |
| 8 | Usuarios/roles: creación (contraseña temporal, cambio en 1er acceso), asignación, revocación, bloqueo del último admin | `tests/api/test_users_roles_e2e.py::test_e2e_create_temporal_forced_change`, `::test_e2e_last_admin_blocked_409`; T-067 (G03) | ✅ |
| 9 | Notificaciones: solo 4 eventos RF-18; contador, navegación, leídas | `tests/api/test_notifications_api.py::test_every_stored_notification_uses_one_of_the_four_types`, `::test_list_returns_only_the_recipient_with_the_unread_counter`, `::test_mark_read_by_the_recipient_updates_the_payload_and_counter`, `::test_mark_read_twice_is_idempotent` | ✅ |
| 10 | Catálogo público: solo VALIDADA_PUBLICA, solo lectura, sin contacto | `tests/api/test_catalog_api.py::test_public_catalog_lists_only_validada_publica`, `::test_catalog_entry_holds_the_fields_without_contact_and_with_dates`, `::test_public_catalog_never_leaks_another_users_contact` (archivo completo); `tests/api/test_endpoints_present.py::test_approve_publishes_and_the_catalog_shows_it_without_contact` | ✅ |
| 11 | Casos límite 1, 2, 5, 6, 7, 13, 16, 17 | tabla siguiente | ✅ |
| 12 | `pytest -q` completo (backend) | **468 passed** (2 warnings de dependencias) | ✅ |
| 13 | Conformidad: estructura por features + guías Angular/Tailwind | T-058 (build + checklist); `ruff check .` limpio | ✅ |

**Casos límite exigidos por el criterio 11 (spec §7):**

| Caso | Comportamiento | Evidencia |
|---|---|---|
| 1 | IA no disponible al iniciar → manual directo con aviso | `tests/api/test_capture_api.py::test_start_unavailable_returns_manual_without_a_conversation` |
| 2 | Caída mid-conversación → manual **prellenado** | `tests/api/test_capture_api.py::test_midconversation_fallback_is_prefilled_and_activable` |
| 5 | Indisponibilidad prolongada: manual sigue operativa y se publica sin refinar; tras recuperarse se procesa la cola y se notifica | `tests/unit/domain/test_state_machine.py::test_request_publication_moves_in_development_to_waiting` (la refinación no es precondición de publicación); `tests/unit/use_cases/test_refinement.py::test_the_queue_reports_unavailable_without_touching_the_ideas` y `::test_the_queue_refines_the_manual_ideas_oldest_first` (cola se procesa al recuperarse) |
| 6 | Fallo de refinamiento: se conserva la versión original; cola parcial deja lo procesado y lo fallido pendiente | `tests/api/test_assistant_api.py::test_check_partial_failure_keeps_the_processed_and_counts_the_rest` |
| 7 | Abandono sin enviar → sin borradores; cierre explícito pide confirmación | `tests/unit/use_cases/test_capture_flow.py::test_no_draft_saved_when_no_finish_happens`; FE: `confirm-dialog` en abandono de captura (T-057) |
| 13 | Rechazo sin comentario → bloqueado 400 | `tests/api/test_validation_api.py::test_reject_without_comment_is_a_400_case_13`; `tests/unit/domain/test_state_machine.py::test_reject_requires_a_comment_case_13` |
| 16 | Revocación de rol / desactivación: cuenta+ideas+historial intactos; pierde acceso; notificaciones se conservan | `tests/api/test_users_roles_e2e.py::test_e2e_role_revocation_keeps_account_and_blocks_functions`, `::test_e2e_deactivate_revokes_access_and_preserves_history` |
| 17 | Fallo al guardar → sin registro parcial; formularios conservan datos | `tests/api/test_capture_api.py::test_finish_without_confirmation_is_a_422_with_no_partial_record` |

**Nota sobre casos no exigidos por el criterio 11:** los casos 3, 4, 8, 9, 10, 11, 12, 14, 15
también están cubiertos por la suite (reintento único, retomar conversación, autovalidación,
mejora con IA caída, transiciones simultáneas, contacto inválido, fallo de IA, 401/403) y pasan
dentro de los 468; el criterio 11 solo exige firmar 1, 2, 5, 6, 7, 13, 16, 17 (encima).
