# Grupo 03 — Administración de usuarios y roles (e2e)

**Vertical:** el panel `/admin` — listado de usuarios, creación con contraseña temporal única
vez, desactivar/habilitar y matriz de roles — cerrando el ciclo completa con la e2e de
usuarios/roles (crear → temporal → cambio forzado → revocar → último admin).

## Estado

> ✅ **Completado** — 3/3 tareas implementadas y verificadas (2026-09-22). Smoke real del
> servidor registrado abajo.

## Tareas (orden de ejecución)

- [x] **T-053** _(FE)_ — `/admin` usuarios: listado, `user-form` (crear → 201 muestra temporal una única vez), desactivar/habilitar (409 último admin mostrado sin aplicar) _(T-039 G02, T-016 G02)_
- [x] **T-054** _(FE)_ — `role-matrix`: asignar/revocar roles por usuario (`PUT /users/{id}/roles`), estado actual, bloqueo por 409 de último admin, "sin acceso a funciones" _(T-053)_
- [x] **T-067** _(E2E)_ — e2e usuarios/roles: admin crea → temporal → el usuario entra y cambia contraseña; revocar/desactivar → pierde acceso, ideas e historial conservados (caso 16); ideas SOLICITANDO de desactivado siguen validables; último admin bloqueado en UI y backend _(T-054, T-016 G02)_

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

## Registro de verificación (T-067, 2026-09-22)

**Automatizado** — `pytest -q` en `backend/`: 96 passed, incluyendo
`tests/api/test_users_roles_e2e.py` (ciclo completo vía TestClient sobre las dependencias
in-memory):

| Paso | Verificación | Resultado |
|---|---|---|
| 1 | `POST /users` 201 con `temporaryPassword` (≥ 12), `passwordHash` nunca expuesto; listado muestra la cuenta por cambiar | ✅ |
| 2 | Login con la temporal → 200 `mustChangePassword=true`; cambio forzado → 200 y flag en falso; la temporal deja de funcionar (401) y la nueva inicia sesión sin flag | ✅ |
| 3 | `PATCH /users/{id}/active` 200 → la sesión viva del desactivado responde 401 al instante (token revocado) y los nuevos logins fallan (401); la cuenta, la contraseña cambiada y las ideas del dueño permanecen en el directorio (`GET /users` y ledger in-mem) | ✅ (caso 16) |
| 4 | Ideas `SOLICITANDO_PUBLICACION` de un desactivado siguen en la cola que consumirán los especialistas (contra el contrato `IdeaLedger`, seam que consumirá `validation` al llegar G10); el desactivado no puede iniciar sesión | ✅ (caso 16) |
| 5 | Revocar todos los roles → la cuenta se conserva, la sesión vive sin roles ("sin acceso a funciones", endpoints por rol → 403); reasignar el rol restaura el acceso a la misma cuenta | ✅ (RF-17) |
| 6 | Último admin: revocar rol o desactivar → 409 `LAST_ADMIN_REQUIRED` sin aplicar; con un segundo admin activo el bloqueo se levanta y el nuevo admin queda protegido a su vez | ✅ (RF-17) |

**Smoke manual (servidor real)** — `uvicorn app.main:app --port 8031` con
`INNOV_DATA_DIR=/tmp/opencode/smoke03.zP8G/data` y seed del primer admin desde entorno; 27
verificaciones HTTP contra la instancia real (`curl`/urllib), todas en verde:
admin login; `carlos` creado (201 + temporal) → login → `mustChangePassword=true` → cambio
forzado → temporal 401 / nueva 200; segregación por rol (`/users` 403 para proponente);
desactivación → sesión viva 401 inmediata + re-login 401 + cuenta e historial conservados;
rehabilitación → acceso restaurado; último admin 409 doble vía (roles y active) y admin
sigue funcional. Captura del servidor en `/tmp/opencode/smoke03.zP8G/uvicorn.log`;
frontend `ng build` verde el mismo día.

**Nota de alcance:** "las ideas de un desactivado siguen validables" se verifica en el seam
compartido `IdeaLedger` (T-008): el endpoint `/validation/*` (G10) consume exactamente ese
objeto, por lo que la condición del caso 16 queda garantizada sin reimplementar la cola.
