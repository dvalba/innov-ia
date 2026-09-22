# Grupo 11 — "Mis ideas" (UI) con mejoras y refinamiento

**Vertical:** la vista del proponente sobre sus ideas — listado, detalle con edición manual y
solicitud de publicación, mejora solicitada a la IA (versión pendiente + decisión) y refinamiento
de ideas manuales (versión refinada vs original, aceptar/ajustar en chat) + nota de rechazo.

## Estado

> ⬜ **Pendiente** — 0/5 tareas implementadas.

## Tareas (orden de ejecución)

- [ ] **T-046** _(FE)_ — Listado "Mis ideas" (`GET /ideas/me`, `httpResource`): título, fecha, origen, estado con `badge-state` (G01), ordenado por fecha, estado vacío en ES; permite abrir cualquiera _(T-039 G02, T-023 G06)_
- [ ] **T-047** _(FE)_ — `pages/detail`: 7 campos, origen/estado/`reviewedByAI` (RNF-2); en EN_DESARROLLO: formulario de edición (PUT, bloqueo visual con aviso si hay generación en curso) + botón "Solicitar publicación" (disponible aunque la idea no haya sido vista por IA); en SOLICITANDO muestra fecha y no permite edición _(T-046)_
- [ ] **T-048** _(FE)_ — "Solicitar mejora a la IA" (campo de instrucción → `POST /ideas/{id}/improve`; sin IA, aviso de solicitud registrada, caso 10); versiones PENDIENTE listadas con campos propuestos y "Aceptar versión"/"Descartar" (decisión única); al aceitar pasa a vigente, idea sigue EN_DESARROLLO _(T-047)_
- [ ] **T-049** _(FE)_ — `refine-view`: versión refinada diferenciada de la original (campo por campo) con "Aceptar la versión" (decisión; sigue EN_DESARROLLO) y "Ajustar detalles en el chat" (conversación precontextualizada sobre la idea, no nueva captura; sin IA → edición manual); al abrir una idea manual pendiente dispara `POST /assistant/check` _(T-048, `chat-message` G08)_
- [ ] **T-050** _(FE)_ — `reject-note`: cuando la idea fue rechazada, muestra el comentario del especialista con su identidad y fecha, en el detalle y accesible desde la notificación (G12) _(T-047)_

## Flujo extremo a extremo

1. Las ideas creadas por captura (G08/G09) o manual aparecen en el listado (T-046) con su badge.
2. El dueño edita campos en `EN_DESARROLLO` (T-047); si hay generación en curso el backend 409 (G06)
   y la UI muestra bloqueo visual.
3. "Solicitar mejora" pide una versión a la IA (T-024, G06); la versión PENDIENTE se decide con
   Aceptar/Descartar (T-048, endpoint `decide` de G06).
4. Para ideas manuales, `refine-view` (T-049) compara la versión refinada con la original y ofrece
   aceptar o "ajustar en chat" (reutiliza el chat de G08 vía `adjust_in_chat`, G06); el disparo de
   `/assistant/check` procesa la cola (G15).
5. Tras un rechazo, `reject-note` (T-050) muestra el comentario con identidad y fecha.

## Criterio de salida

* `ng build` verde.
* Manual (mock): idea asistida/manual visible → editar → solicitar mejora → aceptar versión →
  solicitud de publicación → estado SOLICITANDO sin edición; idea refinada (manual) →
  `refine-view` → aceptar/ajustar; rechazada → nota visible.

## Qué no se rompe

* No modifica el router ni los UC de ideas (G06); solo los consume. Reutiliza `chat-message` de
  G08 para "ajustar en chat" sin forzar cambios al componente.
* `badge-state` y modelos de G01 se reutilizan tal cual.
