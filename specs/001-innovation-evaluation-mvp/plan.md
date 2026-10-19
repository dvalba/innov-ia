# Plan de Implementación Técnico — Innov-IA MVP

**Documento:** specs/001-innovation-evaluation-mvp/plan.md
**Versión:** 1.1
**Depende de:** `specs/001-innovation-evaluation-mvp/spec.md` (v2.1, definitiva) y `docs/CONSTITUTION.md`
**Naturaleza:** Este documento es un plan técnico (arquitectura, contratos y pseudocódigo). No contiene código de implementación y no modifica contratos sin actualizar antes la especificación, conforme a la inmutabilidad de contratos (Constitución §5.2).

Cada sección incluye una **Trazabilidad RF** que asigna explícitamente los requisitos funcionales (RF-1 … RF-26) que cubre.

> **v1.1 (ampliación v2.1):** Incorpora RF-21…RF-26 —contexto de empresa administrable (RF-21) inyectado en
> todas las operaciones de la IA (RF-22), vista de detalle de la idea publicada (RF-23), debate de 30 días con
> `@asistant` (RF-24, RF-25) y evaluación de la IA sobre 5 criterios con aceptación/sustitución del
> especialista (RF-26)—, retira *Recursos estimados* del modelo de la idea (6 campos, decisión 11 de la spec)
> y actualiza secciones 1–7. Los debates y las evaluaciones son **atributos de la idea VALIDADA_PUBLICA, no
> estados** (decisión 12 de la spec).

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
│       │   │   ├── list/             # "Mis ideas": título, fecha, origen, estado
│       │   │   └── detail/           # Detalle + acciones según estado
│       │   ├── components/
│       │   │   ├── idea-card/        # Carta reutilizada también en cola de validación
│       │   │   ├── refine-view/      # Versión refinada vs original + Aceptar/Ajustar
│       │   │   └── reject-note/      # Comentario del especialista (solo si aplica)
│       │   └── services/
│       │       └── my-ideas.service.ts
│       │
│       ├── validation/
│       │   ├── pages/
│       │   │   └── queue/            # Cola de SOLICITANDO_PUBLICACIÓN
│       │   ├── components/
│       │   │   ├── validate-panel/   # Validar / Rechazar + comentario obligatorio
│       │   │   └── idea-card (usar shared si se comparte)  # ver 1.4
│       │   └── services/
│       │       └── validation.service.ts
│       │
│       ├── catalog/
│       │   ├── pages/
│       │   │   ├── public/           # Catálogo COMPACTO (título, fecha publicación, descripción; D16)
│       │   │   └── detail/           # Vista de detalle (RF-23): 6 campos, debate (RF-24/RF-25)
│       │   │                         # y evaluación (RF-26); solo lectura de la idea
│       │   ├── components/
│       │   │   ├── debate/           # Hilo de mensajes, input, selector de mensaje enlazado,
│       │   │   │                     # @asistant, cierre/fecha límite, resumen IA (RF-24/RF-25);
│       │   │   │                     # ajuste inline del límite para rol admin
│       │   │   └── evaluation/       # 5 criterios con score + justificación; aceptar/sustituir
│       │   │                         # para rol especialista (RF-26)
│       │   └── services/
│       │       └── catalog.service.ts
│       │
│       └── admin/
│           ├── pages/
│           │   ├── users/            # Gestión de usuarios y roles
│           │   └── context/          # Contexto de empresa (RF-21): plantilla, edición en línea, subida
│           ├── components/
│           │   ├── user-form/        # Alta / edición de usuario
│           │   ├── role-matrix/      # Asignación/revocación de roles
│           │   └── context-form/     # Secciones del documento: perfil + guía de la IA
│           └── services/
│               └── admin.service.ts
```

**Trazabilidad RF — Estructura frontend**

| Carpeta | RF cubiertas |
|---|---|
| `features/auth` + `shared/interceptors` | RF-1 |
| `features/capture` (chat-assist) | RF-2, RF-3, RF-4, RF-5, RF-6 |
| `features/capture` (manual-form) | RF-7 |
| `features/my-ideas` (detail) | RF-8, RF-9, RF-10, RF-12, RF-13, RF-19 |
| `features/validation` | RF-14, RF-15, RF-16 |
| `features/catalog` (public compacta) | RF-20 |
| `features/catalog` (detail: debate + evaluación) | RF-23, RF-24, RF-25, RF-26 |
| `features/admin` (users) | RF-17 |
| `features/admin` (contexto de empresa) | RF-21, RF-22 |
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
    │   │   └── list_public.py        # (RF-20, compacto D16)
    │   ├── routers/
    │   │   ├── ideas.py
    │   │   └── catalog.py            # Catálogo compacto + detalle (RF-20, RF-23)
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
    │   │   ├── queue_rules.py        # Visibilidad de cola, sin datos de contacto (RF-14)
    │   │   └── evaluation_rules.py   # 5 criterios fijos, decisión única del especialista (RF-26)
    │   ├── use_cases/
    │   │   ├── review_queue.py       # Lista SOLICITANDO_PUBLICACIÓN
    │   │   ├── accept_ai_evaluation.py  # La evaluación IA queda como juicio final (RF-26)
    │   │   └── replace_evaluation.py    # Sustitución por la del especialista (RF-26)
    │   ├── routers/
    │   │   └── validation.py
    │   └── infrastructure/
    │       └── queue_store.py
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
    │   │   └── debate_rules.py       # 30 días por defecto, cierre automático único, ajuste admin auditado
    │   ├── use_cases/
    │   │   ├── open_debate.py        # Crea el debate al publicarse (deadline = publishedAt + 30 d)
    │   │   ├── post_message.py       # Publica mensaje; @asistant enlaza un mensaje (RF-25)
    │   │   ├── list_debate.py        # Mensajes + estado + resumen; cierra si se superó el deadline
    │   │   ├── adjust_deadline.py    # Ajuste por idea (admin; reabrir = fecha futura; auditado)
    │   │   └── close_summary.py      # Al cierre, con mensajes: resumen IA (pendiente si la IA cae)
    │   ├── routers/
    │   │   └── debate.py             # GET/POST /catalog/{ideaId}/debate;
    │   │                             # PUT /admin/ideas/{ideaId}/debate/deadline
    │   └── infrastructure/
    │       └── debate_store.py       # JSON (debates + mensajes) bajo backend/data/
    │
    └── notifications/               # Centro in-app y eventos
        ├── domain/
        │   └── notification.py       # Entidad Notificación + tipos de evento
        ├── use_cases/
        │   ├── create_notification.py # Genera los 4 eventos (RF-18) + fanout a especialistas
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
| `features/ideas` | RF-10, RF-19, RF-20, RF-23 + máquina de estados + evaluación al publicar (RF-26) |
| `features/validation` | RF-14, RF-15, RF-16, RF-26 (aceptar/sustituir evaluación) |
| `features/users` | RF-17 |
| `features/org` | RF-21, RF-22 (contexto de empresa) |
| `features/debate` | RF-24, RF-25 (debate + @asistant + resumen) |
| `features/notifications` | RF-12, RF-15, RF-16, RF-18 |

> **Nota de acoplamiento:** las features solo se comunican mediante contratos definidos en `shared/` (Constitución §3.2/§4.2). Ej.: `assistant` no importará de `ideas`; consumirá un contrato de lectura/expediente de idea expuesto a través de la capa compartida.

### 1.3 Reglas de nombrado aplicadas

* Frontend: *intent over role* — las clases se nombran según propósito (`capture`, `ManualFields`), sin el sufijo `Component` (Guía Angular §6).
* Backend: módulos de dominio puros (`domain/`) libres de FastAPI/Pydantic (Constitución §4.2).

### 1.4 Componentes de feature reutilizados → promotion a `shared/`

Si `idea-card` (usado en `my-ideas`, `validation` y `catalog`) se reutiliza en más de una feature, debe **promoverse** a `shared/components/` (Constitución §3.2). El plan lo define como candidato a promoción para respetar la regla.

**Trazabilidad RF:** estructura completa → RF-1 a RF-26 (cobertura de sección, no de criterio).

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
| `Notification` | Evento in-app | id, user_id, tipo, idea_id, leído, fecha |
| `Session` | Autenticación activa | token, user_id, expiración |
| `CompanyContext` | Contexto de empresa (documento único, RF-21) | perfil (nombre/sector/descripción/misión/objetivos) + texto guía; seed desde `INNOV_ORG_*` |
| `Debate` | Debate de una idea publicada (RF-24) | idea_id, deadline, cerrado, resumen IA, rastro de ajustes (quién/cuándo) |
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
    "state":  { "enum": ["EN_DESARROLLO", "SOLICITANDO_PUBLICACION", "VALIDADA_PUBLICA"], "description": "Máquina de estados" },
    "reviewedByAI":  { "type": "boolean", "default": false },
    "currentVersionId": { "type": ["string", "null"] },

    "createdAt":  { "type": "string", "format": "date-time" },
    "requestDate":{ "type": ["string", "null"], "format": "date-time", "description": "Fecha de solicitud de publicación" },
    "publishedAt":{ "type": ["string", "null"], "format": "date-time", "description": "Fecha de publicación" },
    "publishedBy":{ "type": ["string", "null"], "description": "Quién validó (RNF-8, autovalidación caso 9)" },

    "evaluation": {
      "type": ["object", "null"],
      "description": "Juicio final vigente (RF-26); null hasta el primer intento de generación",
      "properties": {
        "status":      { "enum": ["PENDING", "GENERADA", "ACEPTADA", "SUSTITUIDA"], "description": "PENDING mientras la IA no puede generarla (caso 22); el juicio final es siempre el resultado de la última acción del especialista (caso 23)" },
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
    "type":    { "enum": ["IDEA_REFINED", "IDEA_PUBLISHED", "IDEA_REJECTED", "IDEA_REQUESTED"], "description": "Solo los 4 eventos (RF-18)" },
    "ideaId":  { "type": "string" },
    "message": { "type": "string" },
    "read":    { "type": "boolean", "default": false },
    "createdAt": { "type": "string", "format": "date-time" }
  }
}
```

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
    "deadline":  { "type": "string", "format": "date-time", "description": "publishedAt + 30 días por defecto; ajustable solo por admin (RNF-11)" },
    "closed":    { "type": "boolean", "description": "Cierre automático y definitivo al llegar la fecha límite (solo se ejecuta una vez)" },
    "summary":   { "type": ["string", "null"], "description": "Resumen de la IA de los puntos principales (solo si hubo mensajes; null mientras la IA no puede generarlo)" },
    "adjustments": {
      "type": "array",
      "description": "Rastro de ajustes de la fecha límite (RNF-11): quien, cuándo, valor anterior y nuevo; reabrir = fecha en el futuro",
      "items": {
        "type": "object",
        "required": ["by", "at", "from", "to"],
        "properties": {
          "by":  { "type": "string" },
          "at":  { "type": "string", "format": "date-time" },
          "from": { "type": "string", "format": "date-time" },
          "to":  { "type": "string", "format": "date-time" }
        }
      }
    }
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
| `Idea` | RF-1 (ownerId), RF-10/RF-19/RF-20, RF-15/RF-16 (rastro), RF-26 (evaluación) |
| `ChatMessage` | RF-3, RF-4, RF-5 |
| `Conversation` | RF-2, RF-3, RF-6, RNF-10 |
| `IdeaVersion` | RF-8, RF-11, RF-13 |
| `User` | RF-17 |
| `Notification` | RF-12, RF-15, RF-16, RF-18 |
| `CompanyContext` | RF-21, RF-22 |
| `Debate`, `DebateMessage` | RF-24, RF-25, RNF-11 |
| `IdeaEvaluation` | RF-26, RNF-8, RNF-11 |

