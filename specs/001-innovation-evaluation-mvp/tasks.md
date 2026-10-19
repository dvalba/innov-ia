# Tareas de Implementación — Innov-IA MVP

**Documento:** specs/001-innovation-evaluation-mvp/tasks.md
**Depende de:** `specs/001-innovation-evaluation-mvp/spec.md` (v2.1 — ampliación de alcance del propietario), `specs/001-innovation-evaluation-mvp/plan.md` (v1.1) y `docs/CONSTITUTION.md`
**Naturaleza:** Desglose de implementación en tareas atómicas (20–30 min cada una). Una tarea NO se marca como hecha hasta cumplir su criterio "Hecho cuando".

> **Ampliación de alcance (v2.1):** el propietario del producto incorporó al MVP el debate de las
> ideas publicadas (RF-24/RF-25), la evaluación de la IA sobre 5 criterios con criterio del
> especialista (RF-26), el contexto de empresa gestionable (RF-21/RF-22), la eliminación del campo
> *Recursos estimados* (D11), la vista compacta de catálogo + detalle (RF-20/RF-23) y las
> preferencias de presentación (RNF-13). Quedan registradas en la **Fase 5 / G17–G18** (T-069 y
> siguientes).

> **Reglas de ejecución:**
>
> * Cada tarea atómica dura 20–30 min; si una tarea parece mayor, dividirla antes de ejecutarla.
> * Backend: `pytest -q` y `ruff check .` deben pasar tras cada bloque de backend completo. Sin dependencias externas (Constitución §6.1).
> * Frontend: `ng build` debe pasar tras cada feature. Sin suite de pruebas automatizada (Constitución §6.2).
> * Interfaz y mensajes en español; identificadores en inglés (AGENTS.md).
> * No modificar `specs/` salvo solicitud explícita.

**Leyenda de fases:**

| Fase | Contenido |
|------|-----------|
| **1** | Setup / Core (infraestructura de ambos lados) |
| **2** | Backend: FastAPI Clean Architecture (7 features en v2.0; 9 con `org`/`debate` de v2.1) |
| **3** | Frontend: Angular 20+ features (6 features) |
| **4** | Integración Ollama, e2e y cierre |
| **5** | Ampliación de alcance v2.1: contexto de empresa, debate, evaluación IA, catálogo detalle, sin recursos (G17) |

---

## Fase 1 — Setup / Core

### 1.1 Infraestructura base

- [x] **[T-001] Backend: esqueleto FastAPI, estructura por features y config**
  - **Covers:** RF-1..RF-20 (estructura plan §1.2)
  - **Dependencias:** Ninguna
  - **Hecho cuando:** Existe `backend/app/main.py` con la instancia de FastAPI, CORS y registro de routers (huecos por feature); estructura `backend/{app,shared,features/{auth,capture,ideas,assistant,validation,users,notifications}}` con las subcapas `domain/use_cases/infrastructure/routers` y `__init__.py` de cada paquete; `shared/config/settings.py` lee de variables de entorno (`OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT=60`) y expone un objeto `settings` tipado; `ruff check .` pasa.

- [x] **[T-002] Backend: manejo global de excepciones y formato de errores unificado**
  - **Covers:** RF-1, RF-16 (errores), RNF-9
  - **Dependencias:** [T-001]
  - **Hecho cuando:** `shared/exceptions/handlers.py` define `DomainError`, `ValidationFailed`, `AssistantUnavailable`, `AuthError`, `Forbidden` y registra manejadores globales que devuelven el formato `{"error": {"code", "message", "details"}}` con los códigos HTTP del plan §3.5 (400/401/403/409/422/503); test en `tests/api/test_error_format.py`: lanzar cada excepción desde un endpoint de prueba devuelve el código y el formato exactos (`pytest -q` verde).

- [x] **[T-003] Backend: persistencia JSON reutilizable y utilidad de contraseñas (stdlib)**
  - **Covers:** RF-1..RF-20 (plan D1, D10)
  - **Dependencias:** [T-001]
  - **Hecho cuando:** `shared/utils/persistence.py` ofrece un `JsonStore` (lectura/escritura atómica por ruta, con directorio inicial) y `shared/utils/password.py` ofrece `hash_password`/`verify_password` con salt usando solo stdlib (`hashlib`); test en `tests/unit/infra/test_stores.py` y `tests/unit/infra/test_password.py` cubren round-trip, atomeidad (sin archivo parcial tras fallo simulado) y verificación de hash con/ sin salt (`pytest -q` verde).

- [x] **[T-004] Frontend: proyecto Angular 20+ con Tailwind y núcleo de app (config, rutas lazies, layout shell)**
  - **Covers:** RF-1..RF-20 (estructura plan §1.1)
  - **Dependencias:** Ninguna
  - **Hecho cuando:** `frontend/` creado con Angular 20+ (CLI), Tailwind CSS configurado (conforme a `docs/guides/tailwind-guidelines.md`); `src/app/app.routes.ts` define rutas lazy por feature (`/login`, `/captura`, `/mis-ideas`, `/validacion`, `/catalogo`, `/admin`) y `app.config.ts` configura router + `provideHttpClient(withInterceptors(...))`; existe `shared/layouts/main-layout` (sidebar + contenido, conforme a Constitución §3.2) y `ng build` pasa.

- [x] **[T-005] Frontend: interceptores auth y de errores**
  - **Covers:** RF-1 (sesión), RNF-7
  - **Dependencias:** [T-004]
  - **Hecho cuando:** `shared/interceptors/auth.interceptor.ts` inyecta el portador de sesión en toda petición y, ante un 401, limpia la sesión y redirige a `/login`; `shared/interceptors/error.interceptor.ts` normaliza respuestas de error (formato §3.6) y expone el mensaje para mostrar; ambos registrados en `app.config.ts`; `ng build` pasa.

- [x] **[T-006] Frontend: `SessionService` compartido (sesión, usuario, roles)**
  - **Covers:** RF-1, RNF-7
  - **Dependencias:** [T-005]
  - **Hecho cuando:** `shared/services/session.service.ts` expone señales `sesionActiva`, `usuario` (username, nombre, área, contacto) y `roles`, con métodos `iniciar(token, usuario)`, `cerrar()` y `tieneRol(...roles)`; persistencia de la sesión en `localStorage` y recuperación al cargar; `ng build` pasa.

- [x] **[T-007] Backend: fixture base de pruebas (conftest) con stores in-mem y Ollama mock**
  - **Covers:** RF-1..RF-20 (plan §6.4)
  - **Dependencias:** [T-003]
  - **Hecho cuando:** `backend/tests/conftest.py` provee fixtures `app`, `client` (TestClient), stores in-mem inyectados por override de dependencias y un `ollama_mock` configurable (disponible/down, latencia); los stores de archivo no se tocan en tests; `pytest -q` pasa con un test smoke (`GET /health` 200).

### 1.2 Contratos compartidos

- [x] **[T-008] Backend: contrato `shared` para lectura de ideas entre features**
  - **Covers:** RF-3 (asignación), RF-8, RF-11, RF-13 (plan §1.2 nota de acoplamiento)
  - **Dependencias:** [T-001]
  - **Hecho cuando:** En `shared/contracts/` se define el Protocolo `IdeaLedger` (lectura de idea por id, listado por estado/origen, escritura de campos vigentes) tipado y documentado, sin importar `features/`; las features `assistant` y `validation` lo reciben por inyección; `ruff check .` pasa y ningún módulo de `features/assistant` ni `features/validation` importa de otro `features/` (verificado con `ruff` o test de importación en `tests/unit/domain/test_layering.py`).

