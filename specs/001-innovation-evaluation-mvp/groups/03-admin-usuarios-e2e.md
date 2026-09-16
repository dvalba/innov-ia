# Grupo 03 — Administración de usuarios y roles (e2e)

**Vertical:** el panel `/admin` — listado de usuarios, creación con contraseña temporal única
vez, desactivar/habilitar y matriz de roles — cerrando el ciclo completa con la e2e de
usuarios/roles (crear → temporal → cambio forzado → revocar → último admin).

## Tareas (orden de ejecución)

| # | ID | Capa | Tarea | Dependencias |
|---|------|------|-------|--------------|
| 1 | T-053 | FE | `/admin` usuarios: listado, `user-form` (crear → 201 muestra temporal una única vez), desactivar/habilitar (409 último admin mostrado sin aplicar) | T-039 (G02), T-016 (G02) |
| 2 | T-054 | FE | `role-matrix`: asignar/revocar roles por usuario (`PUT /users/{id}/roles`), estado actual, bloqueo por 409 de último admin, "sin acceso a funciones" | T-053 |
| 3 | T-067 | E2E | e2e usuarios/roles: admin crea → temporal → el usuario entra y cambia contraseña; revocar/desactivar → pierde acceso, ideas e historial conservados (caso 16); ideas SOLICITANDO de desactivado siguen validables; último admin bloqueado en UI y backend | T-054, T-016 (G02) |

## Flujo extremo a extremo

1. El admin (G02 le da el rol) abre `/admin` (T-053): crea usuario vía `POST /users`; la
   contraseña temporal (201) se muestra una única vez para entregarla.
2. El usuario nuevo inicia sesión (G02) y es obligado a cambiarla.
3. `role-matrix` (T-054) asigna/revoca roles; la UI refleja el estado y bloquea la acción si el
   backend responde 409 (último administrador).
4. e2e (T-067) recorre todo: creación → temporal → cambio forzado → desactivación/revocación con
   historial intacto (caso 16) y bloqueo del último admin en las dos capas.

## Criterio de salida

* `ng build` verde; `pytest -q` verde (revalida `tests/api/test_users_api.py`); smoke manual de la
  e2e documentado con capturas.

## Qué no se rompe

* No modifica la API de users/auth; solo la consume. La UI respeta los 409/403 del backend sin
  re-implementar reglas de negocio.
