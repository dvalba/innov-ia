# Backend Guidelines (Python 3.14+ / FastAPI)

## 1. Tipado Estricto y Validación

- Uso obligatorio de *type hints* en todas las funciones y métodos públicos.
- Validar esquemas de entrada y salida mediante modelos de datos estándar (FastAPI / Pydantic).

## 2. Biblioteca Estándar y Dependencias

- Permitido únicamente el uso de la biblioteca estándar de Python y las dependencias base: `fastapi`, `pydantic`, `uvicorn` y `pytest`.
- Para cualquier otra necesidad, es obligatorio consultar previamente presentando:
  1. La justificación de la necesidad.
  2. Una opción basada exclusivamente en código nativo (biblioteca estándar).
  3. La opción con la dependencia externa propuesta.

## 3. Calidad de Código

- Mantener el código limpio, legible y documentado.
- Cumplir estrictamente las reglas de análisis estático ejecutando `ruff check .`.