---

## 3. Contratos de la API REST

Base: `/api/v1`. Autenticación por **portador de sesión** (RF-1). Todos los payloads son JSON (excepción: `GET /admin/contexto/plantilla` devuelve `text/plain`; la subida de contexto envía el texto como campo JSON para no requerir `multipart`).

### 3.1 Resumen de endpoints

| Método | Ruta | Rol | RF | Descripción |
|---|---|---|---|---|
| POST | `/auth/login` | — | RF-1 | Inicia sesión |
| POST | `/auth/logout` | sesión | RF-1 | Cierra sesión |
| GET  | `/auth/me` | sesión | RF-1 | Datos y roles del usuario |
| POST | `/capture/start` | proponente | RF-2 | Inicia/retoma conversación (IA disponible) |
| GET  | `/capture/assistant-status` | proponente | RF-7 | Estado del asistente (OK/UNAVAILABLE) |
| POST | `/capture/messages` | proponente | RF-3,RF-4,RF-5 | Procesa un mensaje de captura |
| POST | `/capture/finish` | proponente | RF-6 | Registra idea (EN_DESARROLLO) |
| POST | `/capture/activate-manual` | proponente | RF-7 | Convierte conversación en formulario prellenado |
| POST | `/ideas` | proponente | RF-6,RF-7 | Crea idea (origen asistida/manual) |
| GET  | `/ideas/me` | proponente | RF-19 | Lista mis ideas |
| GET  | `/ideas/{id}` | dueño | RF-19 | Detalle de una idea |
| PUT  | `/ideas/{id}` | dueño | RF-9 | Edición manual (6 campos) |
| POST | `/ideas/{id}/improve` | dueño (con IA) | RF-8 | Solicita mejora (versión pendiente) |
| POST | `/ideas/{id}/versions/{vid}/decide` | dueño | RF-8,RF-13 | Aceptar/descartar versión |
| POST | `/ideas/{id}/request-publication` | dueño | RF-10 | Solicita publicación |
| GET  | `/validation/queue` | especialista | RF-14 | Cola en SOLICITANDO_PUBLICACION |
| POST | `/validation/{id}/approve` | especialista | RF-15, RF-24, RF-26 | Valida/publica; abre el debate (30 d) e intenta la evaluación IA |
| POST | `/validation/{id}/reject` | especialista | RF-16 | Rechaza con comentario |
| POST | `/validation/{id}/evaluation/accept` | especialista | RF-26 | Acepta la evaluación de la IA (juicio final) |
| POST | `/validation/{id}/evaluation` | especialista | RF-26 | Sustituye la evaluación vigente por la propia (5 criterios) |
| GET  | `/catalog/public` | sesión | RF-20 | Catálogo COMPACTO: título, fecha de publicación, descripción (D16) |
| GET  | `/catalog/{ideaId}` | sesión | RF-23 | Detalle de una idea publicada: 6 campos, debate y evaluación |
| GET  | `/catalog/{ideaId}/debate` | sesión | RF-24, RF-25 | Mensajes del debate + deadline + cerrado + resumen + rastro |
| POST | `/catalog/{ideaId}/debate` | sesión | RF-24, RF-25 | Publica mensaje (texto, mensaje enlazado para @asistant); 409 si cerrado |
| PUT  | `/admin/ideas/{ideaId}/debate/deadline` | admin | RF-24, RNF-11 | Ajusta la fecha límite (adelantar/extender; reabrir = futuro); auditado |
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
// Entrada (invocación @asistant enlazando un mensaje del hilo)
{ "text": "@asistant ¿cómo se alinea esto con las líneas de innovación del contexto?", "linkedMessageId": "debmsg_003" }
// Salida 201
{ "id": "debmsg_007", "author": "Laura Gómez", "text": "@asistant ¿cómo se alinea…?", "linkedMessageId": "debmsg_003", "createdAt": "…" }
// Salida 201 adicional: el sistema responde en el hilo (RF-25)
{ "id": "debmsg_008", "author": "Asistente (IA)", "text": "…criterio generado con el contexto de empresa…", "linkedMessageId": "debmsg_007", "createdAt": "…" }
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

