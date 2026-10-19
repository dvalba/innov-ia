# Especificación Funcional — Innov-IA MVP

**Documento:** specs/001-innovation-evaluation-mvp/spec.md
**Versión:** 2.1 — Revisión de alcance del propietario del producto (debate, evaluación IA, contexto de empresa, campo *Recursos estimados*, preferencias de presentación). Supera a la v2.0.
**Estado:** Aprobada por el propietario del producto. Fuente única del alcance del MVP.
**Fuente de verdad:** Este documento precede a cualquier código (enfoque Spec-First, Constitución §2.4 y §5).

**Cambio de alcance v2.1 (sollicitud expresa del propietario del producto):**

1. El debate de ideas publicadas y la evaluación IA (con override del especialista) **pasan a estar dentro del alcance del MVP** (antes, §8 v2.0).
2. El campo *Recursos estimados* **se elimina del MVP completo** (decisión reversible para el futuro; §10 D11).
3. Se incorpora el **contexto de empresa** gestionable por el administrador (plantilla, edición en línea, subida de archivo), inyectado en **todas** las operaciones de la IA (RF-21, RF-22).
4. Se plasman las preferencias de presentación ya implementadas: **tema claro/oscuro persistente con vista de Ajustes y maquetación responsive** (RNF-13).

---

## 1. Contexto y objetivo

Innov-IA es una plataforma corporativa de gestión de iniciativas de innovación. El MVP entrega la **captura asistida de ideas**: un asistente conversacional con IA actúa como formulario dinámico que recolecta progresivamente 6 datos por idea, con **contingencia manual** cuando la IA no está disponible o falla (el formulario manual se despliega automáticamente, prellenado con lo ya capturado), **flujo de clarificación posterior** de las ideas manuales, y **validación por un especialista** antes de publicarla.

Al publicarse, cada idea abre un **debate** de 30 días (todos los usuarios con sesión; el asistente interviene bajo invocación `@asistant`; al cierre, la IA genera un resumen de los puntos principales) y una **evaluación de la IA sobre 5 criterios fijos**, que el especialista **acepta o sustituye** por su propia evaluación. Todo lo anterior opera guiado por un **contexto de empresa** gestionado por el administrador (RF-21/RF-22).

### 1.1 Datos requeridos por idea (los 6 campos)

| # | Campo | Descripción |
|---|-------|-------------|
| 1 | Título | Identificador corto. La IA lo sugiere de forma proactiva; el usuario lo acepta, pide otro o lo escribe. |
| 2 | Proponente | Nombre, área y datos de contacto. **Se prellena desde la cuenta del usuario** en ambos modos; el usuario puede corregir o completar. |
| 3 | Descripción | Explicación detallada, sintetizada o redactada con ayuda de la IA. |
| 4 | Problema u oportunidad | Situación actual que motiva la idea. |
| 5 | Beneficio esperado | Ahorro de costos, eficiencia, nuevos ingresos, etc. |
| 6 | Alineación estratégica | Correspondencia con los objetivos de la organización. |

> El campo *Recursos estimados* se eliminó del MVP (v2.1, decisión D11): no se captura, no se valida y no se muestra. Puede reintroducirse en una versión futura.

---

## 2. Estado actual de componentes frontend a refactorizar

**Hallazgo: estado cero.** `frontend/` y `backend/` están vacíos: no existe aplicación, componente, interfaz, formulario ni infraestructura previa.

Consecuencias:

* No hay nada que reutilizar ni refactorizar; toda la interfaz se construye desde cero conforme a la Constitución (organización por features y capa compartida).
* Las guías técnicas (`docs/guides/angular-guidelines.md`, `docs/guides/tailwind-guidelines.md`) se aplican directamente.
* La sección se actualizará si en fases posteriores se identifican componentes a refactorizar.

---

## 3. Usuarios y roles

Tres roles; un usuario puede ostentar varios a la vez.

| Rol | Qué puede hacer en el MVP |
|-----|---------------------------|
| **Proponente** | Captura ideas (asistida o manual); revisa, ajusta y solicita la publicación de sus ideas; consulta sus ideas, el catálogo público (detalle, debate y evaluación de cada idea publicada) y sus notificaciones. |
| **Especialista de desarrollo** | Consulta la cola de ideas en espera; valida (publica) o rechaza con comentario; participa en el debate de ideas publicadas y **acepta o sustituye la evaluación de la IA** por la propia. |
| **Administrador** | Crea/desactiva usuarios y gestiona roles; gestiona el contexto de empresa (plantilla, edición, subida de archivo); ajusta el límite del debate idea por idea. |

* Un usuario **sin roles no puede acceder** a funciones de la plataforma (su cuenta e historial existen; ver RF-17).
* Los demás roles del ciclo completo (dirección, comité de evaluación) son versiones futuras.

