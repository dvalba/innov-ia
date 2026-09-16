# Grupo 01 — Núcleo del frontend (shell, interceptores, sesión, modelos)

**Vertical:** la base Angular sobre la que se construye todo el frontend: proyecto + Tailwind +
rutas lazies + layout, interceptores, `SessionService` y modelos TS compartidos. Sin backend
pendiente: solo consume `T-001..T-003` ya hechos.

## Tareas (orden de ejecución)

| # | ID | Tarea | Dependencias |
|---|------|-------|--------------|
| 1 | T-004 | Proyecto Angular 20+ con Tailwind, rutas lazies (`/login`, `/captura`, `/mis-ideas`, `/validacion`, `/catalogo`, `/admin`) y layout shell | Ninguna |
| 2 | T-005 | Interceptores auth (inyecta portador, 401 → limpia sesión y redirige a `/login`) y de errores (normaliza formato §3.6) | T-004 |
| 3 | T-006 | `SessionService`: señales `sesionActiva`/`usuario`/`roles`, `iniciar`/`cerrar`/`tieneRol`, localStorage | T-005 |
| 4 | T-009 | Modelos TS espejo de los esquemas §2, utilidades de fecha en español y `badge-state` (operable con teclado, UI ES) | T-004 |

## Criterio de salida

* `ng build` verde. Rutas lazy registradas; layout con sidebar; interceptores y `SessionService`
  operativos (verificable al ejecutar G02).

## Qué no se rompe

* Solo crea estructura base (`shared/`); ninguna feature existe aún, así que no hay código
  funcional previo que alterar.