1. Cliente → `POST /capture/start` → 200 `conversationId` + saludo/primera pregunta (RF-2).
2. Cliente → `POST /capture/messages` con la respuesta.
3. Backend aplica el texto al campo en curso (asignación narrativa, RF-3) y devuelve la siguiente pregunta + opciones rápidas del turno generadas por la IA (RF-5, D7) + sugerencia de título si corresponde (RF-4).
4. Al completar los 6 campos, el último `messages` devuelve `state: RESUMEN` con el resumen editable (RF-6).
5. Cliente → `POST /capture/finish` → 201 idea (EN_DESARROLLO, RF-6).
6. Si en cualquier paso la IA falló → ver §3.4.

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
| capture (start/messages/finish/activate-manual) | RF-2, RF-3, RF-4, RF-5, RF-6, RF-7 |
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
    si usuario tiene conversación ACTIVA:          # límite 1 (RF-2, caso 8)
        devolver conversación existente
    si ASISTENTE_DISPONIBLE():
        conv = nuevo conversation(campos={}, currentField=ORDER[0])
        devolver conv + saludo + pregunta(ORDER[0])  # sin chips: la 1ª llamada IA va en PROCESAR_MENSAJE (D7)
    si no:
        devolver FORMULARIO_MANUAL(campos={})       # RF-7, caso 1

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