---

## 4. Historias de usuario

| ID | Historia |
|----|----------|
| HU-1 | Como **usuario**, quiero iniciar y cerrar sesión, para acceder a la plataforma de forma segura. |
| HU-2 | Como **proponente**, quiero que el asistente me haga preguntas progresivas con respuestas rápidas y un título sugerido, para registrar mi idea sin conocer la estructura formal. |
| HU-3 | Como **proponente**, si la IA no está disponible o falla, quiero completar un formulario manual (prellenado si ya había capturado campos), para no perder la idea. |
| HU-4 | Como **proponente**, quiero pedir mejoras a la IA y corregir manualmente cualquier campo de mi idea mientras esté en desarrollo, para entregarla en el mejor estado. |
| HU-5 | Como **proponente**, quiero solicitar la publicación de mi idea cuando lo decida (con o sin revisión previa de la IA), para tener el control del momento. |
| HU-6 | Como **proponente**, quiero ser notificado cuando la IA refine mi idea manual y poder aceptar la versión o ajustarla en el chat, para tener el control final de lo que se publica. |
| HU-7 | Como **proponente**, quiero ver mis ideas y su estado, para saber en qué punto están. |
| HU-8 | Como **usuario** de la plataforma, quiero consultar las ideas publicadas, para conocer las iniciativas válidas. |
| HU-9 | Como **especialista de desarrollo**, quiero ver la cola de ideas en espera, y validarlas o rechazarlas con comentario, para filtrar la calidad antes de publicarse. |
| HU-10 | Como **administrador**, quiero crear usuarios y asignar/revocar roles, para controlar quién puede proponer, validar o administrar. |
| HU-11 | Como **usuario** con sesión, quiero leer el detalle de una idea publicada con un debate donde todos podemos enriquecerla, y pedirle criterio al asistente citando un mensaje, para mejorar la iniciativa colectivamente. |
| HU-12 | Como **usuario** con sesión, quiero ver al cierre del debate un resumen de los puntos principales de la conversación (candidato a la ficha de la idea), para no perder las conclusiones. |
| HU-13 | Como **especialista de desarrollo**, quiero aceptar la evaluación de la IA o sustituirla por mi propia evaluación sobre los mismos 5 criterios, para registrar el juicio final de la idea. |
| HU-14 | Como **administrador**, quiero gestionar el contexto de empresa (descargar una plantilla, editarla en la plataforma o subir el archivo), para que la IA guíe toda la plataforma con la información correcta de la organización. |

---

## 5. Requisitos funcionales

Criterios en notación **EARS** (patrones: *Si/Cuando* = evento, *Mientras* = estado, *Donde* = opción, *debe* = omnipresente).

### 5.1 Acceso

**RF-1 — Inicio de sesión y sesión de trabajo**

* Cuando el usuario ingresa credenciales, el sistema debe iniciar una sesión si son válidas, y debe notificar el intento fallido sin indicar qué dato es incorrecto.
* Cuando el usuario termina sesión, el sistema debe cerrar el acceso y devolver a la pantalla de inicio de sesión.
* Mientras no exista una sesión activa, el sistema solo debe mostrar la pantalla de inicio de sesión.
* Criterio de aceptación: Toda idea queda asociada a la cuenta del usuario que la creó (base del listado "Mis ideas", RF-19).

### 5.2 Captura asistida (con IA)

> Régimen común de captura (modo asistido y manual): el campo *Proponente* se prellena con los datos de la cuenta y el usuario puede corregirlo o completarlo antes de registrar. El conjunto completo consta de las **6 preguntas/6 campos** de RF-3; no existe pregunta por *Recursos estimados* (v2.1, D11).

**RF-2 — Conversación de captura**

* Cuando un usuario con rol de proponente inicia una captura, el sistema debe abrir una conversación (saludo y primera pregunta).
* Criterio de aceptación: El usuario solo puede tener **una conversación de captura activa a la vez**; esto no limita el número de ideas que pueda tener en EN_DESARROLLO.
* Criterio de aceptación: "Ajustar detalles" de una idea existente (RF-13) no cuenta como una nueva captura a efectos de este límite.

**RF-3 — Preguntas progresivas**
El asistente recorre un orden fijo de campos, aceptando también narrativa libre.

* Criterio de aceptación: El orden de consulta es: **1) Descripción (narrativa libre) → 2) Título (sugerido, RF-4) → 3) Problema u oportunidad → 4) Beneficio esperado → 5) Alineación estratégica → 6) Proponente (confirmación del prellenado)** (v2.1: sin *Recursos estimados*, D11).
* Criterio de aceptación: Cuando la narrativa libre aporta información para varios campos, el sistema debe asignar cada fragmento al campo correspondiente, marcarlo como completado y no volver a preguntar por él.
* Criterio de aceptación: Cuando una respuesta es insuficiente, el sistema debe pedir aclaración antes de avanzar.

