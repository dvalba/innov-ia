# Plan de Implementación Técnico — Innov-IA MVP

**Documento:** specs/001-innovation-evaluation-mvp/plan.md
**Versión:** 1.3
**Depende de:** `specs/001-innovation-evaluation-mvp/spec.md` (v2.4, definitiva) y `docs/CONSTITUTION.md`
**Naturaleza:** Este documento es un plan técnico (arquitectura, contratos y pseudocódigo). No contiene código de implementación y no modifica contratos sin actualizar antes la especificación, conforme a la inmutabilidad de contratos (Constitución §5.2).

Cada sección incluye una **Trazabilidad RF** que asigna explícitamente los requisitos funcionales (RF-1 … RF-29) que cubre.

> **v1.1 (ampliación v2.1):** Incorpora RF-21…RF-26 —contexto de empresa administrable (RF-21) inyectado en
> todas las operaciones de la IA (RF-22), vista de detalle de la idea publicada (RF-23), debate de 30 días con
> `@asistant` (RF-24, RF-25) y evaluación de la IA sobre 5 criterios con aceptación/sustitución del
> especialista (RF-26)—, retira *Recursos estimados* del modelo de la idea (6 campos, decisión 11 de la spec)
> y actualiza secciones 1–7. Los debates y las evaluaciones son **atributos de la idea VALIDADA_PUBLICA, no
> estados** (decisión 12 de la spec).
>
> **v1.2 (ampliación v2.2):** Incorpora RF-27…RF-29 —decisión final de la calificación del especialista con
> promedio y umbrales configurables (RF-27/RF-28), estados finales `ACEPTADA`/`ARCHIVADA`/`RECHAZADA` como
> salidas reales de la máquina, reevaluación de ideas `ARCHIVADA` (RF-29), cola de validación en **dos etapas**
> (publicación y calificación, RF-14), y catálogo por **4 zonas** (RF-20)—. La idea vuelve a la cola de
> calificación al cerrarse el debate y generarse la evaluación de la IA (RF-27); el resultado final debe
> **coincidir** con la banda del promedio (409 si no, RF-27/RF-28, caso 27) y el motivo es obligatorio para
> archivar/rechazar (RF-27, caso 28). Los umbrales (defecto 4/7) son un documento único administrado
> (RF-28, RNF-8, caso 31).
>
> **v1.3 (ampliación v2.4):** Sustituye el ajuste de fecha límite **idea por idea** del debate por una
> **configuración global administrable de días de debate** (entero 1–90, defecto 30, auditada RNF-11):
> `GET/PUT /admin/debate-days`; el deadline de un debate se fija al abrirlo con el valor vigente y **no se
> recomputa** (los debates existentes conservan su fecha almacenada, sin migración). Se retiran
> `PUT /admin/ideas/{ideaId}/debate/deadline`, el use case `adjust_deadline`, el esquema `DebateDeadlineRequest`
> y el rastro `Debate.adjustments` (v2.4, D23).

---

## 1. Estructura de módulos y carpetas

Organización técnica exacta según la Clean Architecture por características (Constitución §§ 3 y 4). Se identifican **seis features frontend** y **nueve features backend** que cubren el alcance de la spec.

### 1.1 Frontend (`innov-ia/frontend/`)

```text
frontend/src/
├── index.html
├── main.ts
├── app/
│   ├── app.routes.ts            # Rutas de la aplicación (lazy por feature)
│   ├── app.config.ts            # provideHttpClient(withInterceptors(...)), router, etc.
│   │
│   ├── shared/
│   │   ├── components/
│   │   │   ├── notification-bell/    # Campana de notificaciones (transversal a features)
│   │   │   ├── badge-state/          # Insignia de estado de idea (transversal)
│   │   │   └── confirm-dialog/       # Diálogo de confirmación reutilizable
│   │   ├── layouts/
│   │   │   └── main-layout/          # Sidebar + Main Content (Constitución §3.2)
│   │   ├── interceptors/
│   │   │   ├── auth.interceptor.ts   # Inyecta portador de sesión; 401 → login
│   │   │   └── error.interceptor.ts  # Normaliza errores HTTP
│   │   ├── services/
│   │   │   └── session.service.ts    # Sesión activa (signal), usuario, roles
│   │   └── utils/
│   │
│   └── features/
│       ├── auth/
│       │   ├── pages/
│       │   │   └── login/            # Pantalla de inicio/cierre de sesión
│       │   └── services/
│       │       └── auth.service.ts
│       │
│       ├── capture/                  # Asistente conversacional + contingencia manual + desarrollo
│       │   ├── pages/
│       │   │   ├── new-idea/         # Punto de entrada a una captura
│       │   │   ├── chat-assist/      # Conversación asistida (opciones rápidas del turno, título sugerido)
│       │   │   └── manual-form/      # Formulario manual (independiente de la IA)
│       │   ├── components/
│       │   │   ├── chat-message/     # Burbuja de mensajero (usuario/IA); las opciones rápidas
│       │   │   │                     # del turno (D7) se renderizan inline en chat-assist a
│       │   │   │                     # partir de quickOptions (no hay componente chips/)
│       │   │   ├── title-suggestion/ # Aceptar/Otro/Escribir (RF-4)
│       │   │   ├── field-summary/    # Resumen editable de los 6 campos (RF-6)
│       │   │   └── manual-fields/    # 6 campos obligatorios
│       │   └── services/
│       │       ├── capture.service.ts  # Orquestación client-side de la conversación
│       │       └── fields-meta.ts      # Orden fijo + pregunta por campo (chips por turno, D7)
│       │
│       ├── my-ideas/
│       │   ├── pages/
│       │   │   ├── list/             # "Mis ideas": título, fecha, origen, estado (incluye finales)
│       │   │   └── detail/           # Detalle + acciones según estado (solicitar reevaluación de ARCHIVADA, RF-29)
│       │   ├── components/
│       │   │   ├── idea-card/        # Carta reutilizada también en cola de validación
│       │   │   ├── refine-view/      # Versión refinada vs original + Aceptar/Ajustar
│       │   │   └── reject-note/      # Comentario/motivo del especialista (solo si aplica)
│       │   └── services/
│       │       └── my-ideas.service.ts
│       │
│       ├── validation/
│       │   ├── pages/
│       │   │   └── queue/            # Cola de validación en dos etapas (publicación / calificación, RF-14)
│       │   ├── components/
│       │   │   ├── validate-panel/   # Etapa publicación: Validar / Rechazar + comentario obligatorio
│       │   │   ├── calibration-panel/# Etapa calificación (v2.2): ficha completa (RF-23) + calificación
│       │   │   │                     # vigente (IA o sustituta) + promedio y banda EN VIVO +
│       │   │   │                     # formulario de decisión final (RF-27/RF-28) con confirmación
│       │   │   └── idea-card (usar shared si se comparte)  # ver 1.4
│       │   └── services/
│       │       └── validation.service.ts
│       │
│       ├── catalog/
│       │   ├── pages/
│       │   │   ├── public/           # Catálogo COMPACTO POR ZONAS (RF-20, v2.2): pestañas
│       │   │   │                     # En proceso / Aceptadas / Rechazadas / Archivadas
│       │   │   └── detail/           # Vista de detalle (RF-23): 6 campos, debate (RF-24/RF-25)
│       │   │                         # y evaluación (RF-26); estado final + decisión (RF-27);
│       │   │                         # solo lectura de la idea
│       │   ├── components/
│       │   │   ├── debate/           # Hilo de mensajes, input, selector de mensaje enlazado,
│       │   │   │                     # @asistant, cierre/fecha límite, resumen IA (RF-24/RF-25);
│       │   │   │                     # debate CERRADO compactado (resumen + enlace al chat
│       │   │   │                     # completo, solo lectura)
│       │   │   └── evaluation/       # 5 criterios con score + justificación; promedio/banda;
│       │   │                         # aceptar/sustituir para rol especialista (RF-26); decisión
│       │   │                         # final visible (RF-27)
│       │   └── services/
│       │       └── catalog.service.ts
│       │
│       └── admin/
│           ├── pages/
│           │   ├── users/            # Gestión de usuarios y roles
│           │   ├── context/          # Contexto de empresa (RF-21): plantilla, edición en línea, subida
│           │   ├── thresholds/       # Umbrales de calificación (RF-28, v2.2): umbralRechazo/umbralAceptación
│           │   └── debate-days/      # Días de debate (RF-24, v2.4): configuración global 1–90, defecto 30
│           ├── components/
│           │   ├── user-form/        # Alta / edición de usuario
│           │   ├── role-matrix/      # Asignación/revocación de roles
│           │   ├── context-form/     # Secciones del documento: perfil + guía de la IA
│           │   └── threshold-form/   # Los dos umbrales enteros 1–10 + validación rechazo < aceptación
│           └── services/
│               └── admin.service.ts
```

**Trazabilidad RF — Estructura frontend**

| Carpeta | RF cubiertas |
|---|---|
| `features/auth` + `shared/interceptors` | RF-1 |
| `features/capture` (chat-assist) | RF-2, RF-3, RF-4, RF-5, RF-6 |
| `features/capture` (manual-form) | RF-7 |
| `features/my-ideas` (detail) | RF-8, RF-9, RF-10, RF-12, RF-13, RF-19, RF-29 (reevaluación) |
| `features/validation` | RF-14 (dos etapas), RF-15, RF-16, RF-27, RF-28 (decisión final) |
| `features/catalog` (public por zonas) | RF-20 |
| `features/catalog` (detail: debate + evaluación + decisión) | RF-23, RF-24, RF-25, RF-26, RF-27 |
| `features/admin` (users) | RF-17 |
| `features/admin` (contexto de empresa) | RF-21, RF-22 |
| `features/admin` (umbrales) | RF-28 |
| `shared/components/notification-bell` + `shared/services/session` | RF-18, RF-1 (sesión) |

### 1.2 Backend (`innov-ia/backend/`)