### 4.6 Transiciones de estado de la idea (máquina, RF-10/15/16, RNF-9)

```
const TRANSICIONES = {
  EN_DESARROLLO:            { request-publication: SOLICITANDO_PUBLICACION },
  SOLICITANDO_PUBLICACION:  { approve: VALIDADA_PUBLICA, reject: EN_DESARROLLO },
  VALIDADA_PUBLICA:         {}                                   # terminal (MVP)
}

func TRANSICIONAR(idea, accion, usuario):
    objetivo = TRANSICIONES[idea.state][accion]
    if objetivo == inexistente: lanzar DomainError(409)          # no permitida (RNF-9)
    if accion == reject and comentario vacío: lanzar 400          # RF-16, caso 13
    idea.state = objetivo
    if accion == "approve":
        registrar rastro (publishedBy=usuario, publishedAt=now)   # RNF-8
        ABRIR_DEBATE(idea, publishedAt=now)                      # RF-24: deadline = +30 d
        GENERAR_EVALUACION(idea)                                 # RF-26 (no bloquea; ver 4.8)
    if accion == "reject": adjuntar comentario + identificar usuario (RNF-8)
    notificar según evento (RF-18)
    devolver idea
```

### 4.7 Debate de la idea publicada (RF-24, RF-25)

```
const DEFECTO_DEBATE = 30 dias

func ABRIR_DEBATE(idea, publishedAt):
    debate = nuevo Debate(ideaId=idea.id, deadline=publishedAt + DEFECTO_DEBATE,
                          closed=false, summary=null, adjustments=[])

func LEER_DEBATE(ideaId, ahora):
    debate = cargar_debate(ideaId)
    if debate.closed == false and ahora >= debate.deadline:
        debate.closed = true                                       # cierre automático único (RF-24)
        if debate tiene al menos un mensaje:
            CERRAR_CON_RESUMEN(ideaId, debate)
        persistir(debate)
    devolver debate + mensajes ordenados por createdAt

func CERRAR_CON_RESUMEN(ideaId, debate):
    if ASISTENTE_DISPONIBLE():
        debate.summary = IA.resumen_debate(idea, mensajes, contexto_empresa)   # RF-22, RF-24
    si no:
        debate.summary = null                       # se reintenta en la siguiente verificación (RNF-1)

func PUBLICAR_MENSAJE(ideaId, usuario, texto, linkedMessageId):
    debate = LEER_DEBATE(ideaId)                    # cierra si llegó el deadline
    if debate.closed: lanzar DomainError(409)       # RF-24, caso 18
    mensaje = DebateMessage(ideaId, author=usuario.nombre, text=texto,
                            linkedMessageId=linkedMessageId, processed=true)
    if texto empieza con "@asistant":
        if linkedMessageId no existe en el debate: lanzar 400     # RF-25: referencia concreta
        mensaje = pedir_asistente(ideaId, mensaje, debate)
    persistir(mensaje)
    devolver mensaje

func PEDIR_ASISTENTE(ideaId, mensaje, debate):
    if ASISTENTE_DISPONIBLE():
        linked = mensaje(linkedMessageId)
        respuesta = IA.debate_criterio(contexto_empresa, idea, linked, texto_tras_@asistant)  # RF-22, RF-25
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

func AJUSTAR_DEADLINE(ideaId, admin, nuevaFecha):
    debate = cargar_debate(ideaId)
    debate.adjustments.push({ by: admin.id, at: now, from: debate.deadline, to: nuevaFecha })  # RNF-11
    debate.deadline = nuevaFecha
    if nuevaFecha > now: debate.closed = false         # reabrir = ajustar a futuro (RF-24)
    persistir(debate)                                  # el ajuste queda registrado (quién y cuándo)
```

