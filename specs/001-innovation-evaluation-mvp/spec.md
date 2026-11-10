# Especificación Funcional — Innov-IA MVP

**Documento:** specs/001-innovation-evaluation-mvp/spec.md
**Versión:** 2.2 — Revisión de alcance del propietario del producto (debate, evaluación IA, contexto de empresa, campo *Recursos estimados*, preferencias de presentación, **decisión final de la calificación y estados finales**). Supera a la v2.1.
**Estado:** Aprobada por el propietario del producto. Fuente única del alcance del MVP.
**Fuente de verdad:** Este documento precede a cualquier código (enfoque Spec-First, Constitución §2.4 y §5).

**Cambio de alcance v2.1 (sollicitud expresa del propietario del producto):**

1. El debate de ideas publicadas y la evaluación IA (con override del especialista) **pasan a estar dentro del alcance del MVP** (antes, §8 v2.0).
2. El campo *Recursos estimados* **se elimina del MVP completo** (decisión reversible para el futuro; §10 D11).
3. Se incorpora el **contexto de empresa** gestionable por el administrador (plantilla, edición en línea, subida de archivo), inyectado en **todas** las operaciones de la IA (RF-21, RF-22).
4. Se plasman las preferencias de presentación ya implementadas: **tema claro/oscuro persistente con vista de Ajustes y maquetación responsive** (RNF-13).

**Cambio de alcance v2.2 (solicitud expresa del propietario del producto):**

1. Tras cerrarse el debate y generarse la calificación de la IA, la idea **vuelve a aparecer en la cola de validación** (etapa de calificación) y el especialista toma la **decisión final** sobre la ficha completa: el resultado (aceptada/archivada/rechazada) se deduce **automáticamente del promedio de los 5 criterios comparado con umbrales configurables por el administrador** (por defecto: < 4 rechazada, 4–< 7 archivada, ≥ 7 aceptada), se muestra en vivo mientras se puntúa, y la decisión **debe coincidir con el promedio** (si no coincide, el especialista debe ajustar la puntuación, no forzar el resultado).
2. La decisión final conlleva **confiración explícita** con aviso de la consecuencia ("según nuestra evaluación esta idea será rechazada/aceptada/archivada… si quieres cambiar, este es el momento") y **motivo obligatorio** para rechazar y archivar; toda decisión queda auditada (RNF-8) y el creador es notificado (aceptada, rechazada con motivo, archivada con motivo).
3. Nuevos **estados finales**: `ACEPTADA`, `RECHAZADA` (terminal, sin reevaluación) y `ARCHIVADA` (el creador puede **solicitar reevaluación**: la idea vuelve a la cola de calificación conservando el debate cerrado y la evaluación de la IA). `VALIDADA_PUBLICA` deja de ser terminal.
4. El **catálogo público se organiza en 4 zonas** (pestañas): *En proceso* (`VALIDADA_PUBLICA`), *Aceptadas*, *Rechazadas* y *Archivadas*; la vista de detalle opera para las 4 zonas.
5. En la ficha, el debate **cerrado se compacta**: solo se ve el resumen de la IA (o el aviso de que no hubo debate) y un enlace para ver el chat completo en otra vista de solo lectura.
6. Nuevos **eventos de notificación** (RF-18): idea aceptada, idea rechazada (etapa de calificación, con motivo) e idea archivada (con motivo).

---

## 1. Contexto y objetivo

Innov-IA es una plataforma corporativa de gestión de iniciativas de innovación. El MVP entrega la **captura asistida de ideas**: un asistente conversacional con IA actúa como formulario dinámico que recolecta progresivamente 6 datos por idea, con **contingencia manual** cuando la IA no está disponible o falla (el formulario manual se despliega automáticamente, prellenado con lo ya capturado), **flujo de clarificación posterior** de las ideas manuales, y **validación por un especialista** antes de publicarla.