```text
backend/
├── app/  (punto de entrada uvicorn: `app.main:app`)
│   └── main.py                       # Instancia FastAPI, registra routers, CORS, excepciones
│
├── shared/
│   ├── config/
│   │   └── settings.py               # Variables de entorno (Ollama URL, modelo, timeouts)
│   ├── exceptions/
│   │   └── handlers.py               # Manejadores globales (ver §3.7)
│   └── utils/
│       ├── persistence.py            # Abstracción mínima sobre almacenamiento JSON por ruta
│       └── password.py               # Derivación de contraseña (stdlib) — ver §5
│
└── features/
    ├── auth/
    │   ├── domain/
    │   │   └── session.py            # Sesión, validez, roles
    │   ├── use_cases/
    │   │   ├── login.py              # Verifica credenciales, emite sesión
    │   │   └── logout.py
    │   ├── routers/
    │   │   └── auth.py
    │   └── infrastructure/
    │       └── token_store.py        # Almacén de sesiones
    │
    ├── capture/                     # Estado de conversaciones de captura + registro de ideas
    │   ├── domain/
    │   │   ├── conversation.py       # Modelo de conversación + campos capturados
    │   │   └── capture_rules.py      # Orden fijo, preguntas por campo, campos con opciones (D7)
    │   ├── use_cases/
    │   │   ├── start_conversation.py # Inicia/retoma conversación (límite 1 activa, RF-2)
    │   │   ├── process_message.py    # Aplica respuesta → campos, decide siguiente pregunta
    │   │   ├── finish_capture.py     # Registra idea EN_DESARROLLO (RF-6, RF-7)
    │   │   └── activate_manual.py    # Convierte conversación en formulario prellenado (RF-7)
    │   ├── routers/
    │   │   └── capture.py
    │   └── infrastructure/
    │       └── conversation_store.py
    │
    ├── ideas/                       # Entidad central Idea + su ciclo de vida
    │   ├── domain/
    │   │   ├── idea.py               # Entidad Idea (6 campos, origen, estado, atributos)
    │   │   ├── state_machine.py      # Transiciones EN_DESARROLLO→…→VALIDADA_PUBLICA
    │   │   └── validate.py           # Reglas de 6 campos completos, contacto válido
    │   ├── use_cases/
    │   │   ├── create_idea.py        # Creación desde captura (asistida o manual)
    │   │   ├── edit_idea.py          # Edición manual (RF-9) + bloqueo durante generación
    │   │   ├── request_publication.py# Transición única a SOLICITANDO_PUBLICACIÓN (RF-10)
    │   │   ├── approve_idea.py       # VALIDADA_PUBLICA + rastro + notificación (RF-15)
    │   │   │                         # + apertura del debate (30 d, RF-24) + evaluación IA
    │   │   │                         # (RF-26; pendiente si la IA cae)
    │   │   ├── reject_idea.py        # Devolución + comentario obligatorio (RF-16)
    │   │   ├── list_my_ideas.py      # (RF-19)
    │   │   ├── list_public.py        # (RF-20, compacto D16, por zona en v2.2)
    │   │   └── reevaluate_idea.py    # ARCHIVADA → VALIDADA_PUBLICA; limpia decision (RF-29)
    │   ├── routers/
    │   │   ├── ideas.py
    │   │   └── catalog.py            # Catálogo por zonas + detalle (RF-20, RF-23);
    │   │                             # POST /ideas/{id}/request-reevaluation (RF-29)
    │   └── infrastructure/
    │       └── idea_store.py
    │
    ├── assistant/                   # Integración con el asistente de IA
    │   ├── domain/
    │   │   ├── prompts.py            # Plantillas de prompts (dominio puro)
    │   │   └── refinement.py         # Reglas de cola, definición de fallo (caso 14)
    │   ├── use_cases/
    │   │   ├── suggest_title.py      # Generación/sugerencia alternativa (RF-4)
    │   │   ├── refine_manual.py      # Refinamiento de idea manual (RF-11)
    │   │   ├── improve_idea.py       # Mejora bajo instrucción (RF-8)
    │   │   ├── check_availability.py # Verificación bajo demanda
    │   │   └── run_refinement_queue.py # Procesa cola de más antigua a más reciente
    │   ├── routers/
    │   │   └── assistant.py
    │   └── infrastructure/
    │       └── ollama_client.py      # Cliente nativo (urllib) — ver §5
    │
    ├── validation/                  # Cola del especialista y decisión
    │   ├── domain/
    │   │   ├── queue_rules.py        # Visibilidad de cola por ETAPA (publicación/calibración, RF-14 v2.2)
    │   │   ├── evaluation_rules.py   # 5 criterios fijos, decisión única del especialista (RF-26)
    │   │   └── decision_rules.py     # Promedio, banda vs umbrales, motivo obligatorio (RF-27/RF-28)
    │   ├── use_cases/
    │   │   ├── review_queue.py       # Lista por etapa: SOLICITANDO_PUBLICACIÓN / calificación (v2.2)
    │   │   ├── accept_ai_evaluation.py  # La evaluación IA queda como juicio final (RF-26)
    │   │   ├── replace_evaluation.py    # Sustitución por la del especialista (RF-26)
    │   │   ├── decide_final.py         # Decisión final: valida banda/motivo, escribe decision (RF-27/RF-28)
    │   │   └── admin_thresholds.py     # GET/PUT umbrales (RF-28, RNF-8)
    │   ├── routers/
    │   │   └── validation.py         # + POST /validation/{id}/decision (RF-27)
    │   └── infrastructure/
    │       ├── queue_store.py
    │       └── threshold_store.py    # Documento único de umbrales (JSON, defecto 4/7)
    │
    ├── org/                         # Contexto de empresa (documento único administrable, RF-21)
    │   ├── domain/
    │   │   └── company_context.py    # Documento: perfil (secciones fijas) + texto de guía (libre)
    │   ├── use_cases/
    │   │   ├── get_context.py        # Documento vigente o vacío (caso 24)
    │   │   ├── update_context.py     # Edición en línea (PUT)
    │   │   ├── upload_context.py     # Subida de archivo: reemplazo total (RF-21)
    │   │   └── context_template.py   # Plantilla de texto con las secciones orientativas
    │   ├── routers/
    │   │   └── org.py                # GET /admin/contexto/plantilla, GET/PUT /admin/contexto,
    │   │                             # POST /admin/contexto/subida (solo admin)
    │   └── infrastructure/
    │       └── org_store.py          # Persistencia JSON (extiende el perfil v2.0 vía INNOV_ORG_*)
    │
    ├── users/                       # Registro, roles, habilitación
    │   ├── domain/
    │   │   ├── user.py               # Entidad Usuario (datos + roles + habilitado)
    │   │   └── role_rules.py         # Regla "no dejar sin administrador" (RF-17)
    │   ├── use_cases/
    │   │   ├── create_user.py        # Emite contraseña temporal (RF-17)
    │   │   ├── change_password.py    # Cambio forzado en primer acceso
    │   │   ├── assign_roles.py       # Asigna/revoca roles
    │   │   └── toggle_active.py      # Desactiva/preserva historial (RF-17, caso 16)
    │   ├── routers/
    │   │   └── users.py
    │   └── infrastructure/
    │       └── user_store.py
    │
    ├── debate/                      # Debate de la idea publicada (RF-24, RF-25)
    │   ├── domain/
    │   │   └── debate_rules.py       # Validación de días de debate (1–90, defecto 30, v2.4),
    │   │                             # cierre automático único, deadline fijo al abrir (sin recomputar)
    │   ├── use_cases/
    │   │   ├── open_debate.py        # Crea el debate al publicarse (deadline = publishedAt + días globales)
    │   │   ├── post_message.py       # Publica mensaje; @asistant inline con enlace opcional (RF-25, v2.5)
    │   │   ├── list_debate.py        # Mensajes + estado + resumen; cierra si se superó el deadline
    │   │   ├── debate_days.py        # GET/PUT días de debate globales (admin; defecto 30; auditado, v2.4)
    │   │   └── close_summary.py      # Al cierre, con mensajes: resumen IA (pendiente si la IA cae)
    │   ├── routers/
    │   │   ├── debate.py             # GET/POST /catalog/{ideaId}/debate
    │   │   └── admin.py              # GET/PUT /admin/debate-days (admin; 422 inválido, v2.4)
    │   └── infrastructure/
    │       ├── debate_store.py       # JSON (debates + mensajes) bajo backend/data/
    │       └── debate_days_store.py  # Registro único JSON (debateDays, auditoría) bajo backend/data/
    │
    └── notifications/               # Centro in-app y eventos
        ├── domain/
        │   └── notification.py       # Entidad Notificación + tipos de evento (8 eventos, RF-18 v2.2)
        ├── use_cases/
        │   ├── create_notification.py # Genera los 8 eventos (RF-18 v2.2) + fanout a especialistas
        │   ├── list_notifications.py  # Leídas/no leídas
        │   └── mark_read.py
        ├── routers/
        │   └── notifications.py
        └── infrastructure/
            └── notification_store.py
```

**Trazabilidad RF — Estructura backend**

| Feature / capa | RF cubiertas |
|---|---|
| `features/auth` | RF-1 |
| `features/capture` | RF-2, RF-3, RF-5, RF-6, RF-7 |
| `features/assistant` | RF-3 (asignación), RF-4, RF-8, RF-11, RF-12, RF-22 (prompts con contexto) |
| `features/ideas` | RF-10, RF-19, RF-20 (zonas), RF-23 + RF-29 (reevaluación) + máquina de estados (estados finales) |
| `features/validation` | RF-14 (dos etapas), RF-15, RF-16, RF-26 (aceptar/sustituir evaluación), RF-27/RF-28 (decisión final + umbrales) |
| `features/users` | RF-17 |
| `features/org` | RF-21, RF-22 (contexto de empresa) |
| `features/debate` | RF-24, RF-25 (debate + @asistant + resumen) + disparo de la evaluación IA al cerrarse el debate (RF-26, caso 22) + notificación de calificación pendiente (RF-27) |
| `features/notifications` | RF-12, RF-15, RF-16, RF-18 (8 eventos) |

> **Nota de acoplamiento:** las features solo se comunican mediante contratos definidos en `shared/` (Constitución §3.2/§4.2). Ej.: `assistant` no importará de `ideas`; consumirá un contrato de lectura/expediente de idea expuesto a través de la capa compartida.

### 1.3 Reglas de nombrado aplicadas

* Frontend: *intent over role* — las clases se nombran según propósito (`capture`, `ManualFields`), sin el sufijo `Component` (Guía Angular §6).
* Backend: módulos de dominio puros (`domain/`) libres de FastAPI/Pydantic (Constitución §4.2).

### 1.4 Componentes de feature reutilizados → promotion a `shared/`

Si `idea-card` (usado en `my-ideas`, `validation` y `catalog`) se reutiliza en más de una feature, debe **promoverse** a `shared/components/` (Constitución §3.2). El plan lo define como candidato a promoción para respetar la regla.

**Trazabilidad RF:** estructura completa → RF-1 a RF-29 (cobertura de sección, no de criterio).

---

## 2. Modelo de datos y esquemas JSON

### 2.1 Entidades principales

| Entidad | Propósito | Campos esenciales |
|---|---|---|
| `Idea` | Unidad de negocio (los 6 campos + estado + evaluación) | id, campos, owner_id, origen, estado, timestamps, rastro, evaluación (RF-26) |
| `ChatMessage` | Mensaje de la conversación de captura | id, conversation_id, role, contenido, quickOptions (opciones del turno, D7), sugerencia de título |
| `Conversation` | Sesión de captura activa | id, user_id, estado, campos capturados, turno de campo |
| `IdeaVersion` | Versión vigente/refinada de una idea (aceptada/descartada) | id, idea_id, versión, campos, origen (manual/IA), estado |
| `User` | Cuenta y roles | id, username, nombre, área, datos contacto, roles, habilitado |
| `Notification` | Evento in-app (8 tipos, RF-18 v2.2) | id, user_id, tipo, idea_id, leído, fecha |
| `EvaluationThreshold` | Umbrales de calificación (documento único, RF-28) | rejectionThreshold, acceptanceThreshold (enteros 1–10), updatedBy, updatedAt |
| `Session` | Autenticación activa | token, user_id, expiración |
| `CompanyContext` | Contexto de empresa (documento único, RF-21) | perfil (nombre/sector/descripción/misión/objetivos) + texto guía; seed desde `INNOV_ORG_*` |
| `Debate` | Debate de una idea publicada (RF-24) | idea_id, deadline (fijado al abrir con los días globales vigentes, v2.4), cerrado, resumen IA |
| `DebateDays` | Días de debate globales (documento único, RF-24, v2.4) | debateDays (entero 1–90, defecto 30), updatedBy, updatedAt |
| `DebateMessage` | Mensaje del debate (RF-24/RF-25) | id, idea_id, autor (usuario o *Asistente*), texto, mensaje enlazado (@asistant), fecha |
| `IdeaEvaluation` | Evaluación vigente de una idea (RF-26) | 5 criterios (score 1–10 + justificación), autor (IA/especialista), fecha, decisión (aceptada/sustituida), rastro |

### 2.2 Esquema JSON — `Idea` (contemplando los 6 campos)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Idea",
  "type": "object",
  "required": [
    "id", "title", "proponent", "description", "problem",
    "expectedBenefit", "strategicAlignment",
    "ownerId", "origin", "state", "createdAt"
  ],
  "properties": {
    "id":   { "type": "string", "description": "Identificador único" },
    "ownerId": { "type": "string", "description": "Usuario creador (base RF-19)" },

    "title": {
      "type": "string",
      "minLength": 3,
      "maxLength": 140,
      "description": "Campo 1. Sugerido por IA o escrito por el usuario"
    },
    "proponent": {
      "type": "object",
      "required": ["name", "area", "contact"],
      "properties": {
        "name":    { "type": "string", "minLength": 1 },
        "area":    { "type": "string", "minLength": 1 },
        "contact": { "type": "string", "minLength": 1, "description": "Correo/teléfono; validación de formato (caso 12)" }
      },
      "description": "Campo 2. Prellenado desde la cuenta (RF-6/RF-7)"
    },
    "description": {
      "type": "string",
      "minLength": 10,
      "description": "Campo 3"
    },
    "problem": {
      "type": "string",
      "minLength": 5,
      "description": "Campo 4. Problema u oportunidad"
    },
    "expectedBenefit": {
      "type": "string",
      "minLength": 5,
      "description": "Campo 5"
    },
    "strategicAlignment": {
      "type": "string",
      "minLength": 5,
      "description": "Campo 6"
    },

    "origin": { "enum": ["asistida", "manual"], "description": "RF-2/RNF-2" },
    "state":  { "enum": ["EN_DESARROLLO", "SOLICITANDO_PUBLICACION", "VALIDADA_PUBLICA", "ACEPTADA", "ARCHIVADA", "RECHAZADA"], "description": "Máquina de estados (v2.2: estados finales RF-27/RF-29)" },
    "reviewedByAI":  { "type": "boolean", "default": false },
    "currentVersionId": { "type": ["string", "null"] },

    "createdAt":  { "type": "string", "format": "date-time" },
    "requestDate":{ "type": ["string", "null"], "format": "date-time", "description": "Fecha de solicitud de publicación" },
    "publishedAt":{ "type": ["string", "null"], "format": "date-time", "description": "Fecha de publicación" },
    "publishedBy":{ "type": ["string", "null"], "description": "Quién validó (RNF-8, autovalidación caso 9)" },

    "decision": {
      "type": ["object", "null"],
      "description": "Decisión final del especialista en la etapa de calificación (RF-27); null hasta que la idea decide (ACEPTADA/ARCHIVADA/RECHAZADA); se limpia al reevaluar una ARCHIVADA (RF-29)",
      "properties": {
        "outcome":   { "enum": ["ACEPTADA", "ARCHIVADA", "RECHAZADA"], "description": "Resultado final; debe coincidir con la banda del promedio de la evaluación vigente (RF-28)" },
        "reason":    { "type": "string", "description": "Motivo OBLIGATORIO para ARCHIVADA y RECHAZADA; nota opcional para ACEPTADA (RF-27)" },
        "score":     { "type": "number", "description": "Promedio de los 5 criterios al decidir (suma/5, 2 decimales); auditado (RNF-8)" },
        "decidedBy": { "type": "string", "description": "Usuario especialista" },
        "decidedByName": { "type": "string" },
        "decidedAt": { "type": "string", "format": "date-time" }
      },
      "required": ["outcome", "decidedBy", "decidedAt"]
    },

    "evaluation": {
      "type": ["object", "null"],
      "description": "Juicio final vigente (RF-26); null hasta que el debate se cierra y se intenta la generación",
      "properties": {
        "status":      { "enum": ["PENDING", "GENERADA", "ACEPTADA", "SUSTITUIDA"], "description": "PENDING mientras la IA no puede generarla al cierre (caso 22); el juicio final es siempre el resultado de la última acción del especialista (caso 23)" },
        "criteria":    {
          "type": "array",
          "description": "Los 5 criterios fijos: claridadDelProblema, factibilidad, impactoEsperado, alineacionEstrategica, gradoDeInnovacion",
          "items": {
            "type": "object",
            "required": ["criterion", "score", "justification"],
            "properties": {
              "criterion":     { "type": "string" },
              "score":         { "type": "integer", "minimum": 1, "maximum": 10 },
              "justification": { "type": "string" }
            }
          }
        },
        "author":      { "type": "string", "description": "'Asistente (IA)' o usuario especialista" },
        "createdAt":   { "type": "string", "format": "date-time" },
        "decidedBy":   { "type": ["string", "null"] },
        "decidedAt":   { "type": ["string", "null"], "format": "date-time" }
      }
    },
    "aiEvaluation": {
      "type": ["object", "null"],
      "description": "Instantánea inmutable de la evaluación de la IA (mismo formato que `evaluation`); visible en la vista de detalle aunque el juicio final sea la sustitución (RF-26)"
    }
  }
}
```

> `publishedAt`/`publishedBy` son el rastro de auditoría que exige RNF-8. `publishedBy` puede coincidir con `ownerId` sin romper la regla (autovalidación permitida con rastro, RF-15/caso 9). *Recursos estimados* quedó fuera del MVP (decisión 11 de la spec): no se captura, no se valida ni se expone; las ideas antiguas con el campo se leen descártandolo (migración silenciosa en el store). El debate (fecha límite, cerrado, resumen) vive en la feature `debate` y se expone en la vista de detalle (RF-23). La idea expone además `aiEvaluation` (instantánea de la evaluación de la IA, mismo formato que `evaluation`): permanece visible como «evaluación de la IA» aunque el juicio final sea la sustitución del especialista (RF-26).

### 2.3 Esquema JSON — `ChatMessage`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ChatMessage",
  "type": "object",
  "required": ["id", "conversationId", "role", "text", "createdAt"],
  "properties": {
    "id":              { "type": "string" },
    "conversationId":  { "type": "string" },
    "role":            { "enum": ["user", "assistant", "system"] },
    "text":            { "type": "string" },
    "currentField":    { "type": ["string", "null"], "description": "Campo en curso: description|title|problem|expectedBenefit|strategicAlignment|proponent" },
    "quickOptions":    { "type": "array", "items": { "type": "string" }, "description": "Opciones rápidas generadas por la IA para el turno en curso (RF-5, D7)" },
    "titleSuggestion": {
      "type": ["object", "null"],
      "properties": {
        "text":  { "type": "string" },
        "actions": { "enum": ["accept", "another", "manual"] }
      },
      "description": "Sugerencia proactiva de título (RF-4)"
    },
    "needsClarification": { "type": "boolean" },
    "createdAt":         { "type": "string", "format": "date-time" }
  }
}
```

