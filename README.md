# Innov-IA

Plataforma web inteligente para la **captura, estructuración y evaluación automatizada de
iniciativas de innovación**, con la ayuda de un modelo de lenguaje local (Ollama).

- **Backend:** FastAPI sobre Python, arquitectura por features (auth, users, ideas, capture,
  validation, assistant, notifications), persistencia local en JSON (sin base de datos) y sin
  dependencias externas al stack base.
- **Frontend:** Angular 20+ + Tailwind CSS, organizado por features, con rutas lazy,
  interceptores de autenticación/errores, sesión reactiva y guards por rol.
- **IA:** un cliente local que consulta a Ollama para la captura asistida (7 campos),
  generación de títulos, mejoras y refinamiento de ideas.

La especificación del MVP y su plan de desarrollo viven en
`specs/001-innovation-evaluation-mvp/` (spec, plan, tareas y grupos de desarrollo vertical).
Consultar también `docs/constitution.md` y las guías de `docs/guides/`.

## Estructura

```
backend/            API FastAPI (app/, features/, shared/, tests/, pyproject.toml)
  features/<feature>/   cada feature con domain/ use_cases/ infrastructure/ routers/
  shared/               contratos, persistencia JSON, errores, config, contraseñas
  tests/                pytest (unit + api), stores in-mem y mock de Ollama
frontend/         Aplicación Angular (src/app: features/ + shared/)
  src/app/features/<f>/  auth, admin, capture, my-ideas, validation, catalog
  src/app/shared/        layout, guards, interceptores, sesión, tipos, componentes comunes
specs/            especificación y plan del MVP (grupos 01..16, tasks.md)
docs/             constitution y guías técnicas (FastAPI, Angular, Tailwind)
```

## Requisitos

- Python 3.12+ y Node.js 20+ (npm). El backend **no se instala como paquete**: se corre
  desde `backend/` (por eso los tests pasan `pythonpath=["."]` en `pyproject.toml`).
- Ollama corriendo en `http://localhost:11434` **solo** para las funciones de IA
  (captura asistida, mejoras, refinamiento). Login, usuarios, ideas manuales, validación y
  notificaciones funcionan sin él: el sistema degrada a manual cuando la IA no responde.

## Arrancar el backend (puerto 8000)

```bash
cd backend
# solo la primera vez:
python3 -m venv .venv
.venv/bin/pip install fastapi pydantic uvicorn pytest ruff httpx   # como en pyproject.toml
INNOV_ADMIN_USERNAME=admin INNOV_ADMIN_PASSWORD=admin123 \
  .venv/bin/uvicorn app.main:app --reload
```

- Al arrancar por primera vez siembra el administrador inicial (idempotente) con el
  usuario/contraseña de las variables de entorno: **admin / admin123** (cámbialas; sin
  `INNOV_ADMIN_PASSWORD` no se siembra nadie y habrá que crearlo por API).
- Datos persistentes en `backend/data/` (`users.json`, `sessions.json`), ignorada por git.
- Verificación: `curl http://localhost:8000/health` → `{"status":"ok"}`.
- Endpoints de la API actual: `/auth/*` (login, logout, me, change-password),
  `/users*` (listado, alta con contraseña temporal, roles, habilitar/desactivar) y `/health`.
  El resto del plan aparece conforme se implementan sus grupos.
- Tests y lint: `cd backend && .venv/bin/pytest -q && .venv/bin/ruff check .`

## Arrancar el frontend (puerto 4200)

```bash
cd frontend
npm install          # solo la primera vez
ng serve
```

La app queda en `http://localhost:4200`. El dev-server carga `ng serve` con el proxy
(`proxy.conf.json`, declarado en `angular.json`) y reenvía todas las peticiones de la API
(`/auth`, `/users`, `/ideas`, `/capture`, `/validation`, `/catalog`, `/notifications`,
`/assistant`, `/health`) al backend en `http://localhost:8000`. Así el frontend usa URLs
relativas y, en desarrollo, **los dos servicios quedan conectados sin CORS**.

## Verlos trabajando juntos (recorrido actual)

Con ambos corriendo (8000 y 4200), en `http://localhost:4200` ya se puede ejercitar:

1. **Login** (`/login`): entrar con `admin` / `admin123`. Con credenciales inválidas el
   aviso no revela qué dato falló.
2. **Layout**: sidebar con el usuario, sus roles y "Cerrar sesión"; páginas `Mis ideas`,
   `Catálogo`, `Nueva idea`, `Validación` (solo especialista) y `Administración` (solo admin).
3. **Administración** (`/admin`): crear usuarios (la contraseña temporal se muestra una sola
   vez, con helper de copiado), habilitar/desactivar y asignar/revocar roles. El servidor
   bloquea (409) dejar la plataforma sin administrador.
4. **Primer acceso forzado**: un usuario recién creado entra con su temporal y es obligado a
   cambiarla antes de cualquier otra acción.
5. **Guards por rol**: sin sesión, solo existe `/login`; cada sección protege su rol y un 401
   en cualquier llamada limpia la sesión y devuelve a login.

Lo demás (captura asistida, mis ideas, validación, catálogo, notificaciones, asistente) va
apareciendo en sus páginas conforme se cierran los grupos de `specs/.../groups/`; mientras, las
páginas muestran su placeholder.

> **Nota:** `ng build` produce un bundle estático que no lleva el proxy de desarrollo; para
> servirlo de forma conectada en producción habría que reenviar la misma lista de rutas
> (p. ej. con `nginx`) — el proxy de dev existe solo para el ciclo de trabajo.

## Cómo ver el avance

- `ng serve` recalcula al guardar (hot reload): los cambios del frontend se ven al momento en
  el navegador.
- `uvicorn --reload` reinicia el backend al guardar cualquier Python.
- Estado de lo hecho/pendiente: `specs/001-innovation-evaluation-mvp/tasks.md` (tareas con
  casillas) y los grupos de `specs/001-innovation-evaluation-mvp/groups/` (vertical de BE ↔ FE
  por grupo, con criterio de salida).
- Verificación continua: backend con `pytest -q` y `ruff check .`; frontend con `ng build`
  (sin tests automatizados por decisión del plan).