**RF-4 — Sugerencia proactiva del título**

* Criterio de aceptación: Inmediatamente después de la primera respuesta sustantiva del usuario, el sistema debe proponer un título con las opciones **Aceptar / Pedir otra sugerencia / Escribir manualmente**.
* Criterio de aceptación: "Pedir otra sugerencia" genera una sugerencia distinta de las anteriores hasta que el usuario acepte u opte por escribir.
* Criterio de aceptación: El texto escrito por el usuario se usa sin modificación.

**RF-5 — Respuestas rápidas (chips)**

* Criterio de aceptación: Para cada pregunta, el sistema debe ofrecer **respuestas rápidas (chips) generadas por la IA** para el campo en curso, enraizadas en el perfil de organización y los campos ya capturados, además de la respuesta libre por texto (sustitución aprobada del catálogo fijo, D7).
* Criterio de aceptación: Al seleccionar un chip, el sistema debe tomarlo como la respuesta completa del campo.
* Criterio de aceptación: Los chips permanecen disponibles hasta que el campo quede respondido.

**RF-6 — Finalización de la captura asistida**

* Criterio de aceptación: Cuando los 6 campos están completados, el sistema debe mostrar un **resumen editable** y pedir confirmación.
* Criterio de aceptación: Cuando el proponente confirma, el sistema registra la idea en **EN_DESARROLLO** con origen *asistida*.
* Criterio de aceptación: No se aplica ninguna versión de la IA sin que el proponente la haya visto y confirmado (resumen o aceptación explícita, RF-8).

### 5.3 Contingencia (sin IA)

**RF-7 — Formulario manual**

* Si el asistente no está disponible al iniciar, el sistema debe desplegar el formulario manual **automáticamente** (sin necesidad de pulsar nada más, salvo continuar) con los 6 campos (obligatorios) y un aviso claro de contingencia.
* Si el asistente falla durante una conversación en curso, el sistema debe ofrecer continuar por el formulario **prellenado con los campos ya capturados**, sin perder información.
* Cuando el formulario se envía completo, el sistema registra la idea en **EN_DESARROLLO** con origen *manual*.
* Criterio de aceptación: El formulario funciona sin dependencia del asistente.

### 5.4 Desarrollo de la idea

**RF-8 — Mejoras solicitadas a la IA**

* Mientras una idea esté en **EN_DESARROLLO**, cuando el proponente envíe una instrucción de mejora, el sistema debe proponer una nueva versión de los campos indicados. La idea queda marcada *revisada por IA*.
* Criterio de aceptación: Cada versión propuesta requiere **aceptación o descarte** explícito del proponente; el sistema no la aplica automáticamente.
* Criterio de aceptación: No hay límite de repeticiones; el marcado no impide ediciones manuales ni nuevas mejoras.

**RF-9 — Edición manual**

* Mientras una idea esté en **EN_DESARROLLO**, el proponente debe poder editar cualquiera de los 6 campos y el sistema debe conservar el cambio.
* Criterio de aceptación: Mientras el sistema esté generando una versión de la idea, la edición manual debe estar bloqueada con aviso hasta que la generación termine.

**RF-10 — Solicitud de publicación**

* Cuando el proponente de una idea en **EN_DESARROLLO** pulsa la acción *Solicitar publicación*, el sistema debe cambiarla a **SOLICITANDO_PUBLICACIÓN**; es la única acción que provoca esa transición.
* Criterio de aceptación: Está disponible aunque la idea nunca haya sido vista por la IA, inclusive una idea *manual* sin refinar.

### 5.5 Clarificación posterior (ideas manuales)

**RF-11 — Refinamiento de ideas manuales**

* Criterio de aceptación: La cola de refinamiento incluye ideas en **EN_DESARROLLO** con origen *manual* que aún no tienen versión refinada válida.
* Criterio de aceptación: El sistema verifica la disponibilidad del asistente **cuando** el usuario inicia sesión, inicia una conversación de captura, solicita una mejora u abre una idea con refinamiento pendiente; si está disponible, procesa toda la cola **de más antigua a más reciente**.
* Criterio de aceptación: Mientras haya ideas pendientes, estas siguen operando normalmente (RF-8, RF-9, RF-10). El refinamiento no tiene caducidad.

**RF-12 — Notificación de refinamiento**

* Criterio de aceptación: Al generarse una versión refinada, el sistema debe crear una notificación dirigida al proponente, con acceso directo a la idea.

**RF-13 — Aceptación o ajuste de la versión refinada**

