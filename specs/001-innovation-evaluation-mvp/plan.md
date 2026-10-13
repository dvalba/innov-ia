# Plan de Implementación Técnico — Innov-IA MVP

**Documento:** specs/001-innovation-evaluation-mvp/plan.md
**Versión:** 1.0
**Depende de:** `specs/001-innovation-evaluation-mvp/spec.md` (v2.0, definitiva) y `docs/CONSTITUTION.md`
**Naturaleza:** Este documento es un plan técnico (arquitectura, contratos y pseudocódigo). No contiene código de implementación y no modifica contratos sin actualizar antes la especificación, conforme a la inmutabilidad de contratos (Constitución §5.2).

Cada sección incluye una **Trazabilidad RF** que asigna explícitamente los requisitos funcionales (RF-1 … RF-20) que cubre.

---

## 1. Estructura de módulos y carpetas

Organización técnica exacta según la Clean Architecture por características (Constitución §§ 3 y 4). Se identifican **seis features frontend** y **siete features backend** que cubren el alcance de la spec.

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
│       │   │   ├── field-summary/    # Resumen editable de los 7 campos (RF-6)
│       │   │   └── manual-fields/    # 7 campos obligatorios
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
│       │   │   └── public/           # Catálogo de VALIDADA_PUBLICA (solo lectura)
│       │   └── services/
│       │       └── catalog.service.ts
│       │
│       └── admin/
│           ├── pages/
│           │   └── users/            # Gestión de usuarios y roles
│           ├── components/
│           │   ├── user-form/        # Alta / edición de usuario
│           │   └── role-matrix/      # Asignación/revocación de roles
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
| `features/catalog` | RF-20 |
| `features/admin` | RF-17 |
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
    │   │   ├── idea.py               # Entidad Idea (7 campos, origen, estado, atributos)
    │   │   ├── state_machine.py      # Transiciones EN_DESARROLLO→…→VALIDADA_PUBLICA
    │   │   └── validate.py           # Reglas de campos completos, contacto válido
    │   ├── use_cases/
    │   │   ├── create_idea.py        # Creación desde captura (asistida o manual)
    │   │   ├── edit_idea.py          # Edición manual (RF-9) + bloqueo durante generación
    │   │   ├── request_publication.py# Transición única a SOLICITANDO_PUBLICACIÓN (RF-10)
    │   │   ├── approve_idea.py       # VALIDADA_PUBLICA + rastro + notificación (RF-15)
    │   │   ├── reject_idea.py        # Devolución + comentario obligatorio (RF-16)
    │   │   ├── list_my_ideas.py      # (RF-19)
    │   │   └── list_public.py        # (RF-20)
    │   ├── routers/
    │   │   └── ideas.py
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
    │   │   └── queue_rules.py        # Visibilidad de cola, sin datos de contacto (RF-14)
    │   ├── use_cases/
    │   │   └── review_queue.py       # Lista SOLICITANDO_PUBLICACIÓN
    │   ├── routers/
    │   │   └── validation.py
    │   └── infrastructure/
    │       └── queue_store.py
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
| `features/assistant` | RF-3 (asignación), RF-4, RF-8, RF-11, RF-12 |
| `features/ideas` | RF-10, RF-19, RF-20 + máquina de estados |
| `features/validation` | RF-14, RF-15, RF-16 |
| `features/users` | RF-17 |
| `features/notifications` | RF-12, RF-15, RF-16, RF-18 |

> **Nota de acoplamiento:** las features solo se comunican mediante contratos definidos en `shared/` (Constitución §3.2/§4.2). Ej.: `assistant` no importará de `ideas`; consumirá un contrato de lectura/expediente de idea expuesto a través de la capa compartida.

### 1.3 Reglas de nombrado aplicadas

* Frontend: *intent over role* — las clases se nombran según propósito (`capture`, `ManualFields`), sin el sufijo `Component` (Guía Angular §6).
* Backend: módulos de dominio puros (`domain/`) libres de FastAPI/Pydantic (Constitución §4.2).

### 1.4 Componentes de feature reutilizados → promotion a `shared/`