### 2.4 Esquema JSON — `Conversation`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Conversation",
  "type": "object",
  "required": ["id", "userId", "state", "capturedFields", "currentField", "createdAt"],
  "properties": {
    "id":            { "type": "string" },
    "userId":        { "type": "string" },
    "state":         { "enum": ["ACTIVA", "RESUMEN", "TERMINADA", "CONTINGENCIA"] },
    "capturedFields":{
      "type": "object",
      "additionalProperties": { "type": "string" },
      "description": "Campos ya capturados (RNF-10)"
    },
    "currentField":  { "type": "string", "description": "Próximo campo por preguntar" },
    "order": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Orden fijo (RF-3)"
    },
    "createdAt":     { "type": "string", "format": "date-time" }
  }
}
```

### 2.5 Esquema JSON — `IdeaVersion`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "IdeaVersion",
  "type": "object",
  "required": ["id", "ideaId", "fields", "requestedBy", "status", "createdAt"],
  "properties": {
    "id":      { "type": "string" },
    "ideaId":  { "type": "string" },
    "version": { "type": "integer", "minimum": 1 },
    "fields": {
      "type": "object",
      "description": "Los 6 campos propuestos en esta versión",
      "required": ["title","proponent","description","problem","expectedBenefit","strategicAlignment"]
    },
    "requestedBy": { "enum": ["refinement", "improvement", "adjustment"], "description": "Origen de la versión (RF-11/RF-8/RF-13)" },
    "status":    { "enum": ["PENDIENTE", "ACEPTADA", "DESCARTADA", "VIGENTE"], "description": "Aceptación/descarte explícitos (RF-8, RF-13)" },
    "createdAt": { "type": "string", "format": "date-time" }
  }
}
```

### 2.6 Esquema JSON — ejemplo completo de una Idea con los 6 campos

```json
{
  "id": "idea_20260910_0001",
  "ownerId": "user_ana",
  "title": "Optimización del proceso de aprobación de proveedores",
  "proponent": {
    "name": "Ana Torres",
    "area": "Compras",
    "contact": "ana.torres@innov-ia.local"
  },
  "description": "Digitalizar la validación de proveedores eliminando la revisión manual duplicada entre áreas, reduciendo el ciclo de compra de 15 a 5 días.",
  "problem": "El proceso actual exige tres revisiones manuales independientes que duplican esfuerzo y causan retrasos en la compra crítica.",
  "expectedBenefit": "Ahorro de ~120 horas/mes de personal y reducción de costos por compras urgentes.",
  "strategicAlignment": "Alinea con el objetivo estratégico de agilizar la cadena de suministro y reducir la carga administrativa manual.",
  "origin": "asistida",
  "state": "EN_DESARROLLO",
  "reviewedByAI": true,
  "currentVersionId": "ver_0002",
  "createdAt": "2026-09-10T08:42:00Z",
  "requestDate": null,
  "publishedAt": null,
  "publishedBy": null
}
```

### 2.7 Esquema JSON — `Notification`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Notification",
  "type": "object",
  "required": ["id", "userId", "type", "ideaId", "read", "createdAt"],
  "properties": {
    "id":      { "type": "string" },
    "userId":  { "type": "string" },
    "type":    { "enum": ["IDEA_REFINED", "IDEA_PUBLISHED", "IDEA_REJECTED", "IDEA_REQUESTED", "IDEA_ACCEPTED", "IDEA_ARCHIVED", "IDEA_REEVALUATED", "IDEA_CALIBRATION_PENDING"], "description": "Solo los 8 eventos (RF-18; v2.2 añade los 4 últimos). IDEA_REJECTED se reutiliza para el rechazo en la etapa de calificación (RF-27); el mensaje distingue la etapa e incluye el comentario/motivo" },
    "ideaId":  { "type": "string" },
    "message": { "type": "string", "description": "Texto para el usuario; incluye el comentario (publicación) o motivo (calificación) cuando corresponde" },
    "read":    { "type": "boolean", "default": false },
    "createdAt": { "type": "string", "format": "date-time" }
  }
}
```

> v2.2: se amplía el enum de `EVENT_TYPES` (feature `notifications`) con `IDEA_ACCEPTED`, `IDEA_ARCHIVED`, `IDEA_REEVALUATED` (destino: creador) e `IDEA_CALIBRATION_PENDING` (destino: todos los especialistas). El rechazo en la etapa de calificación reutiliza `IDEA_REJECTED` (el texto del mensaje indica que procede de la calificación y lleva el motivo, RF-27/RF-18).

### 2.8 Esquema JSON — `CompanyContext` (contexto de empresa, RF-21)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "CompanyContext",
  "type": "object",
  "required": ["profile", "guideText", "updatedAt"],
  "properties": {
    "profile": {
      "type": "object",
      "description": "Sección fija de la plantilla (RF-21); sustituye al perfil de organización v2.0",
      "properties": {
        "name":     { "type": "string" },
        "sector":   { "type": "string" },
        "description": { "type": "string" },
        "mission":  { "type": "string" },
        "strategicObjectives": { "type": "array", "items": { "type": "string" } }
      }
    },
    "guideText": {
      "type": "string",
      "description": "Texto libre de guía (alineación estratégica, vocabulario, información de referencia) que inyecta la IA en todas sus operaciones (RF-22)"
    },
    "updatedAt": { "type": "string", "format": "date-time" }
  }
}
```

> Cuando `profile` y `guideText` están vacíos se trata de contexto vacío: la IA opera sin contexto y la sección de administración muestra el aviso al administrador (RF-22, caso 24). La plantilla (`GET /admin/contexto/plantilla`) es un texto `text/plain` con las secciones orientativas: **perfil de la organización**, **alineación estratégica** (objetivos, prioridades y líneas de innovación) y **vocabulario e información de referencia**.

### 2.9 Esquema JSON — `Debate` y `DebateMessage` (RF-24, RF-25)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Debate",
  "type": "object",
  "required": ["ideaId", "deadline", "closed"],
  "properties": {
    "ideaId":    { "type": "string" },
    "deadline":  { "type": "string", "format": "date-time", "description": "publishedAt + días de debate globales vigentes al abrir (v2.4); inmutable: no se recomputa ni al cambiar la configuración ni al releer" },
    "closed":    { "type": "boolean", "description": "Cierre automático y definitivo al llegar la fecha límite (solo se ejecuta una vez)" },
    "summary":   { "type": ["string", "null"], "description": "Resumen de la IA de los puntos principales (solo si hubo mensajes; null mientras la IA no puede generarlo)" }
  }
}
```

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "DebateMessage",
  "type": "object",
  "required": ["id", "ideaId", "author", "text", "createdAt"],
  "properties": {
    "id":               { "type": "string" },
    "ideaId":           { "type": "string" },
    "author":           { "type": "string", "description": "Nombre del usuario, o 'Asistente (IA)' para los mensajes generados (RF-25)" },
    "authorId":         { "type": ["string", "null"] },
    "text":             { "type": "string" },
    "linkedMessageId":  { "type": ["string", "null"], "description": "Mensaje al que responde un @asistant (RF-25, RNF-11)" },
    "processed":        { "type": "boolean", "description": "Para peticiones @asistant: false mientras la IA no pudo procesarlas (caso 20); se reintenta en la siguiente interacción" },
    "createdAt":        { "type": "string", "format": "date-time" }
  }
}
```

> **DebateDays (v2.4):** registro único (mismo patrón de documento JSON por entidad, D1/D19):
>
> ```json
> {
>   "debateDays": { "type": "integer", "minimum": 1, "maximum": 90, "default": 30, "description": "Días de duración de cada debate (RF-24, v2.4)" },
>   "updatedBy":  { "type": ["string", "null"], "description": "Auditoría (RNF-11): admin que cambió el valor; null si aún no hay cambio explícito (solo el defecto)" },
>   "updatedAt":  { "type": ["string", "format": "date-time", "null"], "description": "Auditoría (RNF-11): cuándo cambió el valor" }
> }
> ```
>
> Solo afecta a los debates que se abran a partir del cambio; los debates ya abiertos/cerrados conservan su `deadline` almacenado (sin recomputación ni migración).

### 2.10 Esquema JSON — `IdeaEvaluation`

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "IdeaEvaluation",
  "type": "object",
  "required": ["criteria", "author", "createdAt"],
  "properties": {
    "criteria": {
      "type": "array",
      "description": "Los 5 criterios fijos (RF-26): claridadDelProblema, factibilidad, impactoEsperado, alineacionEstrategica, gradoDeInnovacion",
      "items": {
        "type": "object",
        "required": ["criterion", "score", "justification"],
        "properties": {
          "criterion":     { "type": "string" },
          "score":         { "type": "integer", "minimum": 1, "maximum": 10 },
          "justification": { "type": "string" }
        }
      }
    },
    "author":      { "type": "string", "description": "'Asistente (IA)' o id/nombre del especialista" },
    "createdAt":   { "type": "string", "format": "date-time" },
    "decidedBy":   { "type": ["string", "null"], "description": "Aceptación o sustitución: quién y cuándo (RNF-8, RNF-11)" },
    "decidedAt":   { "type": ["string", "null"], "format": "date-time" }
  }
}
```

> El juicio final de la idea es único en todo momento (RF-26): la evaluación de la IA (mientras no haya decisión), la evaluación de la IA aceptada, o la evaluación sustitutiva del especialista. Aceptar y sustituir están disponibles en cualquier orden sobre el estado previo: cada acción produce un nuevo juicio final (última acción, caso 23) y queda auditada (RNF-8, RNF-11).

**Trazabilidad RF — Modelo de datos**

| Entidad | RF |
|---|---|
| `Idea` | RF-1 (ownerId), RF-10/RF-19/RF-20, RF-15/RF-16 (rastro), RF-26 (evaluación), RF-27/RF-29 (estado + decisión) |
| `ChatMessage` | RF-3, RF-4, RF-5 |
| `Conversation` | RF-2, RF-3, RF-6, RNF-10 |
| `IdeaVersion` | RF-8, RF-11, RF-13 |
| `User` | RF-17 |
| `Notification` | RF-12, RF-15, RF-16, RF-18 (8 eventos v2.2) |
| `CompanyContext` | RF-21, RF-22 |
| `Debate`, `DebateMessage` | RF-24, RF-25, RNF-11 |
| `IdeaEvaluation` | RF-26, RNF-8, RNF-11 |
| `Idea.decision` (dentro de `Idea`, §2.2) | RF-27, RF-29, RNF-8 |
| `EvaluationThreshold` | RF-28, RNF-8 |

### 2.11 Esquema JSON — `EvaluationThreshold` (umbrales de calificación, RF-28)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "EvaluationThreshold",
  "type": "object",
  "required": ["rejectionThreshold", "acceptanceThreshold"],
  "properties": {
    "rejectionThreshold":  { "type": "integer", "minimum": 1, "maximum": 9, "description": "Umbral de rechazo (entero); promedio < X → RECHAZADA. Por defecto 4" },
    "acceptanceThreshold": { "type": "integer", "minimum": 2, "maximum": 10, "description": "Umbral de aceptación (entero); promedio ≥ Z → ACEPTADA. Por defecto 7" },
    "updatedBy":   { "type": ["string", "null"], "description": "Último administrador que guardó (RNF-8)" },
    "updatedAt":   { "type": ["string", "null"], "format": "date-time", "description": "Fecha del último guardado (RNF-8)" }
  }
}
```

> Documento único gestionado por el administrador (sección de administración, RF-28): `rejectionThreshold < acceptanceThreshold` (invariante; se valida en el guardado, caso inválido → 422). Bandas: **promedio < X → RECHAZADA**; **X ≤ promedio < Z → ARCHIVADA**; **promedio ≥ Z → ACEPTADA** (caso 26: el promedio exacto en un umbral cae en la banda cerrada por arriba). Persistido como un único registro en `infrastructure/` (misma abstracción de JSON por entidad, D1); el cambio queda auditado con quien y cuándo (RNF-8, §2.11 `updatedAt`/`updatedBy` en el registro persistente). Solo afecta decisiones posteriores: las ideas ya en estado final no se recalculan (caso 31).

---

## 3. Contratos de la API REST

Base: `/api/v1`. Autenticación por **portador de sesión** (RF-1). Todos los payloads son JSON (excepción: `GET /admin/contexto/plantilla` devuelve `text/plain`; la subida de contexto envía el texto como campo JSON para no requerir `multipart`).

### 3.1 Resumen de endpoints

