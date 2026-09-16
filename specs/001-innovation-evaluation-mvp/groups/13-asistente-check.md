# Grupo 13 — Asistente: casos de uso y endpoint `/assistant/check` (backend)

**Vertical:** los casos de uso del asistente (disponibilidad, sugerencia de título, mejora,
refinamiento manual, cola) y el endpoint `POST /assistant/check` con sus disparadores internos
bajo demanda. Conecta el motor de G04 con el núcleo de ideas (G06) y las notificaciones (G10).

## Tareas (orden de ejecución)

| # | ID | Capa | Tarea | Dependencias |
|---|------|------|-------|--------------|
| 1 | T-061 | BE | `check_availability.py` (ping + reintento), `suggest_title.py` (integra IA; alimenta a `capture` vía contrato), `improve_idea.py` (UC que genera versión pendiente; sin IA → solicitud pendiente, caso 10), `refine_manual.py` (versión `requestedBy=refinement` + `IDEA_REFINED` al proponente, RF-12), `run_refinement_queue.py` (cola más antigua→reciente; fallo parcial: lo conservado se queda y lo fallido sigue pendiente, caso 6; la idea sigue operativa, RF-11) | T-060 (G04), T-024 (G06), T-033 (G10) |
| 2 | T-062 | BE | `POST /assistant/check` (rol proponente; verifica disponibilidad y procesa la cola, devuelve nº de ideas refinadas + fallos) + disparadores internos en login (T-013), `/capture/start` (T-031) y al solicitar mejora (T-024); no bloquean la respuesta principal | T-061, T-013 ✓, T-031 (G08) |

## Flujo extremo a extremo

1. El proponente tiene una idea manual sin versión refinada. Al iniciar sesión (login, T-013), al
   iniciar captura (`/capture/start`, G08) o al solicitar mejora (T-024, G06) se dispara
   `POST /assistant/check` (T-062) de forma no bloqueante.
2. Si la IA está disponible, `run_refinement_queue` procesa la cola (más antigua→reciente, G04):
   cada idea manual EN_DESARROLLO sin refinada se genera (`refine_manual`) y emite `IDEA_REFINED`
   (G10). Si un item falla, se conserva lo refinado y lo fallido sigue pendiente (caso 6).
3. `suggest_title` alimenta a `capture` (G07/G08) vía contrato; `improve_idea` deja con IA real la
   mejora pendiente del G06; al recuperar la IA la cola se procesa en el siguiente disparo sin
   caducidad (caso 5, RNF-1).
4. La UI lo consume indirectamente: "Mis ideas"/`refine-view` (G11) disparan el check al abrir una
   idea manual pendiente y muestran la versión refinada.

## Criterio de salida

* `pytest -q` verde con `tests/unit/use_cases/test_refinement.py` (cola completa, fallo parcial,
  mejora sin IA, disparadores) y `tests/api/test_assistant_api.py` (invocación directa,
  integración login/capture, idempotencia).
* `ruff check .` limpio.

## Qué no se rompe

* No redefine `adjust_in_chat` ni `improve_idea` (G06): consume sus contratos y les inyecta el
  cliente IA real (G04).
* La notificación `IDEA_REFINED` reutiliza store/fanout de G10: no añade un 5º tipo de evento.
* Los disparadores internos son asíncronos/no bloqueantes: la latencia de login y `/capture/start`
  no se degrada.