Si `idea-card` (usado en `my-ideas`, `validation` y `catalog`) se reutiliza en más de una feature, debe **promoverse** a `shared/components/` (Constitución §3.2). El plan lo define como candidato a promoción para respetar la regla.

**Trazabilidad RF:** estructura completa → RF-1 a RF-20 (cobertura de sección, no de criterio).

---

## 2. Modelo de datos y esquemas JSON

### 2.1 Entidades principales

| Entidad | Propósito | Campos esenciales |
|---|---|---|
| `Idea` | Unidad de negocio (los 7 campos + estado) | id, campos, owner_id, origen, estado, timestamps, rastro |
| `ChatMessage` | Mensaje de la conversación de captura | id, conversation_id, role, contenido, quickOptions (opciones del turno, D7), sugerencia de título |
| `Conversation` | Sesión de captura activa | id, user_id, estado, campos capturados, turno de campo |
| `IdeaVersion` | Versión vigente/refinada de una idea (aceptada/descartada) | id, idea_id, versión, campos, origen (manual/IA), estado |
| `User` | Cuenta y roles | id, username, nombre, área, datos contacto, roles, habilitado |
| `Notification` | Evento in-app | id, user_id, tipo, idea_id, leído, fecha |
| `Session` | Autenticación activa | token, user_id, expiración |

### 2.2 Esquema JSON — `Idea` (contemplando los 7 campos)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Idea",
  "type": "object",
  "required": [
    "id", "title", "proponent", "description", "problem",
    "expectedBenefit", "strategicAlignment", "estimatedResources",
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
    "estimatedResources": {
      "type": "object",
      "required": ["time", "people", "budget"],
      "properties": {
        "time":    { "type": "string" },
        "people":  { "type": "string" },
        "budget":  { "type": "string" }
      },
      "description": "Campo 7. Tiempo, personal, presupuesto (preliminar)"
    },

    "origin": { "enum": ["asistida", "manual"], "description": "RF-2/RNF-2" },
    "state":  { "enum": ["EN_DESARROLLO", "SOLICITANDO_PUBLICACION", "VALIDADA_PUBLICA"], "description": "Máquina de estados" },
    "reviewedByAI":  { "type": "boolean", "default": false },
    "currentVersionId": { "type": ["string", "null"] },

    "createdAt":  { "type": "string", "format": "date-time" },
    "requestDate":{ "type": ["string", "null"], "format": "date-time", "description": "Fecha de solicitud de publicación" },
    "publishedAt":{ "type": ["string", "null"], "format": "date-time", "description": "Fecha de publicación" },
    "publishedBy":{ "type": ["string", "null"], "description": "Quién validó (RNF-8, autovalidación caso 9)" }
  }
}
```

> `publishedAt`/`publishedBy` son el rastro de auditoría que exige RNF-8. `publishedBy` puede coincidir con `ownerId` sin romper la regla (autovalidación permitida con rastro, RF-15/caso 9).

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
    "currentField":    { "type": ["string", "null"], "description": "Campo en curso: description|title|problem|expectedBenefit|strategicAlignment|estimatedResources|proponent" },
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
      "description": "Los 7 campos propuestos en esta versión",
      "required": ["title","proponent","description","problem","expectedBenefit","strategicAlignment","estimatedResources"]
    },
    "requestedBy": { "enum": ["refinement", "improvement", "adjustment"], "description": "Origen de la versión (RF-11/RF-8/RF-13)" },
    "status":    { "enum": ["PENDIENTE", "ACEPTADA", "DESCARTADA", "VIGENTE"], "description": "Aceptación/descarte explícitos (RF-8, RF-13)" },
    "createdAt": { "type": "string", "format": "date-time" }
  }
}
```

### 2.6 Esquema JSON — ejemplo completo de una Idea con los 7 campos

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
  "estimatedResources": {
    "time": "6 semanas",
    "people": "2 desarrolladores y 1 analista",
    "budget": "50000 PLN"
  },
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

**Trazabilidad RF — Modelo de datos**