| Método | Ruta | Rol | RF | Descripción |
|---|---|---|---|---|
| POST | `/auth/login` | — | RF-1 | Inicia sesión |
| POST | `/auth/logout` | sesión | RF-1 | Cierra sesión |
| GET  | `/auth/me` | sesión | RF-1 | Datos y roles del usuario |
| POST | `/capture/start` | proponente | RF-2 | Inicia/retoma conversación: prioriza la ACTIVA; si no, retoma la RESUMEN más reciente devolviéndole el **resumen editable** (`state: RESUMEN`, `summary`); si no, nueva (IA disponible) o formulario manual |
| GET  | `/capture/assistant-status` | proponente | RF-7 | Estado del asistente (OK/UNAVAILABLE) |
| POST | `/capture/messages` | proponente | RF-3,RF-4,RF-5 | Procesa un mensaje de captura |
| POST | `/capture/finish` | proponente | RF-6 | Registra idea (EN_DESARROLLO) |
| POST | `/capture/activate-manual` | proponente | RF-7 | Convierte conversación en formulario prellenado |
| POST | `/capture/abandon` | proponente | RF-2 | Abandono explícito: termina la conversación (ACTIVA/RESUMEN/CONTINGENCIA) sin guardar nada (sin borradores, caso 7); idempotente si ya terminada; `conversationId` opcional (por defecto la en curso); 403 si no es dueño, 404 si no existe (v2.3) |
| POST | `/ideas` | proponente | RF-6,RF-7 | Crea idea (origen asistida/manual) |
| GET  | `/ideas/me` | proponente | RF-19 | Lista mis ideas |
| GET  | `/ideas/{id}` | dueño | RF-19 | Detalle de una idea |
| PUT  | `/ideas/{id}` | dueño | RF-9 | Edición manual (6 campos) |
| POST | `/ideas/{id}/improve` | dueño (con IA) | RF-8 | Solicita mejora (versión pendiente) |
| POST | `/ideas/{id}/versions/{vid}/decide` | dueño | RF-8,RF-13 | Aceptar/descartar versión |
| POST | `/ideas/{id}/request-publication` | dueño | RF-10 | Solicita publicación |
| GET  | `/validation/queue` | especialista | RF-14 | Cola en dos etapas: `?stage=publicacion` (SOLICITANDO_PUBLICACION) / `?stage=calibracion` (VALIDADA_PUBLICA con debate cerrado, evaluación generada y sin decisión) / sin parámetro (ambas, v2.2) |
| POST | `/validation/{id}/approve` | especialista | RF-15, RF-24 | Valida/publica; abre el debate (días de debate globales vigentes, v2.4). No ejecuta la evaluación IA (se genera al cerrarse el debate, RF-26) |
| POST | `/validation/{id}/reject` | especialista | RF-16 | Rechaza en la etapa de publicación con comentario |
| POST | `/validation/{id}/evaluation/accept` | especialista | RF-26 | Acepta la evaluación de la IA (juicio final) |
| POST | `/validation/{id}/evaluation` | especialista | RF-26 | Sustituye la evaluación vigente por la propia (5 criterios) |
| POST | `/validation/{id}/decision` | especialista | RF-27, RF-28 | Decisión final (etapa de calificación): `{outcome, reason}`; 409 si `outcome` ≠ banda del promedio (caso 27), 400 sin motivo en ARCHIVADA/RECHAZADA (caso 28), 409 si no está en VALIDADA_PUBLICA; audita y notifica |
| POST | `/ideas/{id}/request-reevaluation` | dueño | RF-29 | Reevaluación de una ARCHIVADA: vuelve a VALIDADA_PUBLICA (conserva debate cerrado y evaluación IA; limpia `decision`); 409 si no es ARCHIVADA (caso 29/30); notifica al creador |
| GET  | `/admin/calibration-thresholds` | admin | RF-28 | Umbrales vigentes |
| PUT  | `/admin/calibration-thresholds` | admin | RF-28 | Actualiza umbrales `{rejectionThreshold, acceptanceThreshold}`; 422 si no enteros 1–10 o `rejection < acceptance`; auditado (RNF-8) |
| GET  | `/catalog/public` | sesión | RF-20 | Catálogo COMPACTO por zonas: `?zone=en-proceso\|aceptadas\|rechazadas\|archivadas` (v2.2); sin parámetro → todas (título, fecha de publicación, descripción, D16) |
| GET  | `/catalog/{ideaId}` | sesión | RF-23 | Detalle de una idea publicada (VALIDADA_PUBLICA o estado final): 6 campos, debate y evaluación; expone `state` y `decision` cuando existen |
| GET  | `/catalog/{ideaId}/debate` | sesión | RF-24, RF-25 | Mensajes del debate + deadline + cerrado + resumen |
| POST | `/catalog/{ideaId}/debate` | sesión | RF-24, RF-25 | Publica mensaje (texto, mensaje enlazado para @asistant); 409 si cerrado |
| GET  | `/admin/debate-days` | admin | RF-24, RNF-11 | Días de debate vigentes (v2.4) |
| PUT  | `/admin/debate-days` | admin | RF-24, RNF-11 | Actualiza días de debate `{debateDays}`; entero 1–90, defecto 30; 422 si inválido; auditado (quién/cuándo, RNF-11); solo afecta a debates nuevos (v2.4) |
| GET  | `/admin/contexto/plantilla` | admin | RF-21 | Plantilla de texto del contexto de empresa (`text/plain`) |
| GET  | `/admin/contexto` | admin | RF-21, RF-22 | Documento de contexto vigente (o vacío, caso 24) |
| PUT  | `/admin/contexto` | admin | RF-21 | Edición en línea del documento (perfil + guía); 400 si perfil vacío |
| POST | `/admin/contexto/subida` | admin | RF-21 | Subida de archivo (campo `content`): reemplaza el documento vigente; 400 si vacío |
| GET  | `/notifications` | sesión | RF-18 | Lista + contador no leídas |
| POST | `/notifications/{id}/read` | dueño | RF-18 | Marca leída |
| GET  | `/users` | admin | RF-17 | Lista usuarios |
| POST | `/users` | admin | RF-17 | Crea usuario (contraseña temporal) |
| PUT  | `/users/{id}/roles` | admin | RF-17 | Asigna/revoca roles |
| PATCH| `/users/{id}/active` | admin | RF-17 | Desactiva/habilita |
| POST | `/auth/change-password` | sesión | RF-17 | Cambio forzado en primer acceso |
| POST | `/assistant/check` | proponente | RF-11 | Verifica disponibilidad y procesa la cola (disparador bajo demanda; también se dispara internamente al iniciar sesión) |

### 3.2 Ejemplos de payload

**POST `/capture/messages`**
```json
// Entrada
{ "message": "Quisiera reducir los tiempos de compra con un flujo digital.", "quickOptionSelected": null }
// Salida 200
{
  "conversationId": "conv_001",
  "assistant": {
    "text": "¿Cuál es el problema u oportunidad que aborda exactamente?",
    "currentField": "problem",
    "quickOptions": ["Retraso en compras urgentes", "Costos altos por proveedores no competitivos"],
    "titleSuggestion": null
  }
}
```
> `quickOptions` son las opciones que la IA generó para el turno en curso (RF-5, D7); el array puede ser vacío cuando el campo no las admite.

**POST `/capture/start`** (v2.3: retoma ACTIVA o RESUMEN)
```json
// Entrada: sin cuerpo (solo sesión proponente)
// Salida 200 — retoma la conversación ACTIVA en curso (caso 8, RF-2)
{
  "mode": "assistant",
  "resumed": true,
  "conversation": { "id": "conv_001", "state": "ACTIVA", "currentField": "problem", "capturedFields": { "description": "…" } },
  "assistant": null,
  "state": "ACTIVA",
  "summary": null,
  "manual": null
}
// Salida 200 — retoma la RESUMEN más reciente: los campos ya capturados no se pierden (RF-2/RF-6, v2.3)
{
  "mode": "assistant",
  "resumed": true,
  "conversation": { "id": "conv_002", "state": "RESUMEN", "capturedFields": { "title": "…", "description": "…", "problem": "…", "expectedBenefit": "…", "strategicAlignment": "…", "proponent": "{…json…}" } },
  "assistant": null,
  "state": "RESUMEN",
  "summary": { "title": "…", "description": "…", "problem": "…", "expectedBenefit": "…", "strategicAlignment": "…", "proponent": { "name": "…", "area": "…", "contact": "…" } },
  "manual": null
}
// Salida 200 — nueva conversación (IA disponible)
{
  "mode": "assistant",
  "resumed": false,
  "conversation": { "id": "conv_003", "state": "ACTIVA", "currentField": "description", "capturedFields": {} },
  "assistant": { "text": "…saludo…\n\nCuéntame, ¿en qué quieres trabajar?", "currentField": "description", "quickOptions": [], "titleSuggestion": null },
  "state": "ACTIVA",
  "summary": null,
  "manual": null
}
// Salida 200 — IA no disponible: formulario manual directo (caso 1, RF-7)
{
  "mode": "manual",
  "resumed": false,
  "conversation": null,
  "assistant": null,
  "state": null,
  "summary": null,
  "manual": { "notice": "El asistente no está disponible; completa el formulario manual.", "capturedFields": {} }
}
```

**POST `/capture/abandon`** (v2.3, RF-2, caso 7)
```json
// Entrada (conversationId opcional; por defecto la conversación en curso del usuario)
{ "conversationId": "conv_002" }
// Salida 200 — termina la conversación sin guardar nada (sin borradores)
{ "conversationId": "conv_002", "state": "TERMINADA" }
// Salida 200 — idempotente si la conversación ya estaba TERMINADA
{ "conversationId": "conv_002", "state": "TERMINADA" }
// 403 si la conversación no pertenece al usuario:
{ "error": { "code": "NOT_CONVERSATION_OWNER", "message": "La conversación no es tuya." } }
// 404 si la conversación no existe:
{ "error": { "code": "CONVERSATION_NOT_FOUND", "message": "La conversación no existe." } }
```

**POST `/capture/finish`**
```json
// Entrada (resumen confirmado)
{ "captured": { "title": "…", "description": "…", "problem": "…", "expectedBenefit": "…", "strategicAlignment": "…", "proponent": {"name":"…","area":"…","contact":"…"} } }
// Salida 201
{ "ideaId": "idea_…", "state": "EN_DESARROLLO", "origin": "asistida" }
```

**POST `/validation/{id}/reject`**
```json
// Entrada (comentario OBLIGATORIO)
{ "comment": "Falta estimación de presupuesto; complétalo antes de re-solicitar." }
// Salida 200
{ "state": "EN_DESARROLLO", "rejectNote": "…" }
```

**POST `/catalog/{ideaId}/debate`**
```json
// Entrada (invocación @asistant inline; linkedMessageId es contexto opcional, v2.5)
{ "text": "@asistant ¿cómo se alinea esto con las líneas de innovación del contexto?", "linkedMessageId": "debmsg_003" }
// Salida 201
{ "id": "debmsg_007", "author": "Laura Gómez", "text": "@asistant ¿cómo se alinea…?", "linkedMessageId": "debmsg_003", "createdAt": "…" }
// Salida 201 adicional: el sistema responde en el hilo (RF-25)
{ "id": "debmsg_008", "author": "Asistente (IA)", "text": "…criterio generado con el contexto de empresa…", "linkedMessageId": "debmsg_007", "createdAt": "…" }
// Sin petición tras el token (@asistant solo) se publica como mensaje corriente,
// sin invocar al asistente (caso 19, v2.5); un linkedMessageId inexistente es 400.
// Salida 409 cuando el debate está cerrado
{ "error": { "code": "DEBATE_CLOSED", "message": "El debate está cerrado (fecha límite alcanzada)." } }
```

**POST `/validation/{id}/evaluation`**
```json
// Entrada (sustitución por el especialista; mismos 5 criterios, RF-26)
{ "criteria": [
  { "criterion": "claridadDelProblema",     "score": 8, "justification": "…" },
  { "criterion": "factibilidad",            "score": 7, "justification": "…" },
  { "criterion": "impactoEsperado",         "score": 9, "justification": "…" },
  { "criterion": "alineacionEstrategica",   "score": 8, "justification": "…" },
  { "criterion": "gradoDeInnovacion",       "score": 6, "justification": "…" }
] }
// Salida 200
{ "status": "SUSTITUIDA", "author": "Marta Ruiz (especialista)", "decidedBy": "user_marta", "decidedAt": "…" }
// Aceptar y sustituir pueden alternarse en cualquier orden: el juicio final
// es siempre el resultado de la última acción (caso 23); cada acción queda auditada.
```

**POST `/validation/{id}/decision`** (v2.2, RF-27/RF-28)
```json
// Entrada (decisión final; reason OBLIGATORIO para ARCHIVADA y RECHAZADA, opcional para ACEPTADA)
{ "outcome": "ARCHIVADA", "reason": "Buen encaje estratégico, pero la factibilidad es baja para este ejercicio." }
// Salida 200
{
  "state": "ARCHIVADA",
  "decision": {
    "outcome": "ARCHIVADA",
    "reason": "Buen encaje estratégico, pero la factibilidad es baja para este ejercicio.",
    "score": 5.4,
    "decidedBy": "user_marta",
    "decidedByName": "Marta Ruiz",
    "decidedAt": "…"
  }
}
// 409 cuando outcome ≠ banda del promedio de la evaluación vigente (caso 27):
{ "error": { "code": "DECISION_MISMATCH", "message": "El resultado elegido no coincide con el promedio (5.4 → archivada). Ajusta la puntuación.", "details": { "score": 5.4, "band": "ARCHIVADA" } } }
// 400 sin motivo en ARCHIVADA/RECHAZADA (caso 28):
{ "error": { "code": "DECISION_REASON_REQUIRED", "message": "El motivo es obligatorio para archivar o rechazar." } }
```

**POST `/ideas/{id}/request-reevaluation`** (v2.2, RF-29)
```json
// Entrada: sin cuerpo (solo el dueño de una idea ARCHIVADA)
// Salida 200
{ "state": "VALIDADA_PUBLICA", "decision": null, "note": "La idea vuelve a la cola de calificación conservando el debate cerrado y la evaluación de la IA." }
// 409 si la idea no está en ARCHIVADA (caso 29: ACEPTADA/RECHAZADA no admiten reevaluación):
{ "error": { "code": "REEVALUATION_NOT_ALLOWED", "message": "Solo las ideas archivadas pueden solicitarse a reevaluación." } }
```