Al publicarse, cada idea abre un **debate** de 30 días (todos los usuarios con sesión; el asistente interviene bajo invocación `@asistant`); al **cerrarse** el debate, la IA genera un **resumen de los puntos principales** y la **evaluación de la IA sobre 5 criterios fijos** (RF-24/RF-25/RF-26). La idea **vuelve entonces a la cola de validación** (etapa de calificación, RF-27): el especialista puntúa los 5 criterios (aceptando la de la IA o escribiendo la suya), el **promedio** determina el resultado (aceptada/archivada/rechazada según umbrales configurables, RF-28) y, tras la **confirmación explícita**, la idea queda en su **estado final** (`ACEPTADA`, `ARCHIVADA` o `RECHAZADA`) y se ubica en la zona correspondiente del **catálogo por zonas** (RF-20/RF-29); la decisión se audita (RNF-8) y el creador es notificado (RF-18). Todo lo anterior opera guiado por un **contexto de empresa** gestionado por el administrador (RF-21/RF-22).

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

**RF-14 — Cola de validación (dos etapas)**

* Criterio de aceptación: La pantalla de validación (rol especialista) muestra las ideas pendientes de decisión, en dos etapas: **publicación** (ideas en **SOLICITANDO_PUBLICACIÓN**) y **calificación** (ideas en **VALIDADA_PUBLICA** cuyo debate está cerrado y aún no tienen decisión final). Cada entrada muestra su etapa, los 6 campos, el proponente (nombre y área) y la fecha de solicitud o de cierre del debate, según corresponda.
* Criterio de aceptación: La cola no expone los datos de contacto del proponente (solo nombre y área).
* Criterio de aceptación: Al abrir una entrada de la etapa de calificación, el especialista accede a la **ficha completa** (RF-23): 6 campos, debate compactado (RF-24), calificación de la IA (RF-26) y el formulario de decisión final (RF-27/RF-28).

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
  * al proponente: idea refinada (RF-12); validada/publicada (RF-15); rechazada, con comentario (RF-16) —en la etapa de publicación— o con motivo (RF-27) —en la etapa de calificación; **aceptada, con la nota de la decisión final (RF-27)**; **archivada, con el motivo (RF-27)**; **reevaluación atendida: su idea vuelve a la cola de calificación (RF-29)**.
  * a **todos** los especialistas: idea nueva en **SOLICITANDO_PUBLICACIÓN**; **idea pendiente de calificación** (debate cerrado y evaluación de la IA generada, RF-27).

### 5.9 Mis ideas y catálogo público

**RF-19 — Mis ideas**

* Criterio de aceptación: El proponente consulta sus ideas (título, fecha de registro, origen, estado) y puede abrir cualquiera para ejecutar las acciones de su estado (RF-8, RF-9, RF-10, RF-13).

**RF-20 — Catálogo público por zonas (vista compacta)**

* Criterio de aceptación: Para todo usuario con sesión activa, el catálogo se organiza en **cuatro zonas** (pestañas): **En proceso** (ideas **VALIDADA_PUBLICA** sin decisión final), **Aceptadas** (ACEPTADA), **Rechazadas** (RECHAZADA) y **Archivadas** (ARCHIVADA). Cada zona muestra sus ideas como **lista compacta: título, fecha de publicación y descripción**; **solo de lectura** y sin datos de contacto.
* Criterio de aceptación: Nada menos que **VALIDADA_PUBLICA** (o su estado final) aparece en el catálogo.
* Criterio de aceptación: Al seleccionar una idea, el sistema debe abrirla en su **vista de detalle** (RF-23) con sus 6 campos, el debate (RF-24) y la evaluación (RF-26), y el estado final visible cuando corresponda.

### 5.10 Máquina de estados (MVP)