| Entidad | RF |
|---|---|
| `Idea` | RF-1 (ownerId), RF-10/RF-19/RF-20, RF-15/RF-16 (rastro) |
| `ChatMessage` | RF-3, RF-4, RF-5 |
| `Conversation` | RF-2, RF-3, RF-6, RNF-10 |
| `IdeaVersion` | RF-8, RF-11, RF-13 |
| `User` | RF-17 |
| `Notification` | RF-12, RF-15, RF-16, RF-18 |

---

## 3. Contratos de la API REST

Base: `/api/v1`. Autenticación por **portador de sesión** (RF-1). Todos los payloads son JSON.

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
| PUT  | `/ideas/{id}` | dueño | RF-9 | Edición manual (7 campos) |
| POST | `/ideas/{id}/improve` | dueño (con IA) | RF-8 | Solicita mejora (versión pendiente) |
| POST | `/ideas/{id}/versions/{vid}/decide` | dueño | RF-8,RF-13 | Aceptar/descartar versión |
| POST | `/ideas/{id}/request-publication` | dueño | RF-10 | Solicita publicación |
| GET  | `/validation/queue` | especialista | RF-14 | Cola en SOLICITANDO_PUBLICACION |
| POST | `/validation/{id}/approve` | especialista | RF-15 | Valida/publica |
| POST | `/validation/{id}/reject` | especialista | RF-16 | Rechaza con comentario |
| GET  | `/catalog/public` | sesión | RF-20 | Catálogo de VALIDADA_PUBLICA |
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
{ "captured": { "title": "…", "description": "…", "problem": "…", "expectedBenefit": "…", "strategicAlignment": "…", "estimatedResources": {"time":"…","people":"…","budget":"…"}, "proponent": {"name":"…","area":"…","contact":"…"} } }
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

### 3.3 Manejo del flujo de chat asistido (secuencia)

1. Cliente → `POST /capture/start` → 200 `conversationId` + saludo/primera pregunta (RF-2).
2. Cliente → `POST /capture/messages` con la respuesta.
3. Backend aplica el texto al campo en curso (asignación narrativa, RF-3) y devuelve la siguiente pregunta + opciones rápidas del turno generadas por la IA (RF-5, D7) + sugerencia de título si corresponde (RF-4).
4. Al completar los 7 campos, el último `messages` devuelve `state: RESUMEN` con el resumen editable (RF-6).
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
ORDER = [description, title, problem, expectedBenefit, strategicAlignment, estimatedResources, proponent]

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
    validar 7 campos completos (RNF-5)
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
    respuesta = IA(turn_options_prompt(campo, conv.capturedFields_texto, perfil_organización))
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
    for idea in COLA_REFINAMIENTO():
        try:
            version = IA.refinar(idea)
            if version valida (7 campos OK):
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
    if accion == "approve": registrar rastro (publishedBy=usuario, publishedAt=now)  # RNF-8
    if accion == "reject": adjuntar comentario + identificar usuario (RNF-8)
    notificar según evento (RF-18)
    devolver idea