**PUT `/admin/calibration-thresholds`** (v2.2, RF-28)
```json
// Entrada
{ "rejectionThreshold": 4, "acceptanceThreshold": 7 }
// Salida 200
{ "rejectionThreshold": 4, "acceptanceThreshold": 7, "updatedBy": "user_admin", "updatedAt": "…" }
// 422 si los umbrales no son enteros 1–10 o rejection >= acceptance:
{ "error": { "code": "THRESHOLDS_INVALID", "message": "Los umbrales deben ser enteros 1–10 con umbralRechazo < umbralAceptacion.", "details": { "problems": ["rejectionThreshold >= acceptanceThreshold"] } } }
```

**GET `/catalog/public?zone=aceptadas`** (v2.2, RF-20)
```json
// Salida 200 (una zona; sin parámetro devuelve todas las zonas)
{
  "zone": "aceptadas",
  "items": [
    { "id": "idea_001", "title": "…", "publishedAt": "…", "description": "…" }
  ]
}
```

**PUT `/admin/contexto`**
```json
// Entrada (edición en línea del documento, RF-21)
{
  "profile": {
    "name": "Grupo Innov", "sector": "Industria",
    "description": "…", "mission": "…",
    "strategicObjectives": ["Digitalizar la cadena de suministro", "Reducir la carga administrativa manual"]
  },
  "guideText": "Líneas de innovación: automatización, datos, sostenibilidad.\nVocabulario de referencia: …"
}
// Salida 200: el documento actualizado
```

### 3.3 Manejo del flujo de chat asistido (secuencia)

1. Cliente → `POST /capture/start` → 200: si el usuario tiene conversación ACTIVA, se retoma (caso 8); si solo tiene una RESUMEN, se retoma con `state: RESUMEN` + `summary` editable (v2.3, RF-2); si no, nueva conversación + saludo/primera pregunta (RF-2).
2. Cliente → `POST /capture/messages` con la respuesta.
3. Backend aplica el texto al campo en curso (asignación narrativa, RF-3) y devuelve la siguiente pregunta + opciones rápidas del turno generadas por la IA (RF-5, D7) + sugerencia de título si corresponde (RF-4).
4. Al completar los 6 campos, el último `messages` devuelve `state: RESUMEN` con el resumen editable (RF-6).
5. Cliente → `POST /capture/finish` → 201 idea (EN_DESARROLLO, RF-6).
6. En cualquier momento, el cliente puede → `POST /capture/abandon` (v2.3, RF-2, caso 7): termina la conversación en curso (ACTIVA/RESUMEN/CONTINGENCIA) sin guardar nada (sin borradores) y libera el límite de una conversación a la vez; es idempotente si ya está terminada.
7. Si en cualquier paso la IA falló → ver §3.4.

### 3.4 Fallback manual (secuencia)

1. Al iniciar: cliente llama `GET /capture/assistant-status`.
   * `UNAVAILABLE` → el cliente muestra directamente el formulario manual (RF-7, caso 1, 3).
2. Fallando a mitad de conversación: `POST /capture/messages` devuelve `503` con `{"error": {"code": "ASSISTANT_UNAVAILABLE", …}, "fallback": {"capturedFields": { … } }}`; el cliente abre el formulario **prellenado** (RF-7, caso 2, RNF-10).
3. Cliente → `POST /ideas` (origen `manual`) → 201 idea EN_DESARROLLO (RF-7).

### 3.5 Códigos de respuesta HTTP

| Código | Significado |
|---|---|
| 200 | OK |
| 201 | Creado (idea, usuario, notificación, conversación) |
| 400 | Mal formada o error de validación (ej. rechazar sin comentario, RF-16; campos incompletos, RNF-5) |
| 401 | No autenticado / sesión caducada (caso 15) |
| 403 | Rol no permitido (segregación, RNF-7) |
| 404 | Recurso no encontrado |
| 409 | Conflicto (transición de estado no permitida, RNF-9) |
| 422 | Dato inválido por esquema (ej. campo contacto mal, caso 12) |
| 503 | Asistente de IA no disponible / contingencia (RF-7) |

### 3.6 Errores — formato unificado

```json
{ "error": { "code": "REJECT_WITHOUT_COMMENT", "message": "El rechazo requiere un comentario.", "details": {} } }
```

### 3.7 Manejadores globales de excepciones (`shared/exceptions`)

* `DomainError` (regla de negocio violada) → 409/400.
* `ValidationFailed` (Pydantic) → 422.
* `AssistantUnavailable` → 503 con payload de contingencia.
* `AuthError` → 401.
* `Forbidden` → 403.

**Trazabilidad RF — API REST**

| Bloque endpoint | RF cubiertas |
|---|---|
| auth | RF-1 |
| capture (start/messages/finish/activate-manual/abandon) | RF-2, RF-3, RF-4, RF-5, RF-6, RF-7 |
| ideas (CRUD/improve/versions/request-publication) | RF-8, RF-9, RF-10, RF-19 |
| validation (queue/approve/reject) | RF-14, RF-15, RF-16 |
| catalog | RF-20 |
| notifications | RF-18 (y eventos RF-12/15/16) |
| users + change-password | RF-17 |

---

## 4. Lógica de orquestación (pseudocódigo)

Pseudocódigo de alto nivel. No es código de implementación.

### 4.1 Máquina de estados del chatbot (captura asistida)

```
ORDER = [description, title, problem, expectedBenefit, strategicAlignment, proponent]   # 6 campos (decisión 11 spec)

func INICIAR_CONVERSACION(usuario):
    en_curso = conversaciones del usuario en ACTIVA o RESUMEN  # límite 1 (RF-2, caso 8, v2.3)
    si existe ACTIVA en en_curso:                              # prioridad: la ACTIVA
        devolver la ACTIVA + su turno actual
    si existe RESUMEN en en_curso:                             # v2.3: retoma con el resumen editable
        devolver la RESUMEN + state=RESUMEN + RESUMEN_EDITABLE(resumen)  # los campos ya capturados no se pierden (RF-6)
    si ASISTENTE_DISPONIBLE():
        conv = nuevo conversation(campos={}, currentField=ORDER[0])
        devolver conv + saludo + pregunta(ORDER[0])  # sin chips: la 1ª llamada IA va en PROCESAR_MENSAJE (D7)
    si no:
        devolver FORMULARIO_MANUAL(campos={})       # RF-7, caso 1

func ABANDONAR_CONVERSACION(usuario, [conversationId]):     # v2.3, RF-2, caso 7
    conv = conversación indicada (o la en curso del usuario)
    si conv no existe: 404
    si conv.userId != usuario: 403                          # solo la conversación del propio usuario
    si conv.state en {ACTIVA, RESUMEN, CONTINGENCIA}:
        conv.state = TERMINADA                              # sin guardar nada (sin borradores, D4)
    devolver {conversationId, state: TERMINADA}             # idempotente si ya estaba TERMINADA

func PROCESAR_MENSAJE(conv, texto):
    if conv.state == RESUMEN:                      # ya completado
        devolver RESUMEN_EDITABLE
    if conv.currentField == title:
        # El título se maneja por sugerencia (RF-4), no por texto libre inicial
        devolver SUGERIR_TITULO(conv)
    campos = EXTRAER_CAMPOS(texto)                 # asigna narrativa a 1 o varios campos (RF-3)
    campos = UNION(conv.capturedFields, campos)
    conv.capturedFields = campos
    ADVANZAR_CAMPO(conv)                           # salta campos ya completados (RF-3)
    if TODOS_CAMPOS_COMPLETOS(conv):
        conv.state = RESUMEN
        devolver RESUMEN_EDITABLE(conv)            # RF-6
    si no:
        devolver PREGUNTA(conv.currentField) + opciones_turno(conv, IA) + (title_suggestion si aplica)  # D7

func EXTRAER_CAMPOS(texto):
    # La IA asigna fragmentos a campos (RF-3); si un campo es insuficiente,
    # se marca needsClarification y NO avanza (RF-3).
    ...

func ADVANZAR_CAMPO(conv):
    for campo in ORDER:
        if campo NO in conv.capturedFields:
            conv.currentField = campo
            devolver

func FINALIZAR_CONV(conv, resumen_confirmado):
    validar 6 campos completos (RNF-5)
    idea = crear_idea(resumen, owner=conv.userId, origin=asistida)
    conv.state = TERMINADA
    devolver idea                                    # RF-6
```

### 4.2 Mecanismo de sugerencias rápidas (chips)

```
func OPCIONES_TURNO(conv, IA):                          # D7: generación por turno
    campo = conv.currentField
    si campo NO es elegible para opciones O conv.capturedFields está vacío:
        devolver { quickOptions: [] }
    respuesta = IA(turn_options_prompt(campo, conv.capturedFields_texto, contexto_empresa))   # RF-22
    devolver { quickOptions: limpiar_opciones(respuesta.options) }   # máx. 5, ≤90 chars, únicas

# Además, la misma llamada compacta en texto los campos libres ya capturados
# (description, problem, expectedBenefit, strategicAlignment; nunca los
# estructurados ni el título) y se aplican a conv.capturedFields.

func PREGUNTA_CAMPO(campo, quickOptions=[]):
    devolver {
        text:      PREGUNTA_POR_CAMPO[campo],
        currentField: campo,
        quickOptions: quickOptions                     # del turno (IA, RF-5/D7)
    }

func APLICAR_CHIP(campo, chip):
    si chip NO está entre las ofrecidas en el turno:   # RF-5: solo chips del turno
        devolver ERROR (400)
    conv.capturedFields[campo] = chip                  # el chip es la respuesta COMPLETA
    ADVANZAR_CAMPO(conv)
```

### 4.3 Sugerencia proactiva del título (RF-4)

```
func SUGERIR_TITULO(conv, intentos=[]):
    contexto = resumen_breve(conv.capturedFields)
    titulo = IA.sugerir_titulo(contexto, evitar=intentos)
    devolver titleSuggestion = { text: titulo, actions: [accept, another, manual] }

func ALTERNATIVA_TITULO(conv, sugerencia_actual):
    devolver SUGERIR_TITULO(conv, evitar=+[sugerencia_actual])   # distinta de la anterior (RF-4)

func ACEPTAR_TITULO(conv, texto):
    conv.capturedFields.title = texto                # sin modificación si es manual (RF-4)
    ADVANZAR_CAMPO(conv)
```

### 4.4 Detección de caídas de la IA + activación del modo manual (RF-7, RNF-1, RNF-3)

```
func ASISTENTE_DISPONIBLE():
    try:
        if ping_IA() con timeout 60s: devolver true
    except timeout|error:
        REINTENTAR una única vez (transparente, RNF-3)
        si falla de nuevo: devolver false              # "fallo IA" (caso 14)

func on_fallo_during_conversation(conv, error):
    conv.state = CONTINGENCIA
    devolver 503 { fallback: { capturedFields: conv.capturedFields } }   # prellenado (caso 2, RNF-10)

func ACTIVAR_MANUAL(conv):
    devolver FORMULARIO_MANUAL(prellenado=conv.capturedFields)  # RF-7
```

### 4.5 Clarificación posterior / refinamiento de ideas manuales (RF-11, RF-12)

```
func COLA_REFINAMIENTO():
    devolver ideas WHERE origin==manual
                   AND state==EN_DESARROLLO
                   AND NO tiene version refinada valida
    ordenar por createdAt ASC                        # más antigua primero (RF-11)

func VERIFY_Y_PROCESAR(user_id):                     # llamado bajo demanda (RF-11):
    if NO ASISTENTE_DISPONIBLE(): devolver           # sigue operativo (RF-11)
    REINTENTAR_EVALUACIONES_PENDIENTES()                    # las evaluaciones PENDING (RF-26, caso 22)
    for idea in COLA_REFINAMIENTO():
        try:
            version = IA.refinar(idea)
            if version valida (6 campos OK):
                crear IdeaVersion(idea, version, requestedBy=refinement, status=PENDIENTE)
                notificar IDEA_REFINED(idea.ownerId, idea)   # RF-12
            si no: marcar fallo parcial; la idea sigue pendiente (caso 6)
        except: idea sigue pendiente; fallo parcial conserva lo ya procesado (caso 6)

# Disparadores bajo demanda (RF-11, decisión #4):
#   - iniciar sesión, - iniciar captura, - solicitar mejora (RF-8), - abrir idea pendiente

func AJUSTAR_EN_CHAT(idea):                          # RF-13
    if NO ASISTENTE_DISPONIBLE(): devolver EDICION_MANUAL(idea)   # RF-9
    conversacion = reabrir_sobre(idea)               # no es nueva captura (RF-2)
    aplicar cambios como IdeaVersion(requestedBy=adjustment, status=PENDIENTE)

func SOLICITAR_MEJORA(idea, instruccion):            # RF-8
    if NO ASISTENTE_DISPONIBLE():
        guardar_solicitud_pendiente(idea, instruccion)  # se procesa en la siguiente verificación (caso 10)
        devolver AVISO("IA no disponible; tu solicitud quedará registrada")
    version = IA.mejorar(idea, instruccion)
    crear IdeaVersion(idea, version, requestedBy=improvement, status=PENDIENTE)  # requiere aceptar/descartar (RF-8)
```

### 4.6 Transiciones de estado de la idea (máquina, RF-10/15/16, RF-27/29, RNF-9)