### 4.8 Evaluación de la IA al publicar + decisión del especialista (RF-26)

```
const CRITERIOS = [claridadDelProblema, factibilidad, impactoEsperado,
                   alineacionEstrategica, gradoDeInnovacion]      # fijos (RF-26, D15 spec)

func GENERAR_EVALUACION(idea):
    if NO ASISTENTE_DISPONIBLE():
        idea.evaluation = { status: PENDING }           # la publicación NO se bloquea (caso 22)
        devolver                                          # se genera en la siguiente verificación (RNF-1)
    criterios = IA.evaluar_idea(contexto_empresa, idea)  # RF-22: 5 criterios, score 1–10 + justificación
    idea.evaluation = IdeaEvaluation(criteria=criterios,
                                      author="Asistente (IA)", createdAt=now,
                                      status=GENERADA, decidedBy=null, decidedAt=null)
    persistir(idea)

func REINTENTAR_EVALUACION_PENDIENTE(ideaId):          # llamada en cada verificación de disponibilidad (RF-11 triggers)
    idea = cargar(ideaId)
    if idea.evaluation?.status == PENDING and ASISTENTE_DISPONIBLE():
        GENERAR_EVALUACION(idea)

func ACEPTAR_EVALUACION_IA(ideaId, especialista):
    idea = cargar(ideaId)
    if idea.aiEvaluation == null: lanzar 409      # nada que aceptar (la evaluación IA no existe aún)
    idea.evaluation = idea.aiEvaluation.copy()
    idea.evaluation.status = ACEPTADA
    idea.evaluation.decidedBy = especialista.id                    # juicio final = última acción (caso 23)
    idea.evaluation.decidedAt = now
    persistir(idea)                                                # RNF-8, RNF-11

func SUSTITUIR_EVALUACION(ideaId, especialista, criterios):
    validar que criterios == los 5 fijos y score en 1–10                          # 422 si no (RNF-5)
    idea = cargar(ideaId)
    idea.evaluation = IdeaEvaluation(criteria=criterios, author=especialista.nombre,
                                      createdAt=now, status=SUSTITUIDA,
                                      decidedBy=especialista.id, decidedAt=now)
    persistir(idea)                                                # juicio final = última acción (caso 23)
```