| Estado | Descripción | Transiciones |
|--------|-------------|--------------|
| **EN_DESARROLLO** | Creada, aún no autorizada para publicar. Atributos: origen (*asistida*/*manual*), *revisada por IA*, versión vigente, fecha de registro. | → SOLICITANDO_PUBLICACIÓN (RF-10) |
| **SOLICITANDO_PUBLICACIÓN** | Autorizada por el proponente; espera al especialista. | → VALIDADA_PUBLICA (RF-15); → EN_DESARROLLO (RF-16) |
| **VALIDADA_PUBLICA** | Publicada; visible en el catálogo (zona *En proceso*) con debate (RF-24) y evaluación de la IA (RF-26). Atributos nuevos: fecha de publicación, fecha límite del debate, debate cerrado, resumen del debate, evaluación de la IA. | → ACEPTADA / ARCHIVADA / RECHAZADA (decisión final del especialista, RF-27/RF-28); → VALIDADA_PUBLICA (reevaluación de una ARCHIVADA, RF-29) |
| **ACEPTADA** | Decisión final: el promedio de la calificación quedó en la banda de aceptación (RF-28). Zona *Aceptadas* del catálogo. Atributos: nota de decisión, motivo, decisor y fecha (RNF-8). | Terminal (no admite reevaluación) |
| **ARCHIVADA** | Decisión final: el promedio quedó en la banda media o el especialista la archivó, con motivo (RF-27/RF-28). Zona *Archivadas* del catálogo. | → VALIDADA_PUBLICA (solicitud de reevaluación del creador, RF-29) |
| **RECHAZADA** | Decisión final en la etapa de calificación: el promedio quedó en la banda de rechazo (RF-28), con motivo obligatorio (RF-27). Zona *Rechazadas* del catálogo. | Terminal (la reevaluación de rechazadas queda fuera del MVP; decisión reversible para el futuro) |

* No existe borrador: la idea existe solo a partir de su registro (RF-6/RF-7).
* El debate y la evaluación son **atributos de la idea publicada**, no estados propios (D12).
* Los estados finales registran quién decidió y cuándo (RNF-8); el motivo es obligatorio para ARCHIVADA y RECHAZADA (RF-27).

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
* Criterio de aceptación: En la ficha, el debate **cerrado se muestra compactado**: solo se ve el resumen de la IA (o el aviso de que no hubo debate, caso 21) y un **enlace para ver el chat completo en otra vista de solo lectura** (todos los mensajes, autores y fechas); no se admite escribir en ninguna de las dos vistas cuando el debate está cerrado.

**RF-25 — Intervención del asistente en el debate (@asistant)**

* Criterio de aceptación: Cuando un participante escribe **`@asistant` seguido de una petición**, citando o referenciando un mensaje concreto del debate (el sistema debe permitir seleccionar/enlazar el mensaje al que responde), el asistente debe responder en el propio hilo con el criterio o análisis solicitado, guiado por el contexto de empresa (RF-22).
* Criterio de aceptación: El mensaje del asistente queda identificado como mensaje del asistente (autor *Asistente*), distinto de los de usuario.
* Criterio de aceptación: Si el asistente está caído, la petición se notifica como no procesable y el debate sigue operando sin IA (RNF-1).

**RF-26 — Evaluación de la IA y criterio del especialista**

* Criterio de aceptación: Al **cerrarse el debate** de una idea en **VALIDADA_PUBLICA** (RF-24), el sistema debe generar automáticamente la **evaluación de la IA sobre 5 criterios fijos**: *claridad del problema*, *factibilidad*, *impacto esperado*, *alineación estratégica* y *grado de innovación*, cada uno con **puntuación 1–10 y justificación breve** (si la IA no está disponible la evaluación queda pendiente y se reintenta, sin bloquear nada).
* Criterio de aceptación: La evaluación se muestra en la vista de detalle como **evaluación de la IA** con su autor y fecha, visible para todo usuario con sesión.
* Criterio de aceptación: El rol **especialista de desarrollo** puede **aceptar** la evaluación de la IA (queda como el juicio final de la idea) o **sustituirla** por una nueva evaluación propia sobre los mismos 5 criterios (puntuación 1–10 y justificación por criterio); el sustituto se registra con autor y fecha y es revisable solo mientras la evaluación de la IA no haya sido aceptada.
* Criterio de aceptación: El juicio final de la idea es único en todo momento: la evaluación de la IA (mientras no haya decisión del especialista), la evaluación de la IA aceptada o la evaluación sustitutiva del especialista.
* Criterio de aceptación: Tanto la aceptación de la evaluación de la IA como la sustitución por la propia quedan **auditadas con quien y cuándo** (RNF-8).

**RF-27 — Decisión final del especialista (etapa de calificación)**

* Criterio de aceptación: Al **cerrarse el debate** de una idea en **VALIDADA_PUBLICA** y generarse su evaluación de la IA (RF-26), la idea **vuelve a la cola de validación** (etapa de calificación, RF-14) y se notifica a todos los especialistas (RF-18).
* Criterio de aceptación: En la ficha de la idea (RF-23) el especialista puntúa los 5 criterios fijos: puede **aceptar la calificación de la IA** (se replica en la calificación humana) o **escribir la suya** (sustitución, RF-26); el **promedio** (suma de los 5 / 5) y el **resultado derivado** (aceptada/archivada/rechazada según RF-28) se muestran **en vivo** mientras se rellenan los puntos.
* Criterio de aceptación: Para confirmar, el especialista elige el resultado final entre **aceptar / archivar / rechazar**: cada opción solo se habilita si **coincide con el resultado derivado del promedio**; si el especialista elige un resultado distinto al derivado, el sistema le indica que debe **ajustar la puntuación** para que refleje su intención (nunca se permite forzar un resultado contradictorio con los puntos).
* Criterio de aceptación: Al elegir, el sistema muestra un **aviso de confirmación** con la consecuencia ("según nuestra evaluación, esta idea será rechazada/aceptada/archivada; si quieres cambiar de decisión o de evaluación, este es el momento") y las opciones de **confirmar** o **volver a ajustar**; al confirmar, la idea pasa a su estado final (RF-28) y la decisión se **audita** con el especialista, el resultado y la fecha (RNF-8).
* Criterio de aceptación: **Rechazar y archivar exigen motivo obligatorio** (bloqueado sin él); aceptar no exige motivo, aunque el especialista puede escribir una **nota** opcional que queda en el rastro.
* Criterio de aceptación: Al confirmarse, el **creador es notificado**: idea aceptada; idea rechazada, con el motivo; idea archivada, con el motivo (RF-18).

**RF-28 — Umbral de calificación y resultado automático (solo administrador)**

* Criterio de aceptación: El resultado final se deduce del **promedio simple de los 5 criterios** comparado con **dos umbrales** (enteros 1–10, con `umbralRechazo < umbralAceptacion`): **promedio < umbralRechazo → rechazada**; **umbralRechazo ≤ promedio < umbralAceptacion → archivada**; **promedio ≥ umbralAceptacion → aceptada**. Por defecto: **4 / 7**.
* Criterio de aceptación: Los umbrales son **configurables por el administrador** (sección de administración) y se aplican a las decisiones desde su cambio; quedan registrados con quien y cuándo (RNF-8).
* Criterio de aceptación: El promedio y el resultado derivado se calculan siempre sobre la **calificación vigente** (la de la IA aceptada o la sustitutiva del especialista, RF-26) y se muestran en la ficha (RF-23/RF-27); no existe scoring global 0–100 ni ranking (D15).

**RF-29 — Estados finales, catálogo por zonas y reevaluación**

* Criterio de aceptación: La decisión final mueve la idea a **ACEPTADA**, **ARCHIVADA** o **RECHAZADA** (§5.10); la idea deja de estar en la cola de validación y pasa a la **zona correspondiente del catálogo** (RF-20), donde su vista de detalle (RF-23) es idéntica y muestra el estado final.
* Criterio de aceptación: Solo el **especialista** puede **archivar**; el creador de una idea **ARCHIVADA** puede **solicitar reevaluación**: la idea **vuelve a la cola de la etapa de calificación** (VALIDADA_PUBLICA), **conservando el debate cerrado y la evaluación de la IA**, y se limpia la decisión final (nota, motivo y decisor) para decidir de nuevo; el creador es notificado cuando su solicitud se atiende y de nuevo al confirmarse la nueva decisión (RF-18).
* Criterio de aceptación: Las ideas **ACEPTADA** y **RECHAZADA** **no admiten reevaluación** en el MVP (decisión reversible para el futuro); su ficha no ofrece esa acción.
* Criterio de aceptación: En **Mis ideas** (RF-19) el creador ve el estado final de sus ideas y, en las archivadas, la acción de solicitar reevaluación.

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
| RNF-8 | **Auditoría:** Toda transición a VALIDADA_PUBLICA registra quién y cuándo (inclusive autovalidación); todo rechazo conserva el comentario y la identidad de quien lo emitió; toda decisión final (aceptar/archivar/rechazar, RF-27) y cambio de umbrales (RF-28) registran quién y cuándo. |
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
| 22 | IA caída al momento de cerrarse el debate (evaluación pendiente) | El debate se cierra normalmente (el cierre no depende de la IA); la evaluación queda pendiente y se genera en la siguiente verificación de disponibilidad (RNF-1, RF-26). |
| 23 | Sustitución de la evaluación por el especialista y luego el especialista acepta la de la IA (o al revés) | Cada acción es sobre el estado previo; el juicio final siempre es el resultado de la última acción del especialista. |
| 24 | Contexto de empresa vacío o solo plantilla sin contenido | La IA opera sin contexto; se muestra aviso al administrador en la sección de contexto (RF-22). |
| 25 | Subida de archivo de contexto sin texto o corrupto | Se rechaza el guardado con aviso; el contexto vigente no se modifica. |
| 26 | Promedio exactamente en un umbral | Se aplica la banda cerrada por arriba: promedio = umbralRechazo → archivada; promedio = umbralAceptacion → aceptada (RF-28). |
| 27 | El especialista intenta forzar un resultado distinto al derivado del promedio | La acción se bloquea con aviso: debe ajustar la puntuación para que refleje su intención (RF-27). |
| 28 | Rechazo o archivo sin motivo en la etapa de calificación | Bloqueado (motivo obligatorio, RF-27); la idea no cambia de estado. |
| 29 | Reevaluación de una idea ACEPTADA o RECHAZADA | No existe la acción (fuera del MVP); solo las ARCHIVADAS pueden reevaluarse (RF-29). |
| 30 | Reevaluación de una ARCHIVADA cuyo debate ya cerró | La idea vuelve a la cola de calificación conservando debate cerrado y evaluación de la IA; se limpia la decisión final previa y el especialista decide de nuevo (RF-29). |
| 31 | Cambios de umbrales con ideas ya decididas | Solo afectan decisiones posteriores; las ideas en estado final no se recalculan (RF-28). |

---

## 8. Fuera de alcance

1. Estados formales **IDEA EN DEBATE** y **IDEA EN EVALUACIÓN** (el debate de la plataforma es un atributo de la idea publicada, RF-24, decisión D12), el comité de evaluación y sus decisiones formales. (v2.2: las **salidas** Aceptada/Archivada/Rechazada **sí están en el alcance**, como estados finales del §5.10 y RF-27/RF-29, sin comité).
2. **Scoring global** (0–100) y ranking de ideas; la evaluación se expresa solo como los 5 criterios por criterio (RF-26); el resultado final usa el promedio de los 5 criterios (RF-28), no un score propio.
3. Flujos de evaluación formal más allá de la validación del especialista y la evaluación IA/sustitución del especialista (RF-26/RF-27).
4. Roles adicionales al MVP (dirección, comité) y su integración al panel.
5. Borradores de ideas (decisión explícita).
6. Notificaciones fuera de la aplicación.
7. **Reevaluación de ideas ACEPTADA o RECHAZADA**: fuera del MVP; solo las ARCHIVADAS se reevalúan (RF-29, decisión reversible).
8. Publicación externa (portales, boletines, etc.); "publicada" significa publicada dentro de la plataforma.
9. Edición de ideas en VALIDADA_PUBLICA (no existe edición de una idea publicada; corresponde a fases futuras).
10. Reintroducción del campo *Recursos estimados* (decisión D11: fuera del MVP, reversible en el futuro).

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
10. **Catálogo por zonas:** 4 pestañas (En proceso/Aceptadas/Rechazadas/Archivadas), cada una solo con su estado, en vista compacta (título, fecha de publicación, descripción); al abrir, la vista de detalle muestra los 6 campos, el debate y la evaluación; de solo lectura, sin datos de contacto.
11. **Debate:** mensajes de cualquier usuario con sesión; cierre automático a 30 días; ajuste de fecha por idea del administrador; `@asistant` responde con el mensaje enlazado; al cierre, resumen de la IA visible y el debate **compactado** con enlace al chat completo en otra vista de solo lectura.
12. **Evaluación:** generada al cerrarse el debate sobre 5 criterios (1–10 + justificación; pendiente si la IA cae, con reintento); la idea vuelve a la cola de validación (etapa de calificación); el especialista puntúa (aceptando la de la IA o con la suya), el **promedio** muestra el resultado derivado en vivo, la decisión **coincide** con el promedio, se confirma con aviso y deja un único juicio final auditado; el creador es notificado.
13. **Contexto de empresa:** plantilla descargable, edición en línea y subida de archivo; vacío detectado con aviso; inyectado en captura, título, mejoras, debate y evaluación.
14. **Presentación:** tema claro/oscuro persistido, vista de ajustes, maquetación responsive.
15. **Casos límite:** verificados 1, 2, 5, 6, 7, 13, 16, 17, 18, 20, 22, 26, 27, 28, 29, 30.
16. **Pruebas:** `pytest -q` pasa al completo (backend).
17. **Conformidad:** estructura por features y capa compartida según Constitución; guías de Angular y Tailwind respetadas.
18. **Estados finales:** aceptar/archivar/rechazar mueven la idea a su zona del catálogo; motivo obligatorio en rechazo y archivo; solo las ARCHIVADAS se reevalúan (vuelven a la cola conservando debate e IA).

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
| 12 | **Debate y evaluación son atributos de la idea publicada, no estados:** el debate se cierra por fecha límite (30 días por defecto, ajustable idea por idea por el administrador) y la evaluación es única (IA o del especialista). No se introducen los estados formales *En debate*/*En evaluación* de la v1.0 (v2.2: los estados **finales** ACEPTADA/ARCHIVADA/RECHAZADA sí existen como salidas de VALIDADA_PUBLICA, §5.10). | RF-24, RF-26, RF-27, §5.10 |
| 13 | **Contexto de empresa:** se gestiona como un único documento (plantilla + edición en línea + subida de archivo) y se inyecta en TODAS las operaciones de la IA. Sustituye/expande el perfil de organización de la v2.0 (D7): el perfil queda dentro del documento. | RF-21, RF-22, RNF-12 |
| 14 | **@asistant en el debate:** la intervención del asistente es bajo invocación explícita citando un mensaje concreto; el resumen final del debate lo genera la IA al cerrarse (si hubo mensajes). El debate no es un chat asistido continuo. | RF-24, RF-25 |
| 15 | **Evaluación IA:** 5 criterios fijos (*claridad del problema, factibilidad, impacto esperado, alineación estratégica, grado de innovación*), puntuación 1–10 + justificación por criterio; se genera al cerrarse el debate; el especialista la acepta o la sustituye por su propia sobre los mismos criterios. No hay scoring global 0–100. | RF-26 |
| 16 | **Catálogo en vista compacta:** el listado muestra solo título, fecha de publicación y descripción; el resto (6 campos, debate, evaluación) se ve en la vista de detalle de la idea. | RF-20, RF-23 |
| 17 | **Preferencia de presentación:** tema claro/oscuro elegible por el usuario, persistido entre sesiones, con vista de ajustes accesible del menú y maquetación responsive. | RNF-13 |
| 18 | **Decisión final con confirmación:** el especialista puntúa los 5 criterios (aceptando la IA o con la suya); el promedio da el resultado (RF-28) que se muestra en vivo; el resultado final elegido debe coincidir con el promedio (no se fuerza); la confirmación avisa de la consecuencia y da opción de volver; rechazar y archivar exigen motivo; se audita (RNF-8) y se notifica al creador (RF-18). | RF-27, RF-28, RF-18, RNF-8 |
| 19 | **Umbrales por promedio simple:** promedio = suma de los 5 criterios / 5; bandas: < umbralRechazo → rechazada; umbralRechazo ≤ promedio < umbralAceptacion → archivada; ≥ umbralAceptacion → aceptada; umbrales configurables por el administrador (defecto 4/7, enteros 1–10, rechazo < aceptación); solo afectan decisiones posteriores. | RF-28, §7 caso 26, 31 |
| 20 | **Estados finales y zonas:** ACEPTADA y RECHAZADA son terminales (sin reevaluación en el MVP); ARCHIVADA admite reevaluación del creador (vuelve a la cola conservando debate cerrado y evaluación IA, limpiando la decisión previa); el catálogo se organiza en 4 zonas (En proceso/Aceptadas/Rechazadas/Archivadas). | RF-29, RF-20, §5.10, §8.7 |
| 21 | **Compactado del debate cerrado:** en la ficha, el debate cerrado muestra solo el resumen (o el aviso de que no hubo debate) y un enlace al chat completo en otra vista de solo lectura. | RF-24, §7 caso 18, 21 |