* Criterio de aceptación: El sistema debe mostrar la versión refinada diferenciada de la original, con las opciones **Aceptar la versión** o **Ajustar detalles en el chat**.
* Criterio de aceptación: Al aceptar, la versión refinada pasa a ser la vigente; **la idea permanece en EN_DESARROLLO** (la publicación solo ocurre por RF-10 y RF-15).
* Criterio de aceptación: "Ajustar detalles" reabre una conversación asistida sobre la idea precontextualizada (no es una nueva captura, RF-2); si el asistente no está disponible durante el ajuste, el sistema debe ofrecer la edición manual (RF-9).

### 5.6 Validación por el especialista

**RF-14 — Cola de validación**

* Criterio de aceptación: La pantalla de validación (rol especialista) muestra únicamente las ideas en **SOLICITANDO_PUBLICACIÓN**, con los 6 campos, proponente (nombre y área) y fecha de solicitud.
* Criterio de aceptación: La cola no expone los datos de contacto del proponente (solo nombre y área).

**RF-15 — Validación (publicación)**

* Criterio de aceptación: Cuando el especialista valida una idea en **SOLICITANDO_PUBLICACIÓN**, el sistema debe pasarla a **VALIDADA_PUBLICA**, registrar quién validó y cuándo, y notificar al proponente.
* Criterio de aceptación: La validación se ejecuta por el propio proponente (autovalidación, §7 caso 9) y debe dejar el mismo rastro.

**RF-16 — Rechazo con comentario**

* Criterio de aceptación: Cuando un especialista rechaza una idea en **SOLICITANDO_PUBLICACIÓN**, el sistema debe devolvirla a **EN_DESARROLLO**, adjuntarle el **comentario obligatorio** (bloqueado sin él) y notificar al proponente con enlace a la idea y al comentario.

### 5.7 Usuarios y roles

**RF-17 — Panel de usuarios y roles (solo administrador)**

* Criterio de aceptación: El administrador puede **crear usuarios** (nombre de usuario, nombre, área, datos de contacto); el sistema emite una contraseña temporal que el usuario debe cambiar en su primer acceso, y puede **desactivar** usuarios (pierden acceso; cuenta e historial se conservan).
* Criterio de aceptación: El administrador puede asignar y revocar roles (uno o varios por usuario). Un usuario sin roles no accede a funciones de la plataforma.
* Criterio de aceptación: El panel impide dejar el sistema sin al menos un administrador.
* Criterio de aceptación: El primer administrador se define de forma manual en la inicialización del sistema; los cambios posteriores solo por el panel.

### 5.8 Notificaciones en aplicación

**RF-18 — Centro de notificaciones**
Notificaciones únicamente in-app, con punto de acceso visible, contador de no leídas, navegación al objeto y marcado de leída al consultar.

* Criterio de aceptación: Se notifican estos eventos y solo estos:
  * al proponente: idea refinada (RF-12); validada/publicada (RF-15); rechazada, con comentario (RF-16).
  * a **todos** los especialistas: idea nueva en **SOLICITANDO_PUBLICACIÓN**.

### 5.9 Mis ideas y catálogo público

**RF-19 — Mis ideas**

* Criterio de aceptación: El proponente consulta sus ideas (título, fecha de registro, origen, estado) y puede abrir cualquiera para ejecutar las acciones de su estado (RF-8, RF-9, RF-10, RF-13).

**RF-20 — Catálogo público (vista compacta)**

* Criterio de aceptación: Para todo usuario con sesión activa, el sistema muestra las ideas **VALIDADA_PUBLICA** (propias o de terceros) como una **lista compacta: título, fecha de publicación y descripción**; **solo de lectura** y sin datos de contacto.
* Criterio de aceptación: Nada menos que **VALIDADA_PUBLICA** aparece en el catálogo.
* Criterio de aceptación: Al seleccionar una idea, el sistema debe abrirla en su **vista de detalle** (RF-23) con sus 6 campos, el debate (RF-24) y la evaluación (RF-26).

### 5.10 Máquina de estados (MVP)