```
const TRANSICIONES = {
  EN_DESARROLLO:            { request-publication: SOLICITANDO_PUBLICACION },
  SOLICITANDO_PUBLICACION:  { approve: VALIDADA_PUBLICA, reject: EN_DESARROLLO },
  VALIDADA_PUBLICA:         { decide-accepted: ACEPTADA,
                              decide-archived: ARCHIVADA,
                              decide-rejected: RECHAZADA },
  ARCHIVADA:                { reevaluate: VALIDADA_PUBLICA },    # RF-29 (solo el creador)
  ACEPTADA:                 {},                                  # terminal (MVP)
  RECHAZADA:                {}                                   # terminal (MVP; sin reevaluación, §8.7)
}

func TRANSICIONAR(idea, accion, usuario):
    objetivo = TRANSICIONES[idea.state][accion]
    if objetivo == inexistente: lanzar DomainError(409)          # no permitida (RNF-9)
    if accion == reject and comentario vacío: lanzar 400          # RF-16, caso 13
    idea.state = objetivo
    if accion == "approve":
        registrar rastro (publishedBy=usuario, publishedAt=now)   # RNF-8
        dias = LEER_DIAS_DEBATE().debateDays                      # RF-24 (v2.4): días globales vigentes
        ABRIR_DEBATE(idea, publishedAt=now, debateDays=dias)      # RF-24: deadline = +días globales
        # la evaluación IA NO se ejecuta aquí: se genera al cerrarse el debate (RF-26, ver 4.7/4.8)
    if accion == "reject": adjuntar comentario + identificar usuario (RNF-8)
    if accion in [decide-accepted, decide-archived, decide-rejected]:
        # ver DECIDIR_FINAL en 4.9: valida banda (409 caso 27), motivo obligatorio (400 caso 28)
        registrar idea.decision (outcome, reason, score, decidedBy, decidedByName, decidedAt)  # RNF-8
    if accion == "reevaluate":
        idea.decision = null          # conserva debate cerrado + evaluación IA (RF-29, caso 30)
    notificar según evento (RF-18)
    devolver idea
```

### 4.7 Debate de la idea publicada (RF-24, RF-25)

```
const DEBATE_DAYS_DEFECTO = 30                 # v2.4: configuración global, defecto 30
const DEBATE_DAYS_MIN = 1
const DEBATE_DAYS_MAX = 90

func ABRIR_DEBATE(idea, publishedAt, debateDays):
    debate = nuevo Debate(ideaId=idea.id, deadline=publishedAt + debateDays,
                          closed=false, summary=null)
    # el deadline es inmutable: no se recomputa ni al cambiar la configuración ni al releer (v2.4)

func LEER_DEBATE(ideaId, ahora):
    CERRAR_DEBATE(ideaId, ahora)                                   # cierra si llegó el deadline + resumen/evaluación (idempotente)
    debate = cargar_debate(ideaId)
    if debate NO cerrado: REINTENTAR_ASISTENTE_PENDIENTE(debate)   # @asistant (caso 20)
    devolver debate + mensajes ordenados por createdAt

func CERRAR_DEBATE(ideaId, ahora):
    debate = cargar_debate(ideaId)
    if debate no existe: lanzar DomainError(404)
    if debate.closed == false:
        if ahora < debate.deadline: devolver debate                # aún abierto (sin cambios)
        debate.closed = true                                       # cierre automático único (RF-24)
    REINTENTAR_RESUMEN(debate)                                     # solo si tiene mensajes (caso 21)
    GENERAR_EVALUACION(debate.ideaId)                              # RF-26, caso 22 (idempotente; ver 4.8)
    persistir(debate)

func REINTENTAR_RESUMEN(debate):
    if debate.summary: devolver                                    # ya generado
    if debate tiene al menos un mensaje and ASISTENTE_DISPONIBLE():
        debate.summary = IA.resumen_debate(idea, mensajes, contexto_empresa)   # RF-22, RF-24
    si no: debate.summary = null                # se reintenta en la siguiente verificación (RNF-1)

func PUBLICAR_MENSAJE(ideaId, usuario, texto, linkedMessageId):
    debate = LEER_DEBATE(ideaId)                    # cierra si llegó el deadline
    if debate.closed: lanzar DomainError(409)       # RF-24, caso 18
    mensaje = DebateMessage(ideaId, author=usuario.nombre, text=texto,
                            linkedMessageId=linkedMessageId, processed=true)
    solicitud = texto_tras_@asistant(texto)         # None si no empieza por el token
    if solicitud != null y solicitud no vacía:      # invocación inline (v2.5)
        linked = linkedMessageId ? mensaje(linkedMessageId) : null
        if linkedMessageId y linked == null: lanzar 400      # RF-25: enlace inexistente
        mensaje = pedir_asistente(ideaId, mensaje, linked, solicitud)
    persistir(mensaje)
    devolver mensaje

func PEDIR_ASISTENTE(ideaId, mensaje, linked, solicitud):
    if ASISTENTE_DISPONIBLE():
        respuesta = IA.debate_criterio(contexto_empresa, idea, linked, solicitud)  # RF-22, RF-25 (linked opcional)
        persistir(mensaje)
        asistente = DebateMessage(author="Asistente (IA)", text=respuesta,
                                  linkedMessageId=mensaje.id)
        persistir(asistente)
        devolver asistente                              # el debate sigue operando (RNF-1)
    si no:
        mensaje.processed = false                      # visible como no procesado (caso 20)
        persistir(mensaje)
        devolver mensaje
        # se reintenta en la siguiente interacción con la IA disponible

func LEER_DIAS_DEBATE():                               # RF-24 (v2.4): configuración global
    registro = cargar_registro_debate_days()           # documento único (patrón D1/D19)
    if registro no existe: devolver { debateDays: DEBATE_DAYS_DEFECTO, updatedBy: null, updatedAt: null }
    devolver registro

func GUARDAR_DIAS_DEBATE(admin, valor):                # RF-24, RNF-11 (v2.4)
    if no es_entero(valor) or valor < DEBATE_DAYS_MIN or valor > DEBATE_DAYS_MAX:
        lanzar DomainError(422)                        # entero 1–90; booleanos rechazados
    registro = { debateDays: valor, updatedBy: admin.id, updatedAt: now }  # auditado (RNF-11)
    persistir_registro_debate_days(registro)
    devolver registro
    # solo afecta a los debates abiertos a partir de ahora: los existentes conservan su deadline
```

### 4.8 Evaluación de la IA al cerrarse el debate + decisión del especialista (RF-26)

```
const CRITERIOS = [claridadDelProblema, factibilidad, impactoEsperado,
                   alineacionEstrategica, gradoDeInnovacion]      # fijos (RF-26, D15 spec)

func GENERAR_EVALUACION(ideaId):                        # se dispara al CERRARSE el debate (RF-26, 4.7)
    idea = cargar(ideaId)
    if idea.evaluation?.status in [GENERADA, ACEPTADA, SUSTITUIDA]: devolver   # guarda: nunca sobreescribe (idempotente)
    if NO ASISTENTE_DISPONIBLE():
        idea.evaluation = { status: PENDING }           # el cierre NO se bloquea (caso 22)
        persistir(idea)
        devolver                                        # se genera en la siguiente verificación (RNF-1)
    criterios = IA.evaluar_idea(contexto_empresa, idea)  # RF-22: 5 criterios, score 1–10 + justificación
    if criterios no interpretable: idea.evaluation = { status: PENDING }; persistir(idea); devolver   # caso 22
    idea.evaluation = IdeaEvaluation(criteria=criterios,
                                      author="Asistente (IA)", createdAt=now,
                                      status=GENERADA, decidedBy=null, decidedAt=null)
    idea.aiEvaluation = idea.evaluation.copy()          # instantánea inmutable (visible en el detalle)
    persistir(idea)
    NOTIFICAR_CALIBRACION_PENDIENTE(idea)               # v2.2 (RF-27/RF-18): la idea vuelve a la cola
                                                        # y se avisa a todos los especialistas (1 vez, guard idempotente)

func REINTENTAR_EVALUACIONES_PENDIENTES():              # cada verificación de disponibilidad (RF-11 triggers) + cada lectura de debate cerrado
    for ideaId in ideas con evaluation?.status == PENDING:
        if ASISTENTE_DISPONIBLE(): GENERAR_EVALUACION(ideaId)

func ACEPTAR_EVALUACION_IA(ideaId, especialista):
    idea = cargar(ideaId)
    if idea.aiEvaluation == null: lanzar 409      # nada que aceptar (la evaluación IA no existe aún)
    idea.evaluation = idea.aiEvaluation.copy()
    idea.evaluation.status = ACEPTADA
    idea.evaluation.decidedBy = especialista.id                    # juicio final = última acción (caso 23)
    idea.evaluation.decidedAt = now
    persistir(idea)                                                # RNF-8, RNF-11

func SUSTITUIR_EVALUACION(ideaId, especialista, criterios):
    validar que criterios == los 5 fijos y score en 1–10                          # 422 EVALUATION_INVALID + details.problems (RNF-5)
    idea = cargar(ideaId)
    idea.evaluation = IdeaEvaluation(criteria=criterios, author=especialista.nombre,
                                      createdAt=now, status=SUSTITUIDA,
                                      decidedBy=especialista.id, decidedAt=now)
    persistir(idea)                                                # juicio final = última acción (caso 23); la instantánea aiEvaluation NO se toca
```

### 4.9 Decisión final, umbrales y reevaluación (v2.2, RF-27/RF-28/RF-29)

```
const UMBRAL_DEFECTO = EvaluationThreshold(rejectionThreshold=4, acceptanceThreshold=7)  # RF-28, caso 31

func PROMEDIO(evaluacion):                                     # RF-28: promedio simple de los 5 criterios
    return sum(c.score for c in evaluacion.criteria) / len(evaluacion.criteria)   # 2 decimales

func BANDA(promedio, umbral):                                  # RF-28, caso 26 (banda cerrada por arriba)
    if promedio < umbral.rejectionThreshold:  return RECHAZADA
    if promedio >= umbral.acceptanceThreshold: return ACEPTADA
    return ARCHIVADA

func DECIDIR_FINAL(ideaId, especialista, outcome, reason):     # RF-27 (endpoint POST /validation/{id}/decision)
    validar outcome in [ACEPTADA, ARCHIVADA, RECHAZADA]        # 422 DECISION_INVALID
    idea = cargar(ideaId)
    if idea.state != VALIDADA_PUBLICA: lanzar DomainError(409)  # RNF-9 (solo la etapa de calificación)
    if idea.evaluation == null or idea.evaluation.status == PENDING:
        lanzar DomainError(409)                                 # aún sin calificación vigente (caso 22 en curso)
    if outcome in [ARCHIVADA, RECHAZADA] and reason vacío: lanzar 400   # motivo obligatorio (RF-27, caso 28)
    umbral = cargar_umbral()
    promedio = PROMEDIO(idea.evaluation)
    if BANDA(promedio, umbral) != outcome:                     # RF-27/RF-28, caso 27: nunca se fuerza
        lanzar DomainError(409, "DECISION_MISMATCH", details={score: promedio, band: BANDA(…)})
    TRANSICIONAR(idea, f"decide-{outcome.lower()}", especialista)     # 4.6: escribe idea.decision
    notificar al creador: IDEA_ACCEPTED (con nota) / IDEA_ARCHIVED (motivo) / IDEA_REJECTED (motivo, etapa calificación)  # RF-18

func CARGAR_UMBRAL():                                          # RF-28
    return store_umbral.leer() or UMBRAL_DEFECTO               # si aún no se guardó, el defecto 4/7

func GUARDAR_UMBRAL(admin, rejectionThreshold, acceptanceThreshold):   # RF-28 (endpoint PUT /admin/…)
    if no enteros 1–10 o rejectionThreshold >= acceptanceThreshold: lanzar 422 THRESHOLDS_INVALID
    store_umbral.escribir(EvaluationThreshold(…), updatedBy=admin.id, updatedAt=now)   # RNF-8

func REEVALUAR(ideaId, usuario):                               # RF-29 (endpoint POST /ideas/{id}/request-reevaluation)
    idea = cargar(ideaId)
    if usuario.id != idea.ownerId: lanzar 403                  # solo el creador (segregación RNF-7)
    if idea.state != ARCHIVADA: lanzar DomainError(409)         # caso 29: ACEPTADA/RECHAZADA no admiten reevaluación
    TRANSICIONAR(idea, "reevaluate", usuario)                   # 4.6: state=VALIDADA_PUBLICA, decision=null
    # conserva debate cerrado + evaluación IA (RF-29, caso 30): vuelve a la cola de calificación (RF-14)
    notificar al creador IDEA_REEVALUATED                       # RF-18: "tu idea vuelve a la cola de calificación"
    devolver idea

func NOTIFICAR_CALIBRACION_PENDIENTE(idea):                    # RF-27/RF-18 (tras GENERAR_EVALUACION, 4.8)
    if idea ya notificada como pendiente de calificación: devolver   # guard idempotente (RNF-9)
    for especialista in usuarios_con_rol("especialista"):
        crear_notification(specialista, IDEA_CALIBRATION_PENDING, idea.id, "…")
```

> La **cola de calificación** (RF-14, endpoint `GET /validation/queue?stage=calibracion`) es derivada, no persistida: lista las ideas `VALIDADA_PUBLICA` con debate **cerrado**, `evaluation.status != PENDING` y `decision == null`. Al decidir (4.9) o al reevaluar, la idea entra/sale de la cola de forma coherente con el estado (RNF-9).

**Trazabilidad RF — Lógica de orquestación**

| Bloque pseudocódigo | RF cubiertas |
|---|---|
| 4.1 máquina de estados chatbot | RF-2, RF-3, RF-6 |
| 4.2 sugerencias rápidas | RF-5 |
| 4.3 sugerencia de título | RF-4 |
| 4.4 detección de caídas / manual | RF-7 (RNF-1, RNF-3) |
| 4.5 clarificación posterior | RF-11, RF-12, RF-13, RF-8 |
| 4.6 transiciones de idea | RF-10, RF-15, RF-16 (RNF-8, RNF-9) + RF-24 (apertura del debate) + RF-27/RF-29 (transiciones finales y reevaluación) |
| 4.7 debate de la idea publicada | RF-24, RF-25 (RNF-1, RNF-11, RNF-3) + RF-26 (disparo de la evaluación al cerrarse) |
| 4.8 evaluación IA + decisión especialista | RF-26 (RNF-1, RNF-5, RNF-8, RNF-11) + RF-27 (notificación de calificación pendiente) |
| 4.9 decisión final, umbrales y reevaluación (v2.2) | RF-27, RF-28, RF-29, RF-18 (RNF-7, RNF-8, RNF-9), casos 26–31 |

---

## 5. Decisiones técnicas justificadas