**Trazabilidad RF — Lógica de orquestación**

| Bloque pseudocódigo | RF cubiertas |
|---|---|
| 4.1 máquina de estados chatbot | RF-2, RF-3, RF-6 |
| 4.2 sugerencias rápidas | RF-5 |
| 4.3 sugerencia de título | RF-4 |
| 4.4 detección de caídas / manual | RF-7 (RNF-1, RNF-3) |
| 4.5 clarificación posterior | RF-11, RF-12, RF-13, RF-8 |
| 4.6 transiciones de idea | RF-10, RF-15, RF-16 (RNF-8, RNF-9) + RF-24, RF-26 (disparo) |
| 4.7 debate de la idea publicada | RF-24, RF-25 (RNF-1, RNF-11, RNF-3) |
| 4.8 evaluación IA + decisión especialista | RF-26 (RNF-1, RNF-5, RNF-8, RNF-11) |

**Trazabilidad RF — Lógica de orquestación**

| Bloque pseudocódigo | RF cubiertas |
|---|---|
| 4.1 máquina de estados chatbot | RF-2, RF-3, RF-6 |
| 4.2 sugerencias rápidas | RF-5 |
| 4.3 sugerencia de título | RF-4 |
| 4.4 detección de caídas / manual | RF-7 (RNF-1, RNF-3) |
| 4.5 clarificación posterior | RF-11, RF-12, RF-13, RF-8 |
| 4.6 transiciones de idea | RF-10, RF-15, RF-16 (RNF-8, RNF-9) |

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
| D15 | **Cierre automático del debate en la primera lectura tras el deadline** (no hay worker ni programador); el ajuste de fecha por idea es el único control, auditable (RNF-11). | Tiempo de cierre por cron/worker; debate sin cierre | Sin dependencias de programación (C5) y el estado siempre es coherente al ser leído (RNF-9). |
| D16 | **Catálogo compacto + vista de detalle:** `GET /catalog/public` expone solo título, fecha de publicación y descripción; `GET /catalog/{ideaId}` entrega los 6 campos, el debate y la evaluación (decisiones 16/23 de la spec). | Catálogo completo (todos los datos) | El propietario pidió una listado ligero y el detalle completo; la segregación de datos no cambia (sin contacto en ninguno). |
| D17 | **Evaluación única por idea con juicio final alterable:** la IA genera 5 criterios al publicar (o queda `PENDING` si la IA cae; la validación no se bloquea); el especialista **acepta** (vuelve a poner la de la IA como juicio final) o **sustituye** (nueva sobre los mismos 5 criterios) en cualquier orden, cada acción auditada (caso 23). | Solo aceptación (sin sustitución); scoring global 0–100 | Cumple RF-26 y el caso 23 de la spec; el scoring global está explícitamente fuera (spec §8.2). |

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
│   │   │   └── test_debate_rules.py # 30 d, cierre único, ajuste admin auditado (RF-24)
│   │   └── org/
│   │       └── test_context.py     # documento único, plantilla, subida reemplaza (RF-21)
│   ├── use_cases/
│   │   ├── test_capture_flow.py    # RF-2..RF-7: orden (6 campos), chips, título, resumen, manual
│   │   ├── test_refinement.py      # RF-8, RF-11, RF-12, RF-13
│   │   ├── test_publication.py     # RF-10, RF-15, RF-16 + apertura de debate y evaluación (RF-24/RF-26)
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
    ├── test_evaluation_api.py      # RF-26: /evaluation/accept y /evaluation (403/422/409)
    ├── test_debate_api.py          # RF-24/RF-25: leer/publicar, @asistant, cierre 409, resumen,
    │                               #     PUT deadline admin (reapertura), casos 18-21
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
| 7. Abandono sin enviar | `test_capture_flow::test_no_draft_saved` |
| 13. Rechazo sin comentario | `test_validation_api::test_reject_without_comment_400` |
| 16. Revocación / desactivación | `test_users_roles::test_revoke_keeps_history` |
| 17. Fallo al registrar | `test_capture_api::test_save_failure_no_partial_record` |
| 18. Debate cerrado por límite | `test_debate_api::test_post_after_deadline_409` (y cierre automático en lectura) |
| 19. `@asistant` sin enlazar | `test_debate_api::test_asistant_without_link_treated_as_user` |
| 20. `@asistant` con IA caída | `test_debate_api::test_asistant_ai_down_keeps_unprocessed` (reintento tras recuperación) |
| 21. Cierre sin mensajes | `test_debate_rules::test_close_without_messages_no_summary` |
| 22. IA caída al publicar | `test_evaluation::test_publish_keeps_pending` + `test_evaluation_api::test_pending_generated_on_retry` |
| 23. Aceptar/sustituir alternados | `test_evaluation::test_alternate_accept_replace_last_wins` |
| 24. Contexto vacío | `test_org_context_api::test_empty_context_warning` + `test_prompts::test_empty_context_note` |
| 25. Subida sin texto / corrupta | `test_org_context_api::test_upload_empty_rejected` (el vigente no se modifica) |