- [x] **[T-009] Frontend: modelos TS compartidos, utilidades de fecha/estado y badge de estado**
  - **Covers:** RF-2, RF-10 (estados), RNF-2
  - **Dependencias:** [T-004]
  - **Hecho cuando:** `shared/utils/` contiene interfaces TS espejo de los esquemas JSON del plan §2 (`Idea`, `ChatMessage`, `Conversation`, `IdeaVersion`, `Usuario`, `Notificacion`) y utilidades de formato (fechas en español); `shared/components/badge-state` renderiza el estado de una idea con etiqueta y color por estado (EN_DESARROLLO/SOLICITANDO_PUBLICACION/VALIDADA_PUBLICA), operable con teclado; la UI está en español (RNF-4); `ng build` pasa.

---

## Fase 2 — Backend (FastAPI Clean Architecture)

### 2.1 Feature `auth` (RF-1, RF-17 parcial)

- [x] **[T-010] auth · dominio: sesión, validez y roles**
  - **Covers:** RF-1
  - **Dependencias:** [T-007]
  - **Hecho cuando:** `features/auth/domain/session.py` define `Sesion` (token, user_id, expiración) y reglas puras (sesión válida/caducada, roles de un usuario) sin importar FastAPI/Pydantic; test en `tests/unit/domain/test_session.py` cubre validez, caducidad y combinación de roles (`pytest -q` verde).