| # | Decisión adoptada | Alternativa(s) descartada(s) | Motivo |
|---|---|---|---|
| D1 | **Persistencia por JSON** (abstracción estándar en `shared/utils/persistence.py`), un archivo JSON por entidad / ruta | BD relacional (SQLite / PostgreSQL), ORM (SQLAlchemy) | Constitución §6.1 prohíbe dependencias externas ajenas a fastapi/pydantic/uvicorn/pytest; `sqlite3` (stdlib) fue descartado por falta de un ecosistema de esquema JSON nativo y para mantener la capa `infrastructure` sin librerías ajenas. El JSON por ruta satisface el alcance del MVP. Se deja documentado como sustitución futura. |
| D2 | **Cliente Ollama nativo** (stdlib, p. ej. `urllib`/http.client) | Librería cliente de Ollama, `requests`, `httpx` | Constitución §6.1: solo stdlib + dependencias base. La llamada a Ollama es un POST HTTP simple (modelo + mensajes), resoluble sin paquete. |
| D3 | **Sesiones por token (portador)** almacenado en `infrastructure/token_store.py` | JWT firmado (requiere `pyjwt`), cookies de sesión propias del servidor | `pyjwt` está fuera de las dependencias permitidas (§6.1). Un token opaco con store propio evita la dependencia y cumple RF-1 (login/logout/sesiones). |
| D4 | **No hay borradores** | Borrador persistente de conversación/idea | Decisión explícita de la spec (RF-6/RF-7, §8.5, caso 7): la idea existe solo al registrar. Simplifica el modelo: `IdeaVersion` solo para versiones IA ya registradas. |
| D5 | **Refinamiento bajo demanda (régimen perezoso)** | Tarea/worker de fondo que vigila la IA | Decisión #4 de la spec: verifica al iniciar sesión, al iniciar captura, al pedir mejora, al abrir idea pendiente. Elimina un componente de orquestación persistente; no añade dependencias de programación (cero nuevas). |
| D6 | **Cola de refinamiento y validación en el backend** | Cola en el frontend | La operación debe ser atómica y consistente (RNF-9); el cliente no puede garantizar la consistencia de transiciones. |
| D7 | **Opciones rápidas (chips) generadas por la IA por turno**, enraizadas en el contexto de empresa (perfil como sección del documento, RF-22) + campos capturados | Chips como catálogo fijo por campo (D7 original, superada) | Sustitución aprobada: las opciones son contextuales y no requieren catálogo curado; el chip solo vale si se ofreció en el turno (400 en caso contrario) y la IA que degrada a `quickOptions: []` nunca rompe el flujo. La misma llamada IA compacta los campos libres ya capturados. Determinístico en tests con el helper `turn_options_json`. |
| D8 | **Validación Pydantic solo en la capa `routers/`** | Esquemas en toda la capa | Constitución §4.2: `domain/` es puro, sin FastAPI/Pydantic. La validación de entrada/salida (Guía Backend §1) vive en `routers/`, y las reglas de negocio en `domain/`. |
| D9 | **Notificaciones en-app** (feature propia) | Notificaciones por correo / websocket | Out-scope de la spec (§8.6). In-app es suficiente y evita canal externo; un websocket añadiría complejidad y (posiblemente) dependencias. |
| D10 | **Derivación de contraseña con stdlib** (p. ej. hashing del módulo `hashlib`) | `bcrypt`, `argon2` | Constitución §6.1. `hashlib` (stdlib) + salt cubre el hash de contraseña sin paquetes. Documentado como riesgo a reforzar en producción. |
| D11 | **Modelo de 6 campos:** se retira *Recursos estimados* de todo el sistema (no se captura, no se valida, no se expone); ideas antiguas con el campo se leen descártandolo (migración silenciosa en el store). Decisión de la spec 11 (reversible). | 7 campos (v2.0) | La spec v2.1 lo elimina del alcance; mantenerlo exigiría UI, validación y prompts innecesarios. La reversibilidad queda documentada en `specs/` (futuro reintroducción). |
| D12 | **Debate y evaluación como atributos de la idea publicada, no estados:** el debate vive en su propia feature (`debate`) y la evaluación en `ideas`/`validation`; la máquina de estados **no** adquiere los estados *En debate*/*En evaluación* (decisión 12 de la spec). | Estados IDEA_EN_DEBATE / IDEA_EN_EVALUACION con salidas Aprobada/Archivada (esquema v1.0) | Amplía el alcance sin romper el ciclo de vida MVP; el debate se cierra por fecha y la evaluación es un juicio final, sin transiciones de estado (RNF-9 intacta). |
| D13 | **Contexto de empresa como único documento** (plantilla + edición en línea + subida de archivo que lo reemplaza en su totalidad) en la feature `org`, inyectado en **todas** las operaciones de la IA; el perfil v2.0 queda como sección del documento (decisión 13 de la spec). | Extender el perfil v2.0 sin sección de guía; o documento por sección | Un solo documento es lo que pidió el propietario (RF-21); garantiza la coherencia de lo que la IA inyecta (RF-22, RNF-12) y evita la fragmentación del perfil. |
| D14 | **Subida de contexto como JSON** (el frontend lee el archivo y envía `content` en el cuerpo) | `multipart/form-data` con `python-multipart` | Constitución §6.1: las dependencias permitidas no incluyen `python-multipart`; un campo JSON evita añadir un paquete y es suficiente para texto. |
| D15 | **Cierre automático del debate en la primera lectura tras el deadline** (no hay worker ni programador); la duración la fija la **configuración global de días de debate** (v2.4). | Tiempo de cierre por cron/worker; debate sin cierre | Sin dependencias de programación (C5) y el estado siempre es coherente al ser leído (RNF-9). |
| D16 | **Catálogo compacto + vista de detalle:** `GET /catalog/public` expone solo título, fecha de publicación y descripción; `GET /catalog/{ideaId}` entrega los 6 campos, el debate y la evaluación (decisiones 16/23 de la spec). | Catálogo completo (todos los datos) | El propietario pidió una listado ligero y el detalle completo; la segregación de datos no cambia (sin contacto en ninguno). |
| D17 | **Evaluación única por idea con juicio final alterable:** la IA genera 5 criterios **al cerrarse el debate** (o queda `PENDING` si la IA cae; el cierre no se bloquea); el especialista **acepta** (vuelve a poner la de la IA como juicio final) o **sustituye** (nueva sobre los mismos 5 criterios, sin tocar la instantánea `aiEvaluation`) en cualquier orden, cada acción auditada (caso 23). | Generación al publicar (descartada: la evaluación se alinea con el cierre del debate, momento en que ya hay discusión de la que dar cuenta); solo aceptación (sin sustitución); scoring global 0–100 | Cumple RF-26 y el caso 23 de la spec; el scoring global está explícitamente fuera (spec §8.2). |
| D18 | **Decisión final atada al promedio:** el resultado final (`ACEPTADA`/`ARCHIVADA`/`RECHAZADA`) debe **coincidir** con la banda del promedio de la evaluación vigente (RF-27/RF-28); el endpoint `POST /validation/{id}/decision` devuelve **409 `DECISION_MISMATCH`** si no coincide (el especialista debe ajustar la puntuación) y **400** si falta el motivo en `ARCHIVADA`/`RECHAZADA`. El promedio y la banda se exponen en la respuesta para la vista en vivo del frontend. | Permitir forzar el resultado aunque contradiga los puntos (descartado: rompería la trazabilidad decisión↔puntuación y el RNF-8); decisión sin confirmación (descartado: la spec exige el aviso explícito) | Cumple RF-27/RF-28 y los casos 26–28 de la spec; el frontend hace el mismo cálculo cliente para la vista en vivo (idéntica regla pura compartida en la capa de dominio). |
| D19 | **Umbrales como documento único persistido** (mismo patrón JSON por entidad, D1) con defecto **4/7**, invariante `rejectionThreshold < acceptanceThreshold` (422 al guardar), auditado (RNF-8) y aplicado solo a decisiones posteriores (caso 31). | Umbrales por idea (descartado: la spec dice configurables por el administrador, globales); rangos flotantes (descartado: la spec exige enteros 1–10) | Cumple RF-28 con la mínima superficie: un registro + 2 endpoints admin. |
| D20 | **`Idea.decision` como atributo de la idea** (no entidad aparte): `{outcome, reason, score, decidedBy, decidedByName, decidedAt}`; se limpia a `null` al reevaluar una `ARCHIVADA` (RF-29, caso 30). Los estados finales son salidas reales de la máquina (4.6), no atributos. | Entidad `Decision` con historial (descartado para el MVP: una decisión vigente por idea basta; el historial queda fuera de alcance); sin estados finales (descartado: la spec v2.2 los introduce) | Minimiza el modelo (D1) y mantiene RNF-9 intacta: la reevaluación es una transición legítima `ARCHIVADA → VALIDADA_PUBLICA`. |
| D21 | **Catálogo por zonas derivado del estado:** `GET /catalog/public?zone=…` filtra por estado (en-proceso=`VALIDADA_PUBLICA`, aceptadas/rechazadas/archivadas=estados finales); el detalle `GET /catalog/{ideaId}` acepta los 4 estados y expone `state` + `decision`. | Cuatro colecciones persistidas por zona (descartado: duplicaría datos); catálogo solo de VALIDADA_PUBLICA (descartado: la spec v2.2 organiza en 4 zonas) | Un solo origen de verdad (`Idea.state`); la zona es proyección, no almacenamiento (coherente con RNF-5/D1). |
| D22 | **Cierre del ciclo de captura (v2.3):** `POST /capture/start` retoma la conversación en curso (ACTIVA primero, luego la RESUMEN más reciente devolviendo el **resumen editable** — campos ya capturados no se pierden) y `POST /capture/abandon` termina la conversación (ACTIVA/RESUMEN/CONTINGENCIA) **sin guardar nada** (sin borradores, D4), idempotente y solo sobre la conversación del propio usuario (403/404). | Sin retoma de RESUMEN (descartado: el usuario perdía los 6 campos capturados al volver a `start` y tener que rehacer la captura); abandono solo cerrando la página (descartado: no se liberaba el límite de una conversación y la conversación RESUMEN huérfana bloqueaba capturas futuras) | El límite de una conversación a la vez (RF-2) se libera solo terminando la conversación; la retoma con resumen mantiene el RNF-10 (sin pérdida) y reutiliza el resumen editable existente (RF-6) sin nueva entidad ni borrador (D4 intacta). |
| D23 | **Días de debate como configuración global (v2.4):** un registro único (`debateDays`, entero 1–90, defecto 30, auditado `updatedBy`/`updatedAt`) gestionado por `GET/PUT /admin/debate-days` (misma forma que los umbrales, D19); `open_debate` fija el `deadline = publishedAt + debateDays` con el valor vigente al abrirlo y **no se recomputa** (ni al cambiar la configuración, ni al releer); los debates existentes conservan su `deadline` almacenado (sin migración). Se retiran `PUT /admin/ideas/{ideaId}/debate/deadline`, `adjust_deadline`, `DebateDeadlineRequest` y `Debate.adjustments`. | Ajuste de deadline idea por idea (v2.3; descartado: el propietario pidió sustituirlo por una configuración global); recomputar el deadline al cambiar los días globales (descartado: rompería los debates existentes y el RNF-9) | El deadline es un atributo fijo del debate (D12 intacto); la duración es global y administrable (RF-24); la regla pura de validación vive en `debate/domain/` y el store/auditado en `infrastructure/` (D8); el wiring por feature evita imports cruzados (D12). |

**Trazabilidad RF — Decisiones**

| Decisión | RF / RN afectadas |
|---|---|
| D1 | Todas las de persistencia (RF-1…RF-26) |
| D2 | RF-3, RF-4, RF-8, RF-11, RF-25, RF-26 |
| D3 | RF-1 |
| D4 | RF-6, RF-7 (cero borradores) |
| D5 | RF-8, RF-11, RF-26 (reintento de evaluaciones) |
| D6 | RF-8, RF-10, RF-11, RNF-9 |
| D7 | RF-5 (ahora inyecta el contexto de empresa, RF-22) |
| D8 | Todas (capa dominio) |
| D9 | RF-12, RF-15, RF-16, RF-18 |
| D10 | RF-17 |
| D11 | RF-3, RF-6, RF-7, RF-9, RNF-5 (6 campos) |
| D12 | RF-23, RF-24, RF-26, §5.10 |
| D13 | RF-21, RF-22, RNF-12 |
| D14 | RF-21 |
| D15 | RF-24, RNF-9, RNF-11 |
| D16 | RF-20, RF-23 |
| D17 | RF-26, RNF-8, RNF-11, casos 22/23 |
| D18 | RF-27, RF-28, RNF-8, RNF-9, casos 26/27/28 |
| D19 | RF-28, RNF-8, casos 26/31 |
| D20 | RF-27, RF-29, RNF-8, RNF-9, casos 29/30 |
| D21 | RF-20, RF-23, RF-29 |
| D22 | RF-2, RF-6 (retoma RESUMEN + abandono, v2.3) |
| D23 | RF-24, RNF-11 (días de debate globales, v2.4) |

---

## 6. Estrategia de pruebas

Alineada con la Constitución §6.2 y la regla operativa: **solo backend** con `pytest`; el frontend no tiene suite automatizada. El criterio de finalización 12 exige que `pytest -q` pase.

### 6.1 Alcance de la cobertura

| Capa / objeto | Qué se prueba | Herramienta |
|---|---|---|
| `domain/` de cada feature | Reglas de negocio puras sin I/O: máquina de estados, validaciones, reglas de roles | `pytest` + fixtures |
| `use_cases/` | Casos de uso orquestrando dominio + infrastructures simuladas | `pytest` con mocks de la capa infra |
| `infrastructure/` (clientes) | `ollama_client`, stores, token_store | `pytest` con mocks HTTP / archivos temporales |
| `routers/` (API) | Contratos HTTP, códigos, payloads, flujo chat y fallback | `fastapi.testclient` + JSON |

### 6.2 Estructura de tests

```text
backend/tests/
├── conftest.py                     # fixtures: app, testclient, stores in-mem, ollama mock
├── unit/
│   ├── domain/
│   │   ├── test_state_machine.py   # transiciones válidas/inválidas (RNF-9)
│   │   ├── test_idea_validation.py # 6 campos completos (RNF-5), contacto (caso 12)
│   │   ├── test_evaluation_rules.py# 5 criterios fijos, score 1–10, juicio final (RF-26)
│   │   └── test_role_rules.py      # no dejar sin admin (RF-17)
│   ├── features/
│   │   ├── debate/
    │   │   │   └── test_debate_rules.py # días de debate 1–90 (defecto 30), cierre único (RF-24, v2.4)
│   │   └── org/
│   │       └── test_context.py     # documento único, plantilla, subida reemplaza (RF-21)
│   ├── use_cases/
│   │   ├── test_capture_flow.py    # RF-2..RF-7: orden (6 campos), chips, título, resumen, manual, retoma ACTIVA/RESUMEN y abandono (v2.3)
│   │   ├── test_refinement.py      # RF-8, RF-11, RF-12, RF-13
│   │   ├── test_publication.py     # RF-10, RF-15, RF-16 (la evaluación NO se dispara aquí; se genera al cerrarse el debate, RF-26)
│   │   ├── test_evaluation.py      # PENDING → reintento, aceptar/sustituir en cualquier orden (caso 23)
│   │   └── test_users_roles.py     # RF-17, caso 16
│   └── infra/
│       ├── test_ollama_client.py   # timeout 60s, reintento único, fallo → contingencia (RNF-3)
│       └── test_stores.py          # persistencia JSON (incl. debate.json)
└── api/
    ├── test_auth.py                # RF-1: login/logout/me, 401/403
    ├── test_capture_api.py         # RF-2..RF-7: flujo chat (6 preguntas) + fallback 503 con prellenado
    ├── test_ideas_api.py           # RF-8, RF-9, RF-10, RF-19
    ├── test_validation_api.py      # RF-14..RF-16: cola, aprobar, rechazar (sin comentario → 400)
    ├── test_evaluation_api.py      # RF-26: generación al cierre (PENDING caso 22), reintento, /evaluation/accept (404/409) y /evaluation (403/422)
    ├── test_debate_api.py          # RF-24/RF-25: leer/publicar, @asistant, cierre 409, resumen, casos 18-21
    ├── test_debate_days_api.py     # RF-24 (v2.4): GET/PUT /admin/debate-days (defecto 30, entero 1–90,
    │                               #     422 inválido, 403 no-admin, auditoría RNF-11)
    ├── test_org_context_api.py     # RF-21/RF-22: plantilla, GET/PUT, subida, 403 sin admin,
    │                               #     inyección en prompts (casos 24, 25)
    ├── test_catalog_api.py         # RF-20/RF-23: compacto (título/fecha/descripción) + detalle
    ├── test_prompts.py             # RF-22: cada plantilla incluye contexto o "(sin contexto…)"
    ├── test_notifications_api.py   # RF-18: 4 eventos, contador, marcar leída
    └── test_users_api.py           # RF-17: crear/rol/desactivar
```

### 6.3 Casos límite mapeados a tests (criterio de finalización 11)

| Caso (spec §7) | Test |
|---|---|
| 1. IA no disp. al iniciar | `test_capture_api::test_start_unavailable_returns_manual` |
| 2. Caída a mitad | `test_capture_api::test_midconversation_fallback_prefilled` |
| 5. Indisponibilidad prolongada | `test_refinement::test_manual_publish_without_refine` |
| 6. Fallo refinamiento | `test_refinement::test_partial_failure_keeps_pending` |
| 7. Abandono sin enviar | `test_capture_flow::test_no_draft_saved` + `test_capture_api::test_abandon_closes_the_capture_without_saving` (+ idempotencia/403/404: `test_capture_api::test_abandon_is_idempotent_and_handles_missing_or_foreign`) |
| 8. Una conversación a la vez (v2.3) | `test_capture_flow::test_start_prefers_active_over_summary` + `test_capture_flow::test_start_resumes_a_summary_conversation_with_its_summary` (+ API: `test_capture_api::test_start_after_summary_resumes_with_the_editable_summary`) |
| 13. Rechazo sin comentario | `test_validation_api::test_reject_without_comment_400` |
| 16. Revocación / desactivación | `test_users_roles::test_revoke_keeps_history` |
| 17. Fallo al registrar | `test_capture_api::test_save_failure_no_partial_record` |
| 18. Debate cerrado por límite | `test_debate_api::test_post_after_deadline_409` (y cierre automático en lectura) |
| 19. `@asistant` sin petición | `test_debate_api::test_asistant_token_alone_is_a_plain_message` (token solo; la petición con enlace opcional responde inline) |
| 20. `@asistant` con IA caída | `test_debate_api::test_asistant_down_keeps_the_request_pending` (reintento tras recuperación; + `test_asistant_pending_without_a_link_retries_on_the_next_read`) |
| 21. Cierre sin mensajes | `test_debate_rules::test_close_without_messages_no_summary` |
| 22. IA caída al cerrarse el debate | `test_evaluation::test_generation_down_keeps_the_idea_pending` + `test_evaluation_api::test_closing_with_the_assistant_down_keeps_it_pending_case_22` + `test_evaluation_api::test_pending_evaluation_is_retried_at_the_next_assistant_check` |
| 23. Aceptar/sustituir alternados | `test_evaluation::test_alternate_accept_replace_last_wins` |
| 24. Contexto vacío | `test_org_context_api::test_empty_context_warning` + `test_prompts::test_empty_context_note` |
| 25. Subida sin texto / corrupta | `test_org_context_api::test_upload_empty_rejected` (el vigente no se modifica) |
| 26. Promedio exacto en un umbral | `test_decision_rules::test_score_on_threshold_belongs_to_upper_band` (X → ARCHIVADA, Z → ACEPTADA) |
| 27. Forzar resultado distinto al promedio | `test_decision_api::test_outcome_mismatch_with_average_409` (banda expuesta en `details`) |
| 28. Rechazo/archivo sin motivo | `test_decision_api::test_archive_and_reject_without_reason_400` |
| 29. Reevaluar ACEPTADA/RECHAZADA | `test_reevaluation_api::test_reevaluate_non_archived_409` (y sin acción en la UI, FE) |
| 30. Reevaluar ARCHIVADA con debate cerrado | `test_reevaluation_api::test_reevaluate_archived_keeps_debate_and_evaluation` (decision=null, debate cerrado intacto, evaluación IA intacta) |
| 31. Umbrales con ideas ya decididas | `test_decision_rules::test_threshold_change_does_not_recompute_decided` (decisión previa inalterada) |

### 6.4 Mocks y dependencias en pruebas

* Ollama se **mockea** en `conftest.py` (sin servicio real) para testear el comportamiento de disponibilidad, timeout y refinamiento de forma determinista.
* Los stores usan una variante en memoria (o archivos temporales) para no contaminar.
* Se respetan timeouts configurables (60 s por defecto, RNF-3) para testear el reintento único.

**Trazabilidad RF — Estrategia de pruebas**

| Suite | RF cubiertas |
|---|---|
| unit/domain + unit/use_cases | RF-2…RF-11, RF-24, RF-26, RNF-5, RNF-9, casos 6, 12, 21, 22, 23 |
| unit/features (debate, org) | RF-21, RF-24 (RNF-11) |
| unit/validation (decision_rules) | RF-27, RF-28, RNF-8, RNF-9, casos 26, 31 (v2.2) |
| unit/infra | RF-3, RF-4, RF-8, RF-11 (RNF-3) |
| api/auth | RF-1 |
| api/capture | RF-2…RF-7, casos 1, 2, 7, 17 |
| api/ideas | RF-8, RF-9, RF-10, RF-19 + RF-29 (reevaluación, casos 29/30) |
| api/validation | RF-14 (dos etapas), RF-15, RF-16, RF-26, RF-27 (decisión, casos 27/28) |
| api/evaluation | RF-26, casos 22, 23 |
| api/debate | RF-24, RF-25, casos 18, 19, 20, 21 |
| api/debate-days | RF-24 (v2.4, RNF-11): días globales 1–90, defecto 30, 422/403/401, sin recomputación |
| api/org-context | RF-21, RF-22, casos 24, 25 |
| api/prompts | RF-22 (inyección del contexto) |
| api/catalog | RF-20 (zonas), RF-23 (detalle en los 4 estados) |
| api/notifications | RF-12, RF-15, RF-16, RF-18 (8 eventos: aceptación/archivo/reevaluación/calificación pendiente) |
| api/users | RF-17, caso 16 |
| api/admin-thresholds | RF-28, RNF-8 (umbrales, defecto 4/7, 422 inválidos) |

---

## 7. Matriz de trazabilidad RF → Plan (revisión)

| RF | §1 Estructura | §2 Datos | §3 API | §4 Lógica | §5 Decisiones | §6 Pruebas |
|----|--------------|----------|--------|-----------|----------------|------------|
| RF-1 | auth, interceptors | Session | /auth/* | — | D3 | api/auth |
| RF-2 | capture | Conversation | /capture/start | 4.1 | D6 | api/capture |
| RF-3 | capture (fields-meta) | Conversation, ChatMessage | /capture/messages | 4.1 | D7 | unit+api/capture |
| RF-4 | capture (title-suggestion) | ChatMessage | /capture/messages | 4.3 | D7 | api/capture |
| RF-5 | capture (chips) | ChatMessage | /capture/messages | 4.2 | D7 | api/capture |
| RF-6 | capture (field-summary) | Idea | /capture/finish | 4.1 | D4 | api/capture |
| RF-7 | capture (manual-form) | Idea, Conversation | /ideas, /capture/activate-manual | 4.4 | D1, D4 | api/capture |
| RF-8 | my-ideas (detail) | IdeaVersion | /ideas/{id}/improve, /decide | 4.5 | D5, D6 | api/ideas |
| RF-9 | my-ideas (detail) | Idea | PUT /ideas/{id} | — | D1 | api/ideas |
| RF-10 | my-ideas | Idea | /ideas/{id}/request-publication | 4.6 | D6 | api/ideas |
| RF-11 | my-ideas (refine-view) | IdeaVersion | /assistant/check | 4.5 | D2, D5 | unit+api |
| RF-12 | shared (notification-bell) | Notification | /notifications | 4.5 | D9 | api/notifications |
| RF-13 | my-ideas (refine-view) | IdeaVersion | /decide, /capture | 4.5 | D5 | api/ideas |
| RF-14 | validation (queue) | — | GET /validation/queue (stage) | — | — | api/validation |
| RF-15 | validation (validate-panel) | Idea (rastro) | /validation/{id}/approve | 4.6 | D9 | api/validation |
| RF-16 | validation (validate-panel) | Idea (comentario) | /validation/{id}/reject | 4.6 | — | api/validation |
| RF-17 | admin (users) | User | /users/* | — | D3, D10 | api/users |
| RF-18 | shared (notification-bell) | Notification (8 eventos) | /notifications* | 4.8, 4.9 | D9 | api/notifications |
| RF-19 | my-ideas (list) | Idea (decision) | GET /ideas/me, /ideas/{id}/request-reevaluation | 4.9 | D1, D20 | api/ideas |
| RF-20 | catalog (public por zonas) | Idea | GET /catalog/public?zone | — | D1, D16, D21 | api/catalog |
| RF-21 | admin (context), org | CompanyContext | /admin/contexto/* | — | D13, D14 | api/org-context, unit/features/org |
| RF-22 | assistant (prompts), org | CompanyContext | — | 4.2, 4.7, 4.8 (inyección) | D7, D13 | api/prompts, unit |
| RF-23 | catalog (detail) | Idea (decision), Debate, IdeaEvaluation | GET /catalog/{ideaId} | — | D12, D16, D21 | api/catalog |
| RF-24 | debate, admin (debate-days) | Debate, DebateMessage, DebateDays | GET/POST /catalog/{ideaId}/debate, GET/PUT /admin/debate-days | 4.6 (apertura), 4.7 | D12, D15, D23 | unit/features/debate, api/debate |
| RF-25 | debate, assistant | DebateMessage | POST /catalog/{ideaId}/debate | 4.7 | D2, D12 | api/debate, casos 19, 20 |
| RF-26 | validation, debate, assistant | IdeaEvaluation | /validation/{id}/evaluation* | 4.7 (disparo al cierre), 4.8 | D2, D12, D17 | api/evaluation, unit/assistant, casos 22, 23 |
| RF-27 | validation (calibration-panel/decision-form) | Idea.decision | POST /validation/{id}/decision | 4.6, 4.9 | D18, D20 | api/validation, casos 27, 28 |
| RF-28 | admin (calibration-thresholds) | EvaluationThreshold | GET/PUT /admin/calibration-thresholds | 4.9 | D18, D19 | api/admin-thresholds, unit/validation, casos 26, 31 |
| RF-29 | my-ideas, catalog (zones), validation (queue) | Idea (state, decision) | /ideas/{id}/request-reevaluation, /validation/queue, /catalog/public?zone | 4.6, 4.9 | D19, D20, D21 | api/ideas, api/catalog, casos 29, 30 |

**Cobertura:** los 29 RF (RF-1 a RF-29) están cubiertos en todas las 6 secciones del plan; RF-21…RF-26 son de la ampliación v2.1 y RF-27…RF-29 de la ampliación v2.2.

---

## 8. Nota de cumplimiento de la Constitución

* **Independencia del dominio (CC §2.1):** las reglas de negocio (máquina de estados, validaciones, roles) viven en `domain/` sin FastAPI/Pydantic.
* **Encapsulamiento vertical (CC §2.2):** 9 features backend + 6 features frontend, cada una autosuficiente.
* **Alta cohesión / bajo acoplamiento (CC §2.3):** las dependencias inter-feature se resuelven por contratos en `shared/` (p. ej. lectura de idea para `assistant` y `validation`).
* **Enfoque Spec-First (CC §2.4):** este plan deriva de la spec; cualquier cambio de contrato exige actualizar antes `specs/`.
* **Inmutabilidad de contratos (CC §5.2):** los payloads y rutas son los definidos aquí; alterarlos sin actualizar `specs/` está prohibido.
* **Dependencias (CC §6.1) y pruebas (CC §6.2):** solo stdlib + fastapi/pydantic/uvicorn/pytest; pruebas exclusivamente backend.