| Estado | Descripción | Transiciones |
|--------|-------------|--------------|
| **EN_DESARROLLO** | Creada, aún no autorizada para publicar. Atributos: origen (*asistida*/*manual*), *revisada por IA*, versión vigente, fecha de registro. | → SOLICITANDO_PUBLICACIÓN (RF-10) |
| **SOLICITANDO_PUBLICACIÓN** | Autorizada por el proponente; espera al especialista. | → VALIDADA_PUBLICA (RF-15); → EN_DESARROLLO (RF-16) |
| **VALIDADA_PUBLICA** | Publicada; visible en el catálogo con debate (RF-24) y evaluación (RF-26). Atributos nuevos: fecha de publicación, fecha límite del debate, debate cerrado, resumen del debate, evaluación vigente. | Terminal en el MVP |

* No existe borrador: la idea existe solo a partir de su registro (RF-6/RF-7).
* El debate y la evaluación son **atributos de la idea publicada**, no estados propios (D12).

### 5.11 Contexto de empresa (administrador)

**RF-21 — Gestión del contexto de empresa (solo administrador)**

* Cuando el administrador accede a la sección de contexto de empresa, el sistema debe ofrecer: **descargar la plantilla**, **editar el contenido en la propia plataforma** (formulario con las secciones de la plantilla) y **subir un archivo** (texto) que contenga el contexto editado.
* Criterio de aceptación: La plantilla es un documento de texto con secciones orientativas: **perfil de la organización, alineación estratégica (objetivos, prioridades y líneas de innovación), vocabulario e información de referencia** para guiar a la IA.
* Criterio de aceptación: El contexto se persiste como un **único documento editable** por la plataforma; una subida reemplaza el contenido vigente en su totalidad.
* Criterio de aceptación: El documento vigente queda como **contexto de empresa** a disposición de todas las operaciones de la IA de la plataforma.

**RF-22 — Inyección del contexto de empresa en la IA**

* Criterio de aceptación: El contexto de empresa debe inyectarse en **todas** las operaciones de la IA: preguntas y chips de la captura (RF-2/RF-5), sugerencia del título (RF-4), mejoras y refinamientos (RF-8/RF-11), intervención en el debate (RF-25) y evaluación de ideas (RF-26).
* Criterio de aceptación: El perfil de organización (nombre, sector, misión, objetivos estratégicos) forma parte de la plantilla y se gestiona desde la misma sección; la información que el administrador deje allí es la que la IA usa.
* Criterio de aceptación: Si el contexto es vacío o contiene solo secciones sin contenido, la IA opera sin contexto y el sistema muestra un aviso al administrador.

### 5.12 Publicación, debate y evaluación (ideas VALIDADA_PUBLICA)

**RF-23 — Vista de detalle de la idea publicada**

* Criterio de aceptación: La vista de detalle muestra un **resumen** con los 6 campos de la idea, el proponente (nombre y área), las fechas de registro y publicación, el debate (RF-24) y la evaluación (RF-26). **Solo de lectura** en cuanto a los campos de la idea: no existe edición de una idea publicada en el MVP.

**RF-24 — Debate de la idea publicada**

* Criterio de aceptación: Para todo usuario con sesión activa (proponente, especialista o administrador), mientras el debate no haya cerrado, el sistema debe permitir **publicar mensajes** y leer todos los mensajes previos (autor, fecha y texto).
* Criterio de aceptación: El debate abre con fecha límite = **fecha de publicación + 30 días por defecto**.
* Criterio de aceptación: Al llegar la fecha límite, el debate se **cierra de forma automática y definitiva**: no se admiten nuevos mensajes y la interfaz lo comunica.
* Criterio de aceptación: Solo el **administrador** puede ajustar la fecha límite de un debate **idea por idea** (adelantarla o extenderla), incluso sobre debates cerrados (reabrirlos es ajustando la fecha a un futuro; el ajuste queda registrado con quien lo hizo y cuándo).
* Criterio de aceptación: Al cerrarse el debate, si existió al menos un mensaje, la IA debe generar un **resumen de los puntos principales** de la conversación (el debate, el estado del debate y su resumen son visibles en la vista de detalle).

**RF-25 — Intervención del asistente en el debate (@asistant)**

* Criterio de aceptación: Cuando un participante escribe **`@asistant` seguido de una petición**, citando o referenciando un mensaje concreto del debate (el sistema debe permitir seleccionar/enlazar el mensaje al que responde), el asistente debe responder en el propio hilo con el criterio o análisis solicitado, guiado por el contexto de empresa (RF-22).
* Criterio de aceptación: El mensaje del asistente queda identificado como mensaje del asistente (autor *Asistente*), distinto de los de usuario.
* Criterio de aceptación: Si el asistente está caído, la petición se notifica como no procesable y el debate sigue operando sin IA (RNF-1).

**RF-26 — Evaluación de la IA y criterio del especialista**

* Criterio de aceptación: Cuando una idea pasa a **VALIDADA_PUBLICA** (RF-15), el sistema debe generar automáticamente la **evaluación de la IA sobre 5 criterios fijos**: *claridad del problema*, *factibilidad*, *impacto esperado*, *alineación estratégica* y *grado de innovación*, cada uno con **puntuación 1–10 y justificación breve**.
* Criterio de aceptación: La evaluación se muestra en la vista de detalle como **evaluación de la IA** con su autor y fecha, visible para todo usuario con sesión.
* Criterio de aceptación: El rol **especialista de desarrollo** puede **aceptar** la evaluación de la IA (queda como el juicio final de la idea) o **sustituirla** por una nueva evaluación propia sobre los mismos 5 criterios (puntuación 1–10 y justificación por criterio); el sustituto se registra con autor y fecha y es revisable solo mientras la evaluación de la IA no haya sido aceptada.
* Criterio de aceptación: El juicio final de la idea es único en todo momento: la evaluación de la IA (mientras no haya decisión del especialista), la evaluación de la IA aceptada o la evaluación sustitutiva del especialista.
* Criterio de aceptación: Tanto la aceptación de la evaluación de la IA como la sustitución por la propia quedan **auditadas con quien y cuándo** (RNF-8).

---

## 6. Requisitos no funcionales

| ID | Requisito |
|----|-----------|
| RNF-1 | **Independencia de la IA:** El registro de ideas no depende del asistente. La contingencia manual cubre cualquier indisponibilidad; la cola de refinamiento se procesa al recuperarse. |
| RNF-2 | **Transparencia:** Cada idea muestra su origen y su estado de forma visible; la interfaz deja claro cuando se está con IA o en modo manual. |
| RNF-3 | **Tiempo de respuesta:** Toda interacción con IA muestra carga; si no hay respuesta en 60 s, el sistema reintenta una vez y, de fallar, aplica la contingencia (RF-7). |
| RNF-4 | **Idioma:** Interfaz, mensajes, preguntas y notificaciones en español. |
| RNF-5 | **Integridad:** Ninguna idea se registra con los 6 campos vacíos u omitidos (ambos modos). |
| RNF-6 | **Accesibilidad:** Toda la interfaz (chat, chips, formularios, notificaciones, catálogos) debe poder operarse con teclado y lectores de pantalla. |
| RNF-7 | **Segregación por rol:** Cada rol solo accede a sus funciones y datos. Excepción explícita: el catálogo público (RF-20) es de solo lectura y visible para todos los usuarios con sesión, independientemente de rol. |
| RNF-8 | **Auditoría:** Toda transición a VALIDADA_PUBLICA registra quién y cuándo (inclusive autovalidación); todo rechazo conserva el comentario y la identidad de quien lo emitió. |
| RNF-9 | **Consistencia:** Solo los roles autorizados provocan transiciones; ante dos acciones simultáneas sobre la misma idea, se aplica la que se ejecute primero y se descarta la otra, sin dejar estado inconsistente. |
| RNF-10 | **Sin pérdida en contingencia:** Un fallo de la IA nunca borra campos ya capturados (RF-7). |
| RNF-11 | **Auditoría de debate:** Cada mensaje de debate registra autor, fecha y, cuando corresponda, el mensaje enlazado; el ajuste de fechas de debate y la aceptación/sustitución de la evaluación se auditan (quién y cuándo) (RF-24, RF-26). |
| RNF-12 | **Contexto inyectado:** La IA siempre opera con el contexto de empresa vigente; el contexto vacío se comunica al administrador (RF-22). |
| RNF-13 | **Presentación:** La plataforma ofrece tema claro/oscuro (el usuario elige y la preferencia se persiste entre sesiones), una vista de ajustes accesible y una maquetación responsive legible en móvil, tablet y escritorio. |

---

## 7. Casos límite y manejo de excepciones

| # | Caso | Comportamiento exigido |
|---|------|------------------------|
| 1 | IA no disponible al iniciar captura | Formulario manual directo con aviso de contingencia (RF-7). |
| 2 | Caída de la IA a mitad de conversación | Interrupción con aviso y formulario manual **prellenado** con lo capturado (RF-7). |
| 3 | Exceso de tiempo (60 s) | Reintento único transparente; de fallar, contingencia como caso 2. |
| 4 | Respuesta de IA incompleta/no interpretable | Se trata como fallo: reintento único y, de persistir, contingencia. |
| 5 | Indisponibilidad prolongada | La idea manual sigue operativa y puede publicarse sin refinar (RF-10); al recuperarse, se procesa la cola completa y se notifica por idea (RF-11/RF-12). |
| 6 | Fallo del refinamiento | Se conserva la versión original; el reintento es automático en la siguiente verificación (RF-11); si la cola fallara parcialmente, lo procesado queda y lo fallido sigue pendiente. No existe reintento manual. |
| 7 | Abandono de captura sin enviar | La información se pierde (no hay borradores). Si el cierre es explícito, se pide confirmación con aviso de pérdida; si se cierra la página sin confirmación, simplemente no se guarda nada. |
| 8 | Segunda captura simultánea | Se bloquea y se ofrece retomar la conversación existente (RF-2). |
| 9 | Autovalidación (proponente = especialista) | Permitida; el rastro de quién validó es obligatorio (RNF-8, RF-15). |
| 10 | Mejora solicitada con IA caída | Aviso al proponente; se registra la solicitud y se procesa en la siguiente verificación (RF-11). |
| 11 | Transiciones simultáneas sobre una idea | Gana la primera ejecutada; la restante se descarta (RNF-9). |
| 12 | Datos de contacto inválidos (cuenta o campo Proponente) | Validación de formato y no-vacío; se pide corrección antes de registrar. |
| 13 | Rechazo sin comentario | Bloqueado (RF-16). |
| 14 | Definición de "fallo/conflicto de IA" | Sin respuesta en tiempo límite, error del servicio, o respuesta no interpretable. |
| 15 | Credenciales inválidas o sesión caducada | Devolución a pantalla de inicio de sesión; sin datos expuestos; el registro de ideas no depende de la sesión previa. |
| 16 | Revocación de rol / desactivación de usuario | La cuenta, sus ideas e historial se conservan intactos; el usuario pierde el acceso a funciones. Las ideas en SOLICITANDO_PUBLICACIÓN quedan validables por otros especialistas; las notificaciones del usuario se conservan y son visibles al recuperar acceso. |
| 17 | Fallo al guardar un registro | No se deja registro parcial; si es el formulario manual, los datos permanecen en pantalla para reintentar el envío. |
| 18 | Debate cerrado por límite de fecha | Los mensajes no se admiten; la interfaz lo comunica y muestra el resumen del debate si existió (RF-24). |
| 19 | `@asistant` sin mensaje enlazado o sin petición | Se trata como mensaje de usuario corriente; no se invoca al asistente. |
| 20 | Invocación `@asistant` con la IA caída | La petición queda visible como mensaje no procesado con aviso; se reintenta en la siguiente interacción con la IA disponible (RNF-1, RF-25). |
| 21 | Cierre del debate sin mensajes | No hay resumen generado; la interfaz indica que no hubo debate. |
| 22 | IA caída al momento de publicarse una idea (evaluación pendiente) | La idea se publica normalmente (la validación no depende de la IA); la evaluación se genera en la siguiente verificación de disponibilidad (RNF-1, RF-26). |
| 23 | Sustitución de la evaluación por el especialista y luego el especialista acepta la de la IA (o al revés) | Cada acción es sobre el estado previo; el juicio final siempre es el resultado de la última acción del especialista. |
| 24 | Contexto de empresa vacío o solo plantilla sin contenido | La IA opera sin contexto; se muestra aviso al administrador en la sección de contexto (RF-22). |
| 25 | Subida de archivo de contexto sin texto o corrupto | Se rechaza el guardado con aviso; el contexto vigente no se modifica. |

---

## 8. Fuera de alcance

1. Estados formales **IDEA EN DEBATE** y **IDEA EN EVALUACIÓN** con salidas Aprobada/Archivada/Rechazada (el debate de la plataforma es un atributo de la idea publicada, RF-24, decisión D12), incluidos el comité de evaluación y sus decisiones formales.
2. **Scoring global** (0–100) y ranking de ideas; la evaluación se expresa solo como los 5 criterios por criterio (RF-26).
3. Flujos de evaluación formal más allá de la validación del especialista y la evaluación IA/sustitución del especialista (RF-26).
4. Roles adicionales al MVP (dirección, comité) y su integración al panel.
5. Borradores de ideas (decisión explícita).
6. Notificaciones fuera de la aplicación.
7. Publicación externa (portales, boletines, etc.); "publicada" significa publicada dentro de la plataforma.
8. Edición de ideas en VALIDADA_PUBLICA (no existe edición de una idea publicada; corresponde a fases futuras).
9. Reintroducción del campo *Recursos estimados* (decisión D11: fuera del MVP, reversible en el futuro).

---

## 9. Criterios de finalización

1. **Acceso:** login válido inicia sesión; inválido no la inicia; logout cierra.
2. **Captura asistida e2e:** conversación completa (orden fijo, chips, título sugerido, resumen) → idea en EN_DESARROLLO *asistida*.
3. **Captura manual e2e:** con IA desactivada → idea en EN_DESARROLLO *manual*.
4. **Contingencia:** fallo mid-conversación → formulario prellenado → registro.
5. **Clarificación:** refinamiento automático, notificación, aceptación (o ajuste) → idea sigue en EN_DESARROLLO; pública solo tras RF-10 + RF-15.
6. **Desarrollo:** mejora aceptada/descartada y edición manual persisten.
7. **Validación e2e:** validación → VALIDADA_PUBLICA + notificación; rechazo → EN_DESARROLLO + comentario.
8. **Usuarios/roles:** creación de usuario (contraseña temporal, cambio en primer acceso), asignación, revocación (sin roles = sin acceso, historial intacto), bloqueo del último administrador.
9. **Notificaciones:** solo los 4 eventos de RF-18; contador, navegación y leídas.
10. **Catálogo público:** solo VALIDADA_PUBLICA, en vista compacta (título, fecha de publicación, descripción); al abrir, la vista de detalle muestra los 6 campos, el debate y la evaluación; de solo lectura, sin datos de contacto.
11. **Debate:** mensajes de cualquier usuario con sesión; cierre automático a 30 días; ajuste de fecha por idea del administrador; `@asistant` responde con el mensaje enlazado; al cierre, resumen de la IA visible.
12. **Evaluación:** generada al publicarse sobre 5 criterios (1–10 + justificación); aceptación o sustitución por el especialista dejan un único juicio final auditado.
13. **Contexto de empresa:** plantilla descargable, edición en línea y subida de archivo; vacío detectado con aviso; inyectado en captura, título, mejoras, debate y evaluación.
14. **Presentación:** tema claro/oscuro persistido, vista de ajustes, maquetación responsive.
15. **Casos límite:** verificados 1, 2, 5, 6, 7, 13, 16, 17, 18, 20, 22.
16. **Pruebas:** `pytest -q` pasa al completo (backend).
17. **Conformidad:** estructura por features y capa compartida según Constitución; guías de Angular y Tailwind respetadas.

---

## 10. Registro de decisiones (cero dudas abiertas)

| # | Decisión | Donde queda |
|---|----------|-------------|
| 1 | Aceptar una versión refinada **no publica**; la publicación solo ocurre por la acción explícita del proponente (RF-10) y la validación del especialista (RF-15). | RF-10, RF-13 |
| 2 | Existe **catálogo público** de VALIDADA_PUBLICA, visible para toda la plataforma, de solo lectura, sin datos de contacto. | RF-20 |
| 3 | La **autovalidación** está permitida y exige rastro de quién validó. | RF-15, RNF-8, §7 cas. 9 |
| 4 | El refinamiento de ideas manuales se reintenta **automáticamente en la siguiente verificación** (régimen *bajo demanda*): al iniciar sesión, al iniciar captura, al solicitar mejora y al abrir idea pendiente. Sin límite contador ni reintento manual. | RF-11 |
| 5 | Identidad por **login simple** (usuario/contraseña, sesión) dentro del MVP. | RF-1 |
| 6 | Los usuarios son **creados por el administrador** (contraseña temporal, cambio en primer acceso); el primer administrador se define manualmente en la inicialización. | RF-17 |
| 7 | Un proponente puede tener **varias ideas en EN_DESARROLLO**; solo una conversación de captura a la vez. | RF-2 |
| 8 | Una idea manual **puede publicarse sin refinar**; el refinamiento no es precondición de la publicación. | RF-10 |
| 9 | La revocación de rol/desactivación **conserva cuenta, ideas e historial**; solo se pierde el acceso. | RF-17, §7 cas. 16 |
| 10 | El **Proponente como campo** se prellena desde la cuenta en los dos modos de captura. | §1.1, RF-6, RF-7 |
| 11 | **Recursos estimados fuera del MVP:** el campo no se captura, no se valida y no se muestra en ningún lugar (decisión reversible; puede reintroducirse en una versión futura). Sustituye a los "7 campos" de la v2.0: se trabaja con 6. | §1.1, D11, RF-3, RF-7, RF-9 |
| 12 | **Debate y evaluación son atributos de la idea publicada, no estados:** el debate se cierra por fecha límite (30 días por defecto, ajustable idea por idea por el administrador) y la evaluación es única (IA o del especialista). No se introducen los estados formales *En debate*/*En evaluación* de la v1.0. | RF-24, RF-26, §5.10 |
| 13 | **Contexto de empresa:** se gestiona como un único documento (plantilla + edición en línea + subida de archivo) y se inyecta en TODAS las operaciones de la IA. Sustituye/expande el perfil de organización de la v2.0 (D7): el perfil queda dentro del documento. | RF-21, RF-22, RNF-12 |
| 14 | **@asistant en el debate:** la intervención del asistente es bajo invocación explícita citando un mensaje concreto; el resumen final del debate lo genera la IA al cerrarse (si hubo mensajes). El debate no es un chat asistido continuo. | RF-24, RF-25 |
| 15 | **Evaluación IA:** 5 criterios fijos (*claridad del problema, factibilidad, impacto esperado, alineación estratégica, grado de innovación*), puntuación 1–10 + justificación por criterio; se genera al publicarse; el especialista la acepta o la sustituye por su propia sobre los mismos criterios. No hay scoring global 0–100. | RF-26 |
| 16 | **Catálogo en vista compacta:** el listado muestra solo título, fecha de publicación y descripción; el resto (6 campos, debate, evaluación) se ve en la vista de detalle de la idea. | RF-20, RF-23 |
| 17 | **Preferencia de presentación:** tema claro/oscuro elegible por el usuario, persistido entre sesiones, con vista de ajustes accesible del menú y maquetación responsive. | RNF-13 |