- [x] **[T-011] auth · infraestructura: token store y seed del primer administrador**
  - **Covers:** RF-1, RF-17 (decisión #6)
  - **Dependencias:** [T-009], [T-010]
  - **Hecho cuando:** `features/auth/infrastructure/token_store.py` implementa emisión/revocación de tokens opacos con `JsonStore`; en la inicialización del sistema se crea el primer administrador definido por variables de entorno (username/contraseña), sin API para crearlo; test en `tests/unit/infra/test_token_store.py` cubre emisión, revocación, caducidad y seed idempotente del primer admin (`pytest -q` verde).

- [x] **[T-012] auth · casos de uso: login/logout/me + cambio forzado de contraseña**
  - **Covers:** RF-1, RF-17 (cambio en primer acceso)
  - **Dependencias:** [T-011]
  - **Hecho cuando:** `features/auth/use_cases/login.py`, `logout.py`, `me.py` y `change_password.py` implementan: verificación de credenciales sin revelar qué dato es incorrecto (mensaje único), emisión/revocación de sesión, datos+roles del usuario, y cambio de contraseña obligatorio en primer acceso (flag `debe_cambiar`); usuario desactivado no puede iniciar sesión; tests en `tests/unit/use_cases/test_auth_flow.py` cubren credenciales válidas/inválidas, desactivado, cambio forzado y logout (`pytest -q` verde).

- [x] **[T-013] auth · router: endpoints /auth con Pydantic y dependencias de sesión**
  - **Covers:** RF-1, RF-17
  - **Dependencias:** [T-012]
  - **Hecho cuando:** `features/auth/routers/auth.py` expone `POST /auth/login` (200 con token+usuario), `POST /auth/logout`, `GET /auth/me`, `POST /auth/change-password` (401 si no es sesión propia; 409 si no está forzado); dependencias `requerir_sesion` y `requerir_rol` reutilizables (en routers shared); test en `tests/api/test_auth.py` cubre 200/401/403 y caso 15 (sesión caducada → 401) (`pytest -q` verde).

### 2.2 Feature `users` (RF-17)

- [x] **[T-014] users · dominio: entidad Usuario y regla "no dejar sin administrador"**
  - **Covers:** RF-17
  - **Dependencias:** [T-007]
  - **Hecho cuando:** `features/users/domain/user.py` define `Usuario` (username único, nombre, área, contacto, hash, roles, habilitado, debe_cambiar) y `role_rules.py` implementa la regla de impedir desactivar/revocar al último administrador; test en `tests/unit/domain/test_role_rules.py` cubre los dos lados de la regla (`pytest -q` verde).

- [x] **[T-015] users · casos de uso: crear, cambiar roles, desactivar/habilitar**
  - **Covers:** RF-17, caso 16
  - **Dependencias:** [T-014]
  - **Hecho cuando:** `create_user.py` emite contraseña temporal válida para primer acceso y la devuelve una sola vez; `assign_roles.py` valida roles conocidos y aplica la regla del último admin; `toggle_active.py` conserva cuenta, ideas e historial al desactivar; `change_password.py` de auth (T-012) reutiliza aquí la verificación de contraseña actual; tests en `tests/unit/use_cases/test_users_roles.py` cubren creación con temporal, asignación/revocación y caso 16 (historial intacto) (`pytest -q` verde).

- [x] **[T-016] users · router: endpoints /users con segregación por rol**
  - **Covers:** RF-17, RNF-7
  - **Dependencias:** [T-015], [T-013]
  - **Hecho cuando:** `features/users/routers/users.py` expone `GET/POST /users`, `PUT /users/{id}/roles`, `PATCH /users/{id}/active`, todos con dependencia de rol administrador (403 si no es admin); `POST /users` devuelve la contraseña temporal en la respuesta 201; test en `tests/api/test_users_api.py` cubre 201 con temporal, 403 para no-admin, 409 al desactivar el último admin (`pytest -q` verde).

### 2.3 Feature `ideas` (entidad central; RF-9, RF-10, RF-19, RF-20 + máquina de estados)

- [x] **[T-017] ideas · dominio: entidad Idea y validación de campos (RNF-5, caso 12)**
  - **Covers:** RF-9, RF-19, RNF-5
  - **Dependencias:** [T-007]
  - **Hecho cuando:** `features/ideas/domain/idea.py` define `Idea` con los 7 campos, `ownerId`, `origin`, `state`, `reviewedByAI`, `currentVersionId` y timestamps/rastro, conforme al esquema §2.2; `validate.py` implementa `campos_completos` (ninguno vacío u omitido) y validación de formato del contacto (no-vacío + formato correo/teléfono); test en `tests/unit/domain/test_idea_validation.py` cubre campos completos/parciales y contacto inválido (caso 12) (`pytest -q` verde).

- [x] **[T-018] ideas · dominio: máquina de estados (RNF-9)**
  - **Covers:** RF-10, RF-15, RF-16, RNF-9
  - **Dependencias:** [T-017]
  - **Hecho cuando:** `state_machine.py` implementa la tabla de transiciones exacta del plan §4.6 (EN_DESARROLLO→SOLICITANDO_PUBLICACION solo por request-publication; SOLICITANDO→VALIDADA PUBLICA por approve; SOLICITANDO→EN_DESARROLLO por reject; VALIDADA_PUBLICA terminal) y lanza `DomainError` ante transición no permitida; test en `tests/unit/domain/test_state_machine.py` cubre todas las transiciones válidas y cada transición inválida (`pytest -q` verde).

- [x] **[T-019] ideas · infraestructura: idea_store (persistence JSON + IdeaVersion)**
  - **Covers:** RF-8, RF-9, RF-10, RF-19 (D1)
  - **Dependencias:** [T-018], [T-003]
  - **Hecho cuando:** `infrastructure/idea_store.py` persiste `Idea` e `IdeaVersion` (esquema §2.5) con `JsonStore`, con obtención por id con bloqueo de registro parcial (caso 17: si falla el guardado, no queda estado intermedio); expone operaciones usadas por el resto de features vía el contrato `IdeaLedger` (T-008); test en `tests/unit/infra/test_idea_store.py` cubre guardado, carga, listado por estado y fallo sin registro parcial (`pytest -q` verde).

- [x] **[T-020] ideas · casos de uso: crear y editar idea (bloqueo durante generación)**
  - **Covers:** RF-9, RNF-5
  - **Dependencias:** [T-019]
  - **Hecho cuando:** `create_idea.py` crea la idea con los 7 campos obligatorios + origen + ownerId (rechaza con `ValidationFailed` si faltan campos); `edit_idea.py` permite editar cualquier campo mientras la idea esté en EN_DESARROLLO y en el dueño, y lanza `DomainError` (409) si existe generación en curso (flag `generando`); tests en `tests/unit/use_cases/test_edit_idea.py` cubren edición válida, edición bloqueada durante generación y edición por no-duéño (`pytest -q` verde).

- [x] **[T-021] ideas · casos de uso: solicitud de publicación, aprobación y rechazo**
  - **Covers:** RF-10, RF-15, RF-16, RNF-8
  - **Dependencias:** [T-020], [T-008]
  - **Hecho cuando:** `request_publication.py` transiciona a SOLICITANDO_PUBLICACION (única vía, fija `requestDate`); `approve_idea.py` valida permiso de especialista (o autovalidación, caso 9), transiciona a VALIDADA_PUBLICA, registra `publishedBy`/`publishedAt`, emite notificación IDEA_PUBLISHED al proponente e IDEA_REQUESTED a todos los especialistas en la transición de solicitud; `reject_idea.py` exige comentario no vacío (400 sin él, caso 13), devuelve a EN_DESARROLLO, adjunta el comentario con la identidad del emisor y notifica IDEA_REJECTED; tests en `tests/unit/use_cases/test_publication.py` cubren los tres flujos, autovalidación con rastro, rechazo sin comentario y transición doble (RNF-9: la segunda descarta con 409) (`pytest -q` verde).

- [x] **[T-022] ideas · casos de uso: listado de "mis ideas" y catálogo público**
  - **Covers:** RF-19, RF-20
  - **Dependencias:** [T-021]
  - **Hecho cuando:** `list_my_ideas.py` devuelve solo las ideas del usuario (título, fecha, origen, estado) y `list_public.py` devuelve SOLO `VALIDADA_PUBLICA` (cualquier dueño) sin el campo `contact` del proponente; test en `tests/unit/use_cases/test_listings.py` verifica el filtro por dueño, el filtro de estado y la supresión de datos de contacto (`pytest -q` verde).

- [x] **[T-023] ideas · router: endpoints /ideas (detalle, edición, mejora-solicitud, decisión de versión, solicitud de publicación)**
  - **Covers:** RF-8, RF-9, RF-10, RF-19
  - **Dependencias:** [T-022]
  - **Hecho cuando:** `features/ideas/routers/ideas.py` expone `POST /ideas` (201; 422 con campos faltantes), `GET /ideas/me`, `GET /ideas/{id}` (403 si no es el dueño), `PUT /ideas/{id}` (409 si está generando), `POST /ideas/{id}/improve`, `POST /ideas/{id}/versions/{vid}/decide` (aceptar/descartar), `POST /ideas/{id}/request-publication`; esquemas Pydantic solo en esta capa; tests en `tests/api/test_ideas_api.py` cubren 201/422/403/409 y la decisión aceptar/descartar con cambio de `currentVersionId` al aceptar (`pytest -q` verde).

- [x] **[T-024] ideas · mejora asistida y ajuste en chat: orquestación y versión pendiente (RF-8, RF-13)**
  - **Covers:** RF-8, RF-13
  - **Dependencias:** [T-023], [T-008]
  - **Hecho cuando:** `improve_idea.py` genera (vía cliente de asistente inyectado) una `IdeaVersion` PENDIENTE con `requestedBy=improvement`, marca `reviewedByAI=true` y bloquea edición (T-020); si el asistente no está disponible, guarda la solicitud pendiente y devuelve aviso (caso 10); `decide` con "aceptar" aplica la versión como vigente manteniendo EN_DESARROLLO, con "descartar" conserva la vigente; `adjust_in_chat` (conversión) expone el contrato para reabrir conversación precontextualizada sobre la idea (no captura nueva, RF-2); si en el ajuste la IA no está, se ofrece edición manual; tests en `tests/unit/use_cases/test_refinement.py` (bloque RF-8/RF-13) cubren mejora con/ sin IA, decisión, y ajuste sin IA → edición manual (`pytest -q` verde).

### 2.4 Feature `capture` (RF-2..RF-7)

- [x] **[T-025] capture · dominio: conversación y reglas de captura (orden fijo, opciones por turno, aclaración)**
  - **Covers:** RF-2, RF-3, RF-5
  - **Dependencias:** [T-007]
  - **Hecho cuando:** `domain/conversation.py` define `Conversation` (esquema §2.4: estado ACTIVA/RESUMEN/TERMINADA/CONTINGENCIA, campos capturados, campo en curso, orden, opciones ofrecidas en el turno) y `capture_rules.py` fija el orden exacto de RF-3, los campos elegibles para opciones rápidas (D7 sustituida: son IA por turno, no un catálogo fijo) y las reglas: una conversación ACTIVA por usuario, chip = respuesta completa solo si fue ofrecido en el turno, `needsClarification` cuando la respuesta es insuficiente (sin avanzar); test en `tests/unit/domain/test_capture_rules.py` cubre orden, campos elegibles/compactables, salto de campos ya capturados, aclaración y límite de 1 conversación activa (`pytest -q` verde).

- [x] **[T-026] capture · infraestructura: conversation_store**
  - **Covers:** RF-2, RF-7, RNF-10
  - **Dependencias:** [T-025], [T-003]
  - **Hecho cuando:** `infrastructure/conversation_store.py` persiste `Conversation` con `JsonStore` ofreciendo: obtener la conversación ACTIVA del usuario, crear, actualizar campos capturados (sin perder los existentes), marcar CONTINGENCIA/TERMINADA; test en `tests/unit/infra/test_conversation_store.py` verifica recuperación de campos parciales tras relectura (RNF-10) (`pytest -q` verde).

- [x] **[T-027] capture · casos de uso: iniciar/retomar conversación**
  - **Covers:** RF-2, RF-7 (caso 1)
  - **Dependencias:** [T-026], [T-008]
  - **Hecho cuando:** `start_conversation.py`: si hay conversación ACTIVA la retoma (no crea segunda, RF-2/caso 8); si el asistente está disponible inicia con saludo + primera pregunta (campo 1: descripción) sin chips (las opciones rápidas las genera la IA por turno a partir del primer mensaje, D7 sustituida); si NO está disponible devuelve señal de formulario manual vacío; tests en `tests/unit/use_cases/test_capture_flow.py` (bloque inicio) cubren retoma, inicio y contingencia al iniciar (`pytest -q` verde).

- [x] **[T-028] capture · casos de uso: procesamiento de mensaje (narrativa multi-campo, siguiente pregunta, aclaración)**
  - **Covers:** RF-3, RF-5
  - **Dependencias:** [T-027]
  - **Hecho cuando:** `process_message.py` aplica el texto o la opción rápida (chip) seleccionada al campo en curso — un chip es válido solo si está entre las `quickOptions` ofrecidas en el turno (D7 sustituida); la misma llamada IA del turno genera las opciones del siguiente campo elegible y compacta campos libres; usa el extractor para asignar fragmentos narrativos a uno o varios campos (cada fragmento asignado marca su campo y no se vuelve a preguntar), pide aclaración si la respuesta es insuficiente y avanza al siguiente campo incompleto; al completar los 7 pasa la conversación a RESUMEN; tests cubren: narrativa que completa varios campos a la vez, opción rápida ofrecida como respuesta completa, chip no ofrecido → 400, aclaración por respuesta insuficiente, y salto sin repetir campos (`pytest -q` verde).

- [x] **[T-029] capture · casos de uso: título sugerido (propuesta, alternativa, manual)**
  - **Covers:** RF-4
  - **Dependencias:** [T-028]
  - **Hecho cuando:** `suggest_title.py`: tras la primera respuesta sustantiva propone título con acciones `accept/another/manual`; "another" genera una sugerencia distinta de las anteriores (lista de intentos persistente en la conversación); el texto escrito manualmente se guarda sin modificación; tests cubren propuesta inicial, alternativa distinta y aceptación de texto manual (`pytest -q` verde).

- [x] **[T-030] capture · casos de uso: finalización (resumen confirmado → idea asistida) y activación manual prellenada**
  - **Covers:** RF-6, RF-7 (caso 2), RNF-5, RNF-10
  - **Dependencias:** [T-029], [T-020]
  - **Hecho cuando:** `finish_capture.py` valida los 7 campos completos (RNF-5) desde el resumen confirmado, registra la idea EN_DESARROLLO con origen `asistida` y termina la conversación (sin borrador: nada si no se confirma, caso 7); `activate_manual.py` marca la conversación en CONTINGENCIA y devuelve los `capturedFields` para prellenar el formulario manual sin pérdida; tests cubren finalización completa, finalización con campo faltante (rechazo), y activación manual con campos parciales conservados (`pytest -q` verde).

- [x] **[T-031] capture · router: endpoints /capture (start, messages, finish, activate-manual, assistant-status)**
  - **Covers:** RF-2, RF-3, RF-4, RF-5, RF-6, RF-7
  - **Dependencias:** [T-030], [T-013]
  - **Hecho cuando:** `features/capture/routers/capture.py` expone `POST /capture/start`, `POST /capture/messages` (200 con asistente/siguiente pregunta; 503 con `{error: {code: ASSISTANT_UNAVAILABLE}, fallback: {capturedFields}}` si la IA cae a mitad), `POST /capture/finish` (201 idea), `POST /capture/activate-manual`, `GET /capture/assistant-status` (OK/UNAVAILABLE); dependencia de rol proponente; tests en `tests/api/test_capture_api.py` cubren el flujo completo de chat (inicio → mensajes → resumen → finish 201) y el fallback 503 prellenado (casos 1, 2) (`pytest -q` verde).

### 2.5 Feature `notifications` (RF-12, RF-15, RF-16, RF-18)

- [x] **[T-032] notifications · dominio + infraestructura: entidad, tipos de evento y store**
  - **Covers:** RF-18
  - **Dependencias:** [T-003]
  - **Hecho cuando:** `domain/notification.py` define `Notificacion` (esquema §2.7) con SOLO los 4 tipos `IDEA_REFINED, IDEA_PUBLISHED, IDEA_REJECTED, IDEA_REQUESTED`; `infrastructure/notification_store.py` persiste con `JsonStore` (por usuario, leída/no leída); test en `tests/unit/infra/test_notification_store.py` cubra creación, listado por usuario y contador no leídas (`pytest -q` verde).

- [x] **[T-033] notifications · casos de uso + router: crear, listar, marcar leída, fanout a especialistas**
  - **Covers:** RF-12, RF-15, RF-16, RF-18
  - **Dependencias:** [T-032], [T-021]
  - **Hecho cuando:** `create_notification.py` crea notificación al proponente (con `ideaId` para acceso directo) en los 3 eventos del proponente (refinada, publicada, rechazada) y hace fanout de `IDEA_REQUESTED` a **todos** los usuarios con rol especialista; `list_notifications.py` devuelve lista + contador de no leídas; `mark_read.py` marca leída; `routers/notifications.py` expone `GET /notifications` y `POST /notifications/{id}/read` (solo el destinatario); se registran los puntos de emisión de RF-12/RF-15/RF-16 desde lasfeatures `ideas`/`assistant` vía contrato compartido; tests en `tests/api/test_notifications_api.py` cubren los 4 y solo los 4 eventos, fanout, contador y marcar leída (`pytest -q` verde).

### 2.6 Feature `validation` (RF-14, RF-15, RF-16)

- [x] **[T-034] validation · dominio + casos de uso + router: cola del especialista**
  - **Covers:** RF-14, RF-15, RF-16
  - **Dependencias:** [T-021], [T-033], [T-013]
  - **Hecho cuando:** `domain/queue_rules.py` define la visibilidad de la cola (solo SOLICITANDO_PUBLICACION; proponente solo nombre y área, SIN datos de contacto); `use_cases/review_queue.py` lista la cola con 7 campos, proponente (nombre/área) y fecha de solicitud; `routers/validation.py` expone `GET /validation/queue`, `POST /validation/{id}/approve` (reutiliza `approve_idea`), `POST /validation/{id}/reject` (reutiliza `reject_idea`; 400 sin comentario); rol especialista (403 si no); tests en `tests/api/test_validation_api.py` cubren contenido de cola sin contacto, aprobación con rastro y notificaciones, rechazo con/sin comentario (caso 13) (`pytest -q` verde).

- [x] **[T-035] validation/ideas · catálogo público: endpoint /catalog/public**
  - **Covers:** RF-20, RNF-7
  - **Dependencias:** [T-022]
  - **Hecho cuando:** `GET /catalog/public` (registrado en `routers/catalog.py` o en `ideas`) requiere solo sesión activa (cualquier rol) y devuelve las ideas `VALIDADA_PUBLICA` con 7 campos, nombre/área del proponente, fecha de registro y de publicación; sin `contact`; test en `tests/api/test_catalog_api.py` verifica que solo aparezca VALIDADA_PUBLICA, la ausencia de contacto y el 401 sin sesión (`pytest -q` verde).

### 2.7 Cierre de backend

- [x] **[T-036] Backend: verificación transversal — pytest completo, ruff y arranque**
  - **Covers:** RF-1..RF-20 (verificación)
  - **Dependencias:** [T-031..T-035]
  - **Hecho cuando:** `pytest -q` pasa al completo sin errores ni saltos; `ruff check .` está limpio; `uvicorn app.main:app` arranca y `GET /health` responde 200; todos los endpoints del plan §3.1 existen y responden según sus contratos (verificado con un test de humo por endpoint en `tests/api/test_endpoints_present.py`).

---

## Fase 3 — Frontend (Angular 20+ por features)

### 3.1 Feature `auth`

- [x] **[T-037] auth · AuthService + página de login**
  - **Covers:** RF-1
  - **Dependencias:** [T-006], [T-013]
  - **Hecho cuando:** `features/auth/services/auth.service.ts` llama a `POST /auth/login` (HttpClient en el servicio) y, en éxito, almacena la sesión vía `SessionService`; la página `features/auth/pages/login` muestra formulario usuario/contraseña con mensajes en español, notifica el fallo sin indicar qué dato es incorrecto y redirige al layout principal en éxito; operable con teclado; `ng build` pasa.

- [x] **[T-038] auth · cierre de sesión + guarda de usuario y cambio forzado de contraseña**
  - **Covers:** RF-1, RF-17 (primer acceso)
  - **Dependencias:** [T-037]
  - **Hecho cuando:** El sidebar del layout expone el nombre de usuario y el botón "Cerrar sesión" (llama a `POST /auth/logout` y devuelve a login); si el usuario trae `debeCambiarContraseña`, al iniciar se muestra un diálogo para llamar a `POST /auth/change-password` antes de cualquier otra acción; `ng build` pasa.

- [x] **[T-039] auth · guard de rutas por sesión y rol**
  - **Covers:** RF-1, RNF-7
  - **Dependencias:** [T-038]
  - **Hecho cuando:** `app.routes.ts` aplica `canActivate` a las rutas protegidas: `/login` bloqueado si hay sesión activa; las rutas por rol (`/validacion` → especialista, `/admin` → administrador, `/captura` y `/mis-ideas` → proponente) redirigen a la página de inicio del layout si el rol no corresponde; sin sesión activa solo se muestra login (RF-1); `ng build` pasa.

### 3.2 Feature `capture`

- [x] **[T-040] capture · `fieldsMeta` (orden fijo + preguntas) y `CaptureService` base**
  - **Covers:** RF-3, RF-5, RNF-4
  - **Dependencias:** [T-009], [T-031]
  - **Hecho cuando:** `features/capture/services/fieldsMeta.ts` define el orden fijo de los 7 campos y la pregunta en español por campo (las opciones rápidas ya no son un catálogo cliente: las ofrece el backend por turno, D7 sustituida); `capture.service.ts` envuelve `POST /capture/start`, `POST /capture/messages`, `GET /capture/assistant-status` con manejo de estado de carga (RNF-3); `ng build` pasa.

- [x] **[T-041] capture · página new-idea (decisión asistida vs manual)**
  - **Covers:** RF-2, RF-7 (caso 1)
  - **Dependencias:** [T-040]
  - **Hecho cuando:** `pages/new-idea` consulta `GET /capture/assistant-status`: si OK abre la conversación asistida; si UNAVAILABLE despliega directamente el formulario manual con aviso claro de contingencia; si el backend informa conversación ACTIVA existente ofrece "Retomar conversación" (caso 8, RF-2); `ng build` pasa.

- [x] **[T-042] capture · componente chat (mensajes, chips y sugerencia de título)**
  - **Covers:** RF-5, RF-4
  - **Dependencias:** [T-041]
  - **Hecho cuando:** `pages/chat-assist` renderiza la burbuja de mensajes (`components/chat-message`, papeles usuario/asistente), la lista de opciones rápidas que llega en la respuesta del turno (`quickOptions`, IA generadas por campo, D7 sustituida; selección = respuesta completa, se muestran solo en el turno vigente) y el bloque `components/title-suggestion` con acciones Aceptar / Pedir otra / Escribir (el texto escrito se envía sin modificación); acceso a `POST /capture/messages` con `quickOptionSelected` o texto libre; carga visible durante cada llamada a la IA (RNF-3); `ng build` pasa.

- [x] **[T-043] capture · resumen editable y confirmación de la idea asistida**
  - **Covers:** RF-6, RNF-5
  - **Dependencias:** [T-042]
  - **Hecho cuando:** Al llegar `state: RESUMEN`, `components/field-summary` muestra los 7 campos editables con los valores capturados; el botón "Confirmar" llama a `POST /capture/finish` con el resumen (editado o no) y, con 201, navega a "Mis ideas" mostrando el nuevo estado; si el backend rechaza (campos incompletos), muestra los errores y permanece en el resumen; `ng build` pasa.

- [x] **[T-044] capture · formulario manual (7 campos obligatorios, prellenado, envío)**
  - **Covers:** RF-7, RNF-5
  - **Dependencias:** [T-041], [T-043]
  - **Hecho cuando:** `pages/manual-form` + `components/manual-fields` presentan los 7 campos obligatorios (Proponente prellenado desde la cuenta y corregible), validan no-vacio y formato de contacto (caso 12) antes de habilitar el envío, y envían a `POST /ideas` con origen `manual`; aceptan `prellenado` de ruta (campos ya capturados) tras un 503 de contingencia; en fallo de envío los datos permanecen en pantalla (caso 17); `ng build` pasa.

- [x] **[T-045] capture · contingencia a mitad de conversación (503 → prellenado)**
  - **Covers:** RF-7 (caso 2), RNF-10, RNF-3
  - **Dependencias:** [T-042], [T-044]
  - **Hecho cuando:** Si `POST /capture/messages` devuelve 503 `ASSISTANT_UNAVAILABLE`, el chat muestra un aviso de interrupción y ofrece "Continuar en formulario manual", pasando `fallback.capturedFields` al formulario manual prellenado; los campos capturados no se pierden; si el 503 llega en el reinicio, se reenvía la misma solicitud una vez (reintento único, RNF-3) antes de contingencia; `ng build` pasa.

### 3.3 Feature `my-ideas`

- [x] **[T-046] my-ideas · listado "Mis ideas"**
  - **Covers:** RF-19
  - **Dependencias:** [T-039], [T-023]
  - **Hecho cuando:** `features/my-ideas/pages/list` muestra las ideas del usuario (título, fecha de registro, origen, estado con `badge-state`) vía `httpResource` (`GET /ideas/me`), ordenadas por fecha, y permite abrir cualquiera; estado vacío con mensaje en español; `ng build` pasa.

- [x] **[T-047] my-ideas · detalle con acciones según estado + edición manual**
  - **Covers:** RF-9, RF-10
  - **Dependencias:** [T-046]
  - **Hecho cuando:** `pages/detail` muestra los 7 campos, origen/estado/`reviewedByAI` (RNF-2) y, si la idea está en EN_DESARROLLO: formulario de edición de cualquier campo (PUT, con bloqueo visual con aviso mientras el backend informa generación en curso) y botón "Solicitar publicación" (disponible aunque la idea no haya sido vista por la IA); en SOLICITANDO_PUBLICACION muestra la fecha de solicitud y no permite edición; `ng build` pasa.

- [x] **[T-048] my-ideas · mejoras solicitadas a la IA (instrucción, versión pendiente, decisión)**
  - **Covers:** RF-8
  - **Dependencias:** [T-047]
  - **Hecho cuando:** El detalle ofrece "Solicitar mejora a la IA" con campo de instrucción (envía a `POST /ideas/{id}/improve`); si la IA no está disponible muestra el aviso de solicitud registrada (caso 10); las versiones PENDIENTE se listan con los campos propuestos y botones "Aceptar versión" / "Descartar" (decisión única por versión); al aceptar, la versión pasa a ser la vigente y la idea sigue en EN_DESARROLLO; `ng build` pasa.

- [x] **[T-049] my-ideas · refinamiento de ideas manuales: versión refinada vs original + ajustar en chat**
  - **Covers:** RF-11, RF-12, RF-13
  - **Dependencias:** [T-048], [T-042]
  - **Hecho cuando:** `components/refine-view` muestra la versión refinada diferenciada de la original (campo por campo) con botones "Aceptar la versión" / "Ajustar detalles en el chat"; al aceptar (decision endpoint) la idea sigue EN_DESARROLLO; al ajustar, se abre la conversación asistida precontextualizada sobre la idea (no nueva captura) y, si la IA no está disponible, ofrece la edición manual; al abrir una idea manual pendiente la app dispara `POST /assistant/check`; `ng build` pasa.

- [x] **[T-050] my-ideas · nota de rechazo visible**
  - **Covers:** RF-16
  - **Dependencias:** [T-047]
  - **Hecho cuando:** `components/reject-note` muestra, cuando la idea fue rechazada, el comentario del especialista con su identidad y la fecha, en el detalle de la idea y accesible desde la notificación; `ng build` pasa.

### 3.4 Feature `validation`

- [x] **[T-051] validation · cola + panel validar/rechazar**
  - **Covers:** RF-14, RF-15, RF-16
  - **Dependencias:** [T-039], [T-034]
  - **Hecho cuando:** `features/validation/pages/queue` lista la cola (7 campos, proponente solo nombre/área, fecha de solicitud) vía `httpResource`; `components/validate-panel` permite "Validar" (POST approve) y "Rechazar" con campo de comentario obligatorio (botón bloqueado sin comentario, caso 13); los estados se refrescan tras la acción y se muestra confirmación en español; `ng build` pasa.

### 3.5 Feature `catalog`

- [x] **[T-052] catalog · página de catálogo público (solo lectura)**
  - **Covers:** RF-20
  - **Dependencias:** [T-039], [T-035]
  - **Hecho cuando:** `features/catalog/pages/public` muestra las ideas VALIDADA_PUBLICA (7 campos, nombre/área del proponente, fecha de registro y de publicación) vía `httpResource`, sin datos de contacto y sin botones de edición (solo lectura); accesible para todo usuario con sesión; `ng build` pasa.

### 3.6 Feature `admin`

- [x] **[T-053] admin · panel de usuarios (crear, desactivar, roles)**
  - **Covers:** RF-17
  - **Dependencias:** [T-039], [T-016]
  - **Hecho cuando:** `features/admin/pages/users` lista los usuarios (nombre, área, roles, estado); `components/user-form` crea usuarios (username, nombre, área, contacto) y, tras 201, muestra la contraseña temporal una única vez para entregarla; permite desactivar/habilitar usuario; al intentar desactivar el último administrador muestra el error del backend (409) sin aplicar el cambio; `ng build` pasa.

- [x] **[T-054] admin · matriz de roles (asignar/revocar)**
  - **Covers:** RF-17
  - **Dependencias:** [T-053]
  - **Hecho cuando:** `components/role-matrix` permite asignar/revocar uno o varios roles (proponente, especialista, administrador) por usuario (PUT /users/{id}/roles), refleja el estado actual y bloquea la UI según el error del backend (último admin); usuarios sin roles se marcan como "sin acceso a funciones"; `ng build` pasa.

### 3.7 Componentes transversales

- [x] **[T-055] shared · campana de notificaciones (contador, lista, navegar, marcar leída)**
  - **Covers:** RF-18, RF-12
  - **Dependencias:** [T-006], [T-033]
  - **Hecho cuando:** `shared/components/notification-bell` (en el layout) muestra contador de no leídas (polling `GET /notifications`), lista las notificaciones con mensaje en español y fecha, navega al objeto indicado por `ideaId` (detalle de idea) y marca leída al consultar el objeto (POST read); sin notificaciones fuera de la app; `ng build` pasa.

- [x] **[T-056] shared · diálogo de confirmación reutilizable + idea-card compartido**
  - **Covers:** RF-2, RF-19, RF-14 (reutilización)
  - **Dependencias:** [T-046], [T-051], [T-052]
  - **Hecho cuando:** `shared/components/confirm-dialog` (usado p. ej. en "Solicitar publicación" y en el abandono de captura con aviso de pérdida, caso 7) está en `shared/` y es operable con teclado (RNF-6); `idea-card` se promueve a `shared/components/` (Constitución §3.2) y se usa en `my-ideas`, `validation` y `catalog` sinimportaciones cruzadas entre features; `ng build` pasa.

- [x] **[T-057] Frontend: accesibilidad transversal (teclado y lectores de pantalla)**
  - **Covers:** RNF-6, RNF-4
  - **Dependencias:** [T-042], [T-044], [T-055]
  - **Hecho cuando:** Chat, chips, formularios, notificaciones y catálogos son operables con solo teclado (orden de foco lógico, `aria-expanded`/`aria-live` donde corresponde, etiquetas para inputs, roles ARIA en el diálogo); toda la UI está en español (RNF-4); verificado recorriendo cada feature con navegación por teclado sin herramienta de automatización (criterio manual documentado en la tarea); `ng build` pasa.

- [x] **[T-058] Frontend: build final y verificación de cumplimiento de guías**
  - **Covers:** RF-1..RF-20 (verificación)
  - **Dependencias:** [T-037..T-057]
  - **Hecho cuando:** `ng build` pasa sin errores; la estructura de carpetas coincide con el plan §1.1 (6 features + shared); no hay `*ngIf`/`*ngFor`/`@Input`/`@Output` (busqueda de patrones vacía), se usa `inject()`, `httpResource` en lecturas y `input()/output()/signal()`; nomenclatura sin sufijo `Component`; ningún componente de feature importa de otra feature; las rutas lazy están activas.

---

## Fase 4 — Integración Ollama / E2E y Cierre

- [ ] **[T-059] assistant · cliente Ollama nativo (stdlib) con timeout 60 s y reintento único**
  - **Covers:** RNF-3, caso 14
  - **Dependencias:** [T-001]
  - **Hecho cuando:** `features/assistant/infrastructure/ollama_client.py` implementa con `urllib`/`http.client` (D2): `ping()` para disponibilidad, `generate(prompt)` para generación, con timeout configurable (default 60 s, RNF-3) y reintento único transparente ante timeout/error; define "fallo de IA" = sin respuesta en el tiempo límite, error del servicio, o respuesta no interpretable (caso 14) y lanza `AssistantUnavailable`; test en `tests/unit/infra/test_ollama_client.py` con servidor HTTP simulado cubre: ping OK, timeout con reintento único, error de servicio → contingencia (`pytest -q` verde).

- [ ] **[T-060] assistant · dominio: prompts y reglas de refinamiento**
  - **Covers:** RF-3 (asignación), RF-4, RF-11
  - **Dependencias:** [T-059]
  - **Hecho cuando:** `domain/prompts.py` contiene las plantillas de prompts en español: extracción de campos de narrativa libre (RF-3), sugerencia de título con lista de intentos a evitar (RF-4), refinamiento de idea manual (7 campos), mejora bajo instrucción (RF-8); `domain/refinement.py` define la cola: ideas EN_DESARROLLO con origen manual y sin versión refinada válida, ordenadas de más antigua a más reciente, y la interpretación de la respuesta de la IA (valida los 7 campos; si no es interpretable se trata como fallo); tests en `tests/unit/domain/test_refinement.py` cubren el filtro de cola, el orden y la interpretación inválida → fallo (`pytest -q` verde).

- [x] **[T-061] assistant · casos de uso: disponibilidad, sugerencia de título, mejora, refinamiento, cola**
  - **Covers:** RF-4, RF-8, RF-11, RF-12
  - **Dependencias:** [T-060], [T-024], [T-033]
  - **Hecho cuando:** `check_availability.py` (ping + reintento), `suggest_title.py` (integra IA; alimenta a `capture` vía contrato), `improve_idea.py` (genera versión pendiente; si la IA no está, guarda solicitud pendiente para la siguiente verificación — caso 10), `refine_manual.py` (genera versión con `requestedBy=refinement` + notificación IDEA_REFINED al proponente, RF-12), `run_refinement_queue.py` (procesa toda la cola de más antigua a más reciente; si un item falla, lo conservado se queda y lo fallido sigue pendiente — caso 6; el refinamiento conservado se queda y las ideas siguen operando — RF-11); tests en `tests/unit/use_cases/test_refinement.py` cubren cola completa, fallo parcial, mejora sin IA (solicitud pendiente) y disparadores (`pytest -q` verde).

- [x] **[T-062] assistant · router: /assistant/check con disparadores bajo demanda**
  - **Covers:** RF-11
  - **Dependencias:** [T-061], [T-013]
  - **Hecho cuando:** `POST /assistant/check` requiere rol proponente y: verifica disponibilidad; si está disponible procesa la cola (más antigua → más reciente) y devuelve el resultado (nº de ideas refinadas, fallos); se invoca internamente también al iniciar sesión (login — T-013), al iniciar captura (`/capture/start` — T-031) y al solicitar mejora (T-024), según decisión #4; los disparadores internos no bloquean la respuesta principal (resultado disponible en la cola/notificaciones); tests en `tests/api/test_assistant_api.py` cubren la invocación directa, la integración con login/capture e idempotencia (`pytest -q` verde).

- [x] **[T-063] Integración: captura asistida e2e con Ollama real (mock en tests, real en smoke)**
  - **Covers:** RF-2..RF-6, RF-4
  - **Dependencias:** [T-062], [T-043]
  - **Hecho cuando:** Con Ollama corriendo (settings reales, no mock), el flujo completo desde la UI: nueva idea → conversación (orden fijo, opciones rápidas generadas por turno D7, título sugerido con Aceptar/Otra/Escribir) → resumen editable → confirmación → idea EN_DESARROLLO origen `asistida` visible en "Mis ideas"; los tests de API que usan `ollama_mock` simulan las respuestas de generación de forma determinista (`pytest -q` verde); el smoke manual queda registrado con capturas/pasos en la tarea.

- [x] **[T-064] Integración: contingencia e2e (IA caída al inicio y a mitad de conversación)**
  - **Covers:** RF-7, RNF-1, RNF-3, RNF-10, casos 1, 2, 3
  - **Dependencias:** [T-063], [T-045]
  - **Hecho cuando:** Con Ollama detenido: al iniciar captura, la UI muestra directamente el formulario manual con aviso (caso 1); comenzando una conversación y cayendo la IA a mitad, el chat ofrece el formulario prellenado con los campos ya capturados y el registro final crea la idea `manual` (caso 2); el reinicio único (60 s) no expone al usuario (RNF-3); `pytest -q` verde con el mock de caída; smoke manual documentado.

- [x] **[T-065] Integración: clarificación e2e (refinamiento manual, notificación, aceptación/ajuste)**
  - **Covers:** RF-11, RF-12, RF-13, RNF-1, caso 5
  - **Dependencias:** [T-064], [T-049]
  - **Hecho cuando:** Con Ollama detenido, se crea una idea manual; con Ollama recuperado, al iniciar sesión la cola se procesa (de más antigua a más reciente) y se genera notificación de idea refinada con acceso directo; la UI muestra la versión refinada vs original; al aceptar, la versión vigente cambia y la idea sigue EN_DESARROLLO (solo se publica por RF-10+RF-15); "Ajustar detalles" reabre la conversación precontextualizada; el refinamiento no tiene caducidad y la idea siguió operativa durante la indisponibilidad (caso 5); `pytest -q` verde; smoke manual documentado.

- [x] **[T-066] Integración: validación e2e (publicación y rechazo) + notificaciones**
  - **Covers:** RF-10, RF-14, RF-15, RF-16, RF-18, RNF-8, caso 9
  - **Dependencias:** [T-065], [T-051], [T-055]
  - **Hecho cuando:** Proponente solicita publicación (notificación IDEA_REQUESTED a todos los especialistas); especialista valida → VALIDADA_PUBLICA con rastro (quién/cuándo) y notificación al proponente, idea visible en el catálogo; especialista rechaza con comentario → vuelve a EN_DESARROLLO con el comentario visible y notificación al proponente; la autovalidación (proponente que también es especialista) funciona con rastro (caso 9); el contador de la campana refleja cada evento y solo esos; `pytest -q` verde; smoke manual documentado.

- [x] **[T-067] Integración: usuarios/roles e2e (crear, temporal, revocar, último admin)**
  - **Covers:** RF-17, caso 16
  - **Dependencias:** [T-054], [T-016]
  - **Hecho cuando:** El admin crea un usuario (recibe contraseña temporal), el usuario inicia sesión y está obligado a cambiarse la contraseña; el admin revoca roles/desactiva el usuario: pierde el acceso pero sus ideas e historial se conservan; las ideas en SOLICITANDO_PUBLICACION de un usuario desactivado siguen validables por otros especialistas; desactivar/revocar el último administrador está bloqueado en UI y backend (409); `pytest -q` verde; smoke manual documentado.

- [x] **[T-068] Cierre: verificación de criterios de finalización (spec §9) y casos límite**
  - **Covers:** RF-1..RF-20, RNF-1..RNF-10, casos 1,2,5,6,7,13,16,17
  - **Dependencias:** [T-058], [T-063..T-067]
  - **Hecho cuando:** Cada uno de los 13 criterios de finalización del spec §9 se verifica y marca con evidencia: (1) login/logout; (2) captura asistida e2e; (3) captura manual e2e; (4) contingencia prellenada; (5) clarificación completa; (6) mejora aceptada/descartada + edición manual; (7) validación e2e con notificación; (8) usuarios/roles completos; (9) notificaciones (solo 4 eventos, contador, navegación, leyendo); (10) catálogo solo VALIDADA_PUBLICA sin contacto; (11) casos límite 1, 2, 5, 6, 7, 13, 16, 17; (12) `pytest -q` al completo; (13) estructura por features + guías Angular/Tailwind; `ruff check .` limpio.

---

## Fase 5 — Ampliación de alcance v2.1 (G17/G18)

> Pendiente: la v2.1 (decisión del propietario) amplía el alcance. Ejecutar en orden G17 → G18.

### 5.1 G17 — Contexto de empresa y retirada de *Recursos estimados*

- [x] **[T-069] Backend: retirar *Recursos estimados* del dominio de la idea (6 campos)**
  - **Covers:** §1.1 (6 campos), RF-3, RF-6, RF-7, RF-9, D11
  - **Dependencias:** Ninguna
  - **Hecho cuando:** `estimatedResources` desaparece de todo el backend y el frontend (dominio `idea.py`, `validate.py`, schemas de `create_idea`/`edit_idea`, `FIELD_ORDER` de `conversation.py`, `capture_rules.py` (orden + preguntas + chips + saludo "6 datos"), `prompts.py` (FIELD_LABELS + plantillas), `fieldsMeta.ts`, formularios manual/field-summary/new-idea); `grep -rn estimatedResources backend frontend/src` → 0 coincidencias; los tests existentes se actualizan y `pytest -q` y `ng build` pasan; persistencia de ideas antiguas con el campo: el store lo descarta en la lectura (migración silenciosa).

 - [x] **[T-070] Backend: contexto de empresa como documento administrable (plantilla, edición, subida)**
  - **Covers:** RF-21, casos 24, 25
  - **Dependencias:** [T-069]
  - **Hecho cuando:** La feature `org` gestiona un **único documento** con secciones: perfil (name, sector, description, mission, strategicObjectives) + texto libre de guía (vocabulario, línea estratégica, información de referencia). Endpoints (solo admin): `GET /admin/contexto/plantilla` (200, `text/plain`, plantilla descargable con las secciones y ayudas), `GET /admin/contexto` (200, documento vigente o vacío), `PUT /admin/contexto` (200, guarda el documento editado: perfil + texto libre; 400 si el perfil queda vacío), `POST /admin/contexto/subida` (200, reemplaza el documento vigente con el contenido de un archivo de texto; 400 si el texto viene vacío). Se conserva el seed desde `INNOV_ORG_*` (compatibilidad) y la lectura sin sesión `GET /admin/organizacion` puede eliminarse; `pytest -q` verde en `tests/api/test_org_context_api.py`.

- [x] **[T-071] Backend: inyectar el contexto de empresa en TODAS las operaciones de la IA**
  - **Covers:** RF-22, RNF-12, RF-25/RF-26 (premise)
  - **Dependencias:** [T-070]
  - **Hecho cuando:** `prompts.py` recibe un bloque de contexto (perfil + texto libre) en `extract_fields_prompt`, `title_suggestion_prompt`, `refine_idea_prompt`, `improve_idea_prompt` y `turn_options_prompt`; todos los use cases que invocan al motor (captura por turno, sugerencia de título, mejora, refinamiento) cargan el documento vigente del contexto y lo pasan; si el documento está vacío se inyecta el aviso "(sin contexto de empresa definido)"; tests unitarios en `tests/unit/domain/test_prompts.py` verifican que cada plantilla contiene el contexto o el aviso; `pytest -q` verde.

- [x] **[T-075] Frontend: captura y formularios sin *Recursos estimados***
  - **Covers:** §1.1 (6 campos), RF-3, RF-6, RF-7, D11
  - **Dependencias:** [T-069]
  - **Hecho cuando:** El formulario manual (6 campos, sin la sección *Recursos estimados*), el resumen editable del chat, el detalle/edición de "Mis ideas", el resumen manual de contingencia en `new-idea` y el mapeo de etiquetas (`etiquetaCampo`) muestran/exigen solo los 6 campos; la validación de completitud se ajusta (6/6); `ng build` verde; sin texto "Recursos" visible en ninguna vista.

- [x] **[T-076] Frontend: sección de administración de contexto de empresa**
  - **Covers:** RF-21, RNF-12, D13
  - **Dependencias:** [T-070]
  - **Hecho cuando:** En `/admin` (rol administrador) hay una sección **Contexto de empresa**: botón **Descargar plantilla** (GET plantilla, descarga el archivo .txt), formulario de **edición en línea** (campos de perfil: nombre/sector/descripción/misión/objetivos + textarea del texto libre de guía) con guardar (PUT), y **subida de archivo** (input de tipo archivo `.txt`/`.md`; el contenido se envía a `POST /subida` y reemplaza el documento); aviso visible cuando el documento está vacío (caso 24); la navegación la tiene el enlace en MainLayout/admin; `ng build` verde.

### 5.2 G18 — Debate, evaluación IA y catálogo con detalle

- [x] **[T-072] Backend: dominio y persistencia del debate de ideas publicadas**
  - **Covers:** RF-24, RNF-11
  - **Dependencias:** [T-069]
  - **Hecho cuando:** Existe la feature `debate`: dominio `Debate` (ideaId, deadline, closed, summary, audit de cierre/ajustes) y `DebateMessage` (id, ideaId, authorId, authorName, text, linkedMessageId, isAssistant, createdAt); `debate_store` JSON bajo `backend/data/debate.json`; rules: creación del debate al publicarse (deadline = publishedAt + 30 días), cierre automático cuando `now >= deadline` (solo una vez), ajuste de deadline por idea (solo admin; queda auditado: quien/cuándo/antes/después), los mensajes solo se admiten con debate abierto; tests unitarios en `tests/unit/features/debate/` (`pytest -q` verde).

- [x] **[T-073] Backend: router del debate + @asistant + resumen al cierre**
  - **Covers:** RF-24, RF-25, casos 18, 19, 20, 21
  - **Dependencias:** [T-072], [T-071]
  - **Hecho cuando:** Endpoints: `GET /catalog/{ideaId}/debate` (200: mensajes + deadline + cerrado + resumen + autor), `POST /catalog/{ideaId}/debate` (201 mensaje; 409 si el debate está cerrado); detección de `@asistant`: si el texto empieza por `@asistant` y se enlaza un mensaje existente, el sistema responde con un mensaje de `isAssistant` generado por la IA (prompt con contexto de empresa + idea + mensaje enlazado + petición; RNF-3 aplica; si la IA cae, el mensaje queda guardado como no procesado con aviso y se reintenta en la siguiente interacción — caso 20, el debate sigue operando); cierre: la primera lectura tras la fecha límite cierra el debate y, si hay mensajes, genera `summary` (si la IA no está, el cierre sí ocurre y el resumen queda pendiente hasta la siguiente verificación — caso 21); `PUT /admin/ideas/{ideaId}/debate/deadline` (admin: nueva fecha; reabre si es futura; rastro auditado). Tests en `tests/api/test_debate_api.py` (`pytest -q` verde).

- [ ] **[T-074] Backend: evaluación de la IA (5 criterios) al publicar + decisión del especialista**
  - **Covers:** RF-26, RNF-11, RNF-8, caso 22, 23
  - **Dependencias:** [T-071]
  - **Hecho cuando:** Al validar/publicar (UC `approve_idea`), el sistema intenta generar la evaluación: 5 criterios fijos (*claridad del problema*, *factibilidad*, *impacto esperado*, *alineación estratégica*, *grado de innovación*), cada uno con score 1–10 (entero) y justificación breve, autor = "Asistente (IA)" y fecha; si la IA no está disponible la publicación no se bloquea y la evaluación queda `pending` (se genera en la siguiente verificación de disponibilidad; caso 22). El payload de la idea expone `evaluation` (criteria[], author, createdAt, status, decidedBy, decidedAt). Endpoints (rol especialista): `POST /validation/{ideaId}/evaluation/accept` (200, la evaluación de la IA queda como juicio final; 409 si ya había decisión) y `POST /validation/{ideaId}/evaluation` (200, sustituye la evaluación vigente por la del especialista sobre los mismos 5 criterios; 403 sin rol; 422 si faltan criterios/fuera de rango). Tests en `tests/api/test_evaluation_api.py` y unitarios del prompt (`pytest -q` verde).

- [ ] **[T-077] Frontend: catálogo compacto + vista de detalle (resumen, debate, evaluación)**
  - **Covers:** RF-20, RF-23, RF-24, RF-25, RF-26
  - **Dependencias:** [T-075], [T-073], [T-074]
  - **Hecho cuando:** `/catalogo/publico` lista ideas compactas (título, fecha de publicación, descripción, proponente nombre+área) y al pulsar abre `/catalogo/publico/{id}`: vista de detalle con resumen de los 6 campos (solo lectura), el debate (mensajes con autor/fecha, input para publicar, selector de mensaje enlazado, invocación de `@asistant` con estado de carga, indicador de cierre/fecha límite, resumen de la IA cuando existe, y para rol administrador un control inline para ajustar la fecha límite) y la evaluación (los 5 criterios con score y justificación; para rol especialista los botones **Acepto la evaluación de la IA** y **Sustituir con mi evaluación** abren el formulario de los 5 criterios); todo responsive y accesible (teclado/aria, RNF-6); `ng build` verde.

- [ ] **[T-078] E2E e integración: verificación de la ampliación v2.1 (spec §9 10–14 + casos límite)**
  - **Covers:** RF-20..RF-26, RNF-11..RNF-13, casos 18, 20, 22
  - **Dependencias:** [T-072..T-077]
  - **Hecho cuando:** Se verifica y firma cada criterio nuevo del spec §9 (10-14) y los casos límite 18, 20, 22 con evidencia de tests (tests de API integrados del flujo: publicar → debate abierto → mensaje → `@asistant` → cierre por deadline → resumen; evaluación generada → sustituida por especialista; contexto vacío/inyectado), `pytest -q` al completo verde, `ruff check .` limpio y `ng build` verde; el estado de G17/G18 queda firmado en los archivos de grupo.

---

## Matriz de cobertura RF → tareas

| RF | Tareas |
|----|--------|
| RF-1 | T-005, T-006, T-010..T-013, T-037..T-039 |
| RF-2 | T-025, T-027, T-031, T-040, T-041, T-056, T-063 |
| RF-3 | T-008, T-025, T-028, T-031, T-040, T-060, T-063 |
| RF-4 | T-029, T-031, T-042, T-060, T-061, T-063 |
| RF-5 | T-025, T-028, T-031, T-040, T-042, T-063 |
| RF-6 | T-030, T-031, T-043, T-063 |
| RF-7 | T-026, T-027, T-030, T-031, T-041, T-044, T-045, T-064 |
| RF-8 | T-020, T-023, T-024, T-048, T-061, T-065 |
| RF-9 | T-017, T-020, T-023, T-047, T-065 |
| RF-10 | T-018, T-021, T-023, T-047, T-066 |
| RF-11 | T-024, T-060, T-061, T-062, T-049, T-065 |
| RF-12 | T-033, T-061, T-055, T-065 |
| RF-13 | T-024, T-049, T-065 |
| RF-14 | T-034, T-051, T-066 |
| RF-15 | T-021, T-033, T-034, T-051, T-066 |
| RF-16 | T-021, T-033, T-034, T-050, T-051, T-066 |
| RF-17 | T-011, T-012, T-014..T-016, T-038, T-053, T-054, T-067 |
| RF-18 | T-032, T-033, T-055, T-066 |
| RF-19 | T-022, T-023, T-046, T-047 |
| RF-20 | T-022, T-035, T-052, T-068, T-077 |
| RF-21 | T-070, T-076 |
| RF-22 | T-071, T-076 |
| RF-23 | T-077 |
| RF-24 | T-072, T-073, T-077, T-078 |
| RF-25 | T-071, T-073, T-077, T-078 |
| RF-26 | T-071, T-074, T-077, T-078 |

**Cobertura:** los 26 RF (RF-1..RF-26) están cubiertos (RF-21..RF-26 son v2.1). **Total de tareas:** 78 (68 del MVP v2.0 + 10 de la ampliación v2.1: T-069..T-078).