### 6.4 Mocks y dependencias en pruebas

* Ollama se **mockea** en `conftest.py` (sin servicio real) para testear el comportamiento de disponibilidad, timeout y refinamiento de forma determinista.
* Los stores usan una variante en memoria (o archivos temporales) para no contaminar.
* Se respetan timeouts configurables (60 s por defecto, RNF-3) para testear el reintento único.

**Trazabilidad RF — Estrategia de pruebas**

| Suite | RF cubiertas |
|---|---|
| unit/domain + unit/use_cases | RF-2…RF-11, RF-24, RF-26, RNF-5, RNF-9, casos 6, 12, 21, 22, 23 |
| unit/features (debate, org) | RF-21, RF-24 (RNF-11) |
| unit/infra | RF-3, RF-4, RF-8, RF-11 (RNF-3) |
| api/auth | RF-1 |
| api/capture | RF-2…RF-7, casos 1, 2, 7, 17 |
| api/ideas | RF-8, RF-9, RF-10, RF-19 |
| api/validation | RF-14, RF-15, RF-16, caso 13 |
| api/evaluation | RF-26, casos 22, 23 |
| api/debate | RF-24, RF-25, casos 18, 19, 20, 21 |
| api/org-context | RF-21, RF-22, casos 24, 25 |
| api/prompts | RF-22 (inyección del contexto) |
| api/catalog | RF-20, RF-23 |
| api/notifications | RF-12, RF-15, RF-16, RF-18 |
| api/users | RF-17, caso 16 |

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
| RF-14 | validation (queue) | — | GET /validation/queue | — | — | api/validation |
| RF-15 | validation (validate-panel) | Idea (rastro) | /validation/{id}/approve | 4.6 | D9 | api/validation |
| RF-16 | validation (validate-panel) | Idea (comentario) | /validation/{id}/reject | 4.6 | — | api/validation |
| RF-17 | admin (users) | User | /users/* | — | D3, D10 | api/users |
| RF-18 | shared (notification-bell) | Notification | /notifications* | — | D9 | api/notifications |
| RF-19 | my-ideas (list) | Idea | GET /ideas/me | — | D1 | api/ideas |
| RF-20 | catalog (public compacta) | Idea | GET /catalog/public | — | D1, D16 | api/catalog |
| RF-21 | admin (context), org | CompanyContext | /admin/contexto/* | — | D13, D14 | api/org-context, unit/features/org |
| RF-22 | assistant (prompts), org | CompanyContext | — | 4.2, 4.7, 4.8 (inyección) | D7, D13 | api/prompts, unit |
| RF-23 | catalog (detail) | Idea, Debate, IdeaEvaluation | GET /catalog/{ideaId} | — | D12, D16 | api/catalog |
| RF-24 | debate | Debate, DebateMessage | GET/POST /catalog/{ideaId}/debate, PUT deadline | 4.6 (apertura), 4.7 | D12, D15 | unit/features/debate, api/debate |
| RF-25 | debate, assistant | DebateMessage | POST /catalog/{ideaId}/debate | 4.7 | D2, D12 | api/debate, casos 19, 20 |
| RF-26 | validation, ideas, assistant | IdeaEvaluation | /validation/{id}/evaluation* | 4.6 (disparo), 4.8 | D2, D12, D17 | api/evaluation, unit/use_cases, casos 22, 23 |

**Cobertura:** los 26 RF (RF-1 a RF-26) están cubiertos en todas las 6 secciones del plan; RF-21…RF-26 son de la ampliación v2.1.

---

## 8. Nota de cumplimiento de la Constitución

* **Independencia del dominio (CC §2.1):** las reglas de negocio (máquina de estados, validaciones, roles) viven en `domain/` sin FastAPI/Pydantic.
* **Encapsulamiento vertical (CC §2.2):** 9 features backend + 6 features frontend, cada una autosuficiente.
* **Alta cohesión / bajo acoplamiento (CC §2.3):** las dependencias inter-feature se resuelven por contratos en `shared/` (p. ej. lectura de idea para `assistant` y `validation`).
* **Enfoque Spec-First (CC §2.4):** este plan deriva de la spec; cualquier cambio de contrato exige actualizar antes `specs/`.
* **Inmutabilidad de contratos (CC §5.2):** los payloads y rutas son los definidos aquí; alterarlos sin actualizar `specs/` está prohibido.
* **Dependencias (CC §6.1) y pruebas (CC §6.2):** solo stdlib + fastapi/pydantic/uvicorn/pytest; pruebas exclusivamente backend.
