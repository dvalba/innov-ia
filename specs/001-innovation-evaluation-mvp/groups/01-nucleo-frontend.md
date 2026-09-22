# Grupo 01 — Núcleo del frontend (shell, interceptores, sesión, modelos)

**Vertical:** la base Angular sobre la que se construye todo el frontend: proyecto + Tailwind +
rutas lazies + layout, interceptores, `SessionService` y modelos TS compartidos. Sin backend
pendiente: solo consume `T-001..T-003` ya hechos.

## Estado

> ✅ **Completado** — 4/4 tareas implementadas y verificadas (2026-09-22).

## Tareas (orden de ejecución)

- [x] **T-004** — Proyecto Angular 20+ con Tailwind, rutas lazies (`/login`, `/captura`, `/mis-ideas`, `/validacion`, `/catalogo`, `/admin`) y layout shell _(sin deps)_
- [x] **T-005** — Interceptores auth (inyecta portador, 401 → limpia sesión y redirige a `/login`) y de errores (normaliza formato §3.6) _(T-004)_
- [x] **T-006** — `SessionService`: señales `sesionActiva`/`usuario`/`roles`, `iniciar`/`cerrar`/`tieneRol`, localStorage _(T-005)_
- [x] **T-009** — Modelos TS espejo de los esquemas §2, utilidades de fecha en español y `badge-state` (operable con teclado, UI ES) _(T-004)_

## Criterio de salida

* `ng build` verde. Rutas lazy registradas; layout con sidebar; interceptores y `SessionService`
  operativos (verificable al ejecutar G02).

## Qué no se rompe

* Solo crea estructura base (`shared/`); ninguna feature existe aún, así que no hay código
  funcional previo que alterar.