```

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
| D7 | **Opciones rápidas (chips) generadas por la IA por turno**, enraizadas en el perfil de organización + campos capturados | Chips como catálogo fijo por campo (D7 original, superada) | Sustitución aprobada: las opciones son contextuales y no requieren catálogo curado; el chip solo vale si se ofreció en el turno (400 en caso contrario) y la IA que degrada a `quickOptions: []` nunca rompe el flujo. La misma llamada IA compacta los campos libres ya capturados. Determinístico en tests con el helper `turn_options_json`. |
| D8 | **Validación Pydantic solo en la capa `routers/`** | Esquemas en toda la capa | Constitución §4.2: `domain/` es puro, sin FastAPI/Pydantic. La validación de entrada/salida (Guía Backend §1) vive en `routers/`, y las reglas de negocio en `domain/`. |
| D9 | **Notificaciones en-app** (feature propia) | Notificaciones por correo / websocket | Out-scope de la spec (§8.6). In-app es suficiente y evita canal externo; un websocket añadiría complejidad y (posiblemente) dependencias. |
| D10 | **Derivación de contraseña con stdlib** (p. ej. hashing del módulo `hashlib`) | `bcrypt`, `argon2` | Constitución §6.1. `hashlib` (stdlib) + salt cubre el hash de contraseña sin paquetes. Documentado como riesgo a reforzar en producción. |

**Trazabilidad RF — Decisiones**

| Decisión | RF / RN afectadas |
|---|---|
| D1 | Todas las de persistencia (RF-1…RF-20) |
| D2 | RF-3, RF-4, RF-8, RF-11 |
| D3 | RF-1 |
| D4 | RF-6, RF-7 (cero borradores) |
| D5 | RF-8, RF-11 |
| D6 | RF-8, RF-10, RF-11, RNF-9 |
| D7 | RF-5 |
| D8 | Todas (capa dominio) |
| D9 | RF-12, RF-15, RF-16, RF-18 |
| D10 | RF-17 |

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
│   │   ├── test_idea_validation.py # 7 campos completos (RNF-5), contacto (caso 12)
│   │   └── test_role_rules.py      # no dejar sin admin (RF-17)
│   ├── use_cases/
│   │   ├── test_capture_flow.py    # RF-2..RF-7: orden, chips, título, resumen, manual
│   │   ├── test_refinement.py      # RF-8, RF-11, RF-12, RF-13
│   │   ├── test_publication.py     # RF-10, RF-15, RF-16
│   │   └── test_users_roles.py     # RF-17, caso 16
│   └── infra/
│       ├── test_ollama_client.py   # timeout 60s, reintento único, fallo → contingencia (RNF-3)
│       └── test_stores.py          # persistencia JSON
└── api/
    ├── test_auth.py                # RF-1: login/logout/me, 401/403
    ├── test_capture_api.py         # RF-2..RF-7: flujo chat + fallback 503 con prellenado
    ├── test_ideas_api.py           # RF-8, RF-9, RF-10, RF-19
    ├── test_validation_api.py      # RF-14..RF-16: cola, aprobar, rechazar (sin comentario → 400)
    ├── test_catalog_api.py         # RF-20: solo VALIDADA_PUBLICA, sin contacto
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

### 6.4 Mocks y dependencias en pruebas

* Ollama se **mockea** en `conftest.py` (sin servicio real) para testear el comportamiento de disponibilidad, timeout y refinamiento de forma determinista.
* Los stores usan una variante en memoria (o archivos temporales) para no contaminar.
* Se respetan timeouts configurables (60 s por defecto, RNF-3) para testear el reintento único.

**Trazabilidad RF — Estrategia de pruebas**

| Suite | RF cubiertas |
|---|---|
| unit/domain + unit/use_cases | RF-2…RF-11, RNF-5, RNF-9, casos 6, 12 |
| unit/infra | RF-3, RF-4, RF-8, RF-11 (RNF-3) |
| api/auth | RF-1 |
| api/capture | RF-2…RF-7, casos 1, 2, 7, 17 |
| api/ideas | RF-8, RF-9, RF-10, RF-19 |
| api/validation | RF-14, RF-15, RF-16, caso 13 |
| api/catalog | RF-20 |
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
| RF-20 | catalog (public) | Idea | GET /catalog/public | — | D1 | api/catalog |

**Cobertura:** los 20 RF (RF-1 a RF-20) están cubiertos en todas las 6 secciones del plan.

---

## 8. Nota de cumplimiento de la Constitución

* **Independencia del dominio (CC §2.1):** las reglas de negocio (máquina de estados, validaciones, roles) viven en `domain/` sin FastAPI/Pydantic.
* **Encapsulamiento vertical (CC §2.2):** 7 features backend + 6 features frontend, cada una autosuficiente.
* **Alta cohesión / bajo acoplamiento (CC §2.3):** las dependencias inter-feature se resuelven por contratos en `shared/` (p. ej. lectura de idea para `assistant` y `validation`).
* **Enfoque Spec-First (CC §2.4):** este plan deriva de la spec; cualquier cambio de contrato exige actualizar antes `specs/`.
* **Inmutabilidad de contratos (CC §5.2):** los payloads y rutas son los definidos aquí; alterarlos sin actualizar `specs/` está prohibido.
* **Dependencias (CC §6.1) y pruebas (CC §6.2):** solo stdlib + fastapi/pydantic/uvicorn/pytest; pruebas exclusivamente backend.
