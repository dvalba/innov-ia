# Grupo 02 — Sesión y autenticación de extremo a extremo

**Vertical:** router `/users` (T-016) en backend + login, cambio forzado de contraseña, cierre
de sesión y guards de rutas en frontend, conectando la API de auth (T-010..T-013, ya hecha) con
el login y los guards del frontend. Deja lista la vertical de usuarios para que G03 (admin)
consuma sus 403/409.

## Tareas (orden de ejecución)

| # | ID | Capa | Tarea | Dependencias |
|---|------|------|-------|--------------|
| 1 | T-016 | BE | Router `/users`: `GET/POST /users`, `PUT /{id}/roles`, `PATCH /{id}/active` (rol admin, 403 no-admin, 409 último admin; 201 con contraseña temporal) | T-015 ✓, T-013 ✓ |
| 2 | T-037 | FE | `AuthService` (login → `SessionService`) + página login (mensajes ES, fallo sin indicar campo) | T-006 (G01), T-013 ✓ |
| 3 | T-038 | FE | Cierre de sesión en sidebar + diálogo de cambio forzado de contraseña en primer acceso | T-037 |
| 4 | T-039 | FE | Guards `canActivate`: sin sesión → solo `/login`; por rol (`/validacion`→especialista, `/admin`→admin, `/captura`/`/mis-ideas`→proponente) | T-038 |

## Flujo extremo a extremo

1. `POST /auth/login` (T-013, ya hecho) → `AuthService` almacena sesión en `SessionService` →
   redirección al layout (T-037).
2. Usuario con `debeCambiar` → diálogo forzoso → `POST /auth/change-password` (T-013, ya hecho)
   antes de cualquier acción; "Cerrar sesión" llama a `POST /auth/logout` (T-038).
3. Guards (T-039) protegen todas las rutas; un 401 en cualquier llamada limpia la sesión
   (interceptor de G01) y vuelve a login.
4. `T-016` deja listo el API de administración (403 para no-admin, 409 último admin, 201 con
   temporal) que G03 ejercita desde la UI.

## Criterio de salida

* `pytest -q` verde con `tests/api/test_users_api.py` (201 temporal, 403, 409 último admin);
  `ruff check .` limpio; `ng build` verde.
* Manual: login → layout; login con `debeCambiar` → cambio forzado; rutas protegidas redirigen
  según rol.

## Qué no se rompe

* Reutiliza las dependencias `requerir_sesion`/`requerir_rol` de T-013 sin modificar la API de
  auth existente (T-010..T-013).
* Los guards no tocan features ya construidas; las rutas de G01 se rellenan con `canActivate`.
