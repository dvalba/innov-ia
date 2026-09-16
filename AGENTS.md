# AGENTS.md - Innov-IA

## Proyecto

Plataforma web inteligente para la captura, estructuración y evaluación automatizada de iniciativas de innovación mediante la integración de un modelo de lenguaje local en Ollama. Arquitectura basada en FastAPI (Python 3.14+) y Angular 20+ con Tailwind CSS.

## Comandos

* **Backend:** `cd innov-ia/backend && uvicorn app.main:app --reload`
* **Frontend:** `cd innov-ia/frontend && ng serve`
* **Pruebas:** `pytest -q`
* **Linting Backend:** `ruff check .`

## Estilo y convenciones

* **Backend:** Python 3.14+ (ver `docs/guides/backend-fastapi-guidelines.md`).
* **Frontend:** Angular 20+ (ver `docs/guides/angular-guidelines.md`).
* **Estilos:** Tailwind CSS (ver `docs/guides/tailwind-guidelines.md`).
* **Nomenclatura e Idioma:** Código, variables e identificadores en inglés. Interfaz de usuario y mensajes finales en español.

## Reglas Operativas

* **Lectura previa:** Consultar `docs/constitution.md` y la especificación activa en `specs/` antes de modificar código.
* **Guías técnicas:** Revisar la guía correspondiente en `docs/guides/` antes de implementar cambios en el backend, frontend o estilos.
* **Control de especificaciones:** Prohibida la modificación de archivos en `specs/` salvo solicitud explícita.
* **Pruebas:** Exclusivas para el backend (`pytest`). El frontend no incluye pruebas automatizadas.
* **Dependencias:** Prohibido añadir paquetes externos en el backend sin consulta previa y propuesta de alternativa nativa.

## Protocolo de Cierre de Tareas

* Ejecutar `pytest -q` y confirmar formalmente que todas las pruebas pasaron con éxito.