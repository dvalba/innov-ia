# Constitución de Arquitectura y Gobierno Técnico - Innov-IA

## 1. Propósito y Alcance

Este documento constituye la norma suprema de diseño y gobernanza técnica para la plataforma **Innov-IA**. Establece las reglas arquitectónicas, los límites conceptuales y las pautas de organización de código que deben cumplirse de forma obligatoria en la implementación de la solución.

Ninguna adición, refactorización o modificación de código fuente podrá realizarse si vulnera los principios de independencia, separación de incumbencias y estructura por características (*features*) definidos en esta Constitución. Este documento actúa como la única fuente de verdad técnica para desarrolladores y agentes de inteligencia artificial.

---

## 2. Principios Fundamentales

La plataforma Innov-IA adopta una **Clean Architecture** orientada a características (**Feature-Driven Architecture**). Los pilares rectores son:

1. **Independencia del Dominio:** La lógica central de negocio no depende de marcos de trabajo (*frameworks*), librerías externas ni detalles de infraestructura.
2. **Encapsulamiento Vertical por Feature:** El código se organiza en torno a capacidades operativas y del negocio (ej. `innovations`, `evaluations`), agrupando los componentes por significado funcional y no por su tipo técnico global.
3. **Alta Cohesión y Bajo Acoplamiento:** Cada característica (*feature*) es autosuficiente. Las dependencias entre distintas características se gestionan exclusivamente mediante contratos explícitos en la capa compartida (`shared`).
4. **Enfoque Spec-First:** La definición funcional y de contratos de datos (esquemas JSON / API) precede obligatoriamente a la fase de codificación.

---

## 3. Arquitectura del Frontend (`innov-ia/frontend/src/`)

El cliente web se desarrolla sobre **Angular 20+** utilizando componentes *standalone* y una distribución espacial estrictamente modular.

### 3.1. Estructura de Directorios

```text
src/
├── app/
│   ├── shared/
│   │   ├── components/       # Componentes UI base reutilizables (botones, modales, cartas)
│   │   ├── layouts/          # Estructuras envolventes globales (ej. Sidebar + Main Content)
│   │   ├── interceptors/     # Interceptores HTTP globales
│   │   └── utils/            # Funciones de soporte y utilidades generales
│   │
│   └── features/
│       └── <feature_name>/   # Módulo encapsulado por característica (ej. home, innovations)
│           ├── pages/        # Componentes contenedores vinculados directamente a rutas
│           ├── components/   # Componentes visuales exclusivos de la feature
│           └── services/     # Estado local y comunicación HTTP de la feature

```

### 3.2. Reglas de la Capa Frontend

* **`shared/`:** Aloja únicamente elementos transversales empleados en múltiples características. Incluye la infraestructura de *layouts* que define el marco visual de la aplicación.
* **`features/`:** Cada carpeta dentro de `features/` representa una unidad funcional aislada. Un componente perteneciente a una *feature* no debe importar directamente componentes internos de otra *feature*; cualquier elemento común debe promoverse a `shared/`.

---

## 4. Arquitectura del Backend (`innov-ia/backend/`)

El servidor backend se implementa en **Python 3.14+** con **FastAPI**, guiado por un desacoplamiento riguroso de responsabilidades.

### 4.1. Estructura de Directorios

```text
backend/
├── shared/
│   ├── config/           # Variables de entorno y configuración general
│   ├── exceptions/       # Excepciones personalizadas y manejadores globales
│   └── utils/            # Herramientas base reutilizables
│
└── features/
    └── <feature_name>/   # Módulo encapsulado por característica de negocio
        ├── domain/       # Modelos de dominio puros y reglas de negocio
        ├── use_cases/    # Casos de uso e orquestación de la lógica
        ├── infrastructure/# Integración con Ollama, persistencia y clientes externos
        └── routers/      # Endpoints de FastAPI y esquemas de validación (Pydantic)

```

### 4.2. Reglas de la Capa Backend

* **`domain/`:** Contiene la lógica y estructuras de negocio más puras. Prohibido importar dependencias de FastAPI, Pydantic o librerías de infraestructura en esta capa.
* **`use_cases/`:** Coordina el flujo de datos desde y hacia los modelos de dominio.
* **`infrastructure/`:** Implementa los detalles técnicos (comunicación con la API local de Ollama, acceso a datos o servicios externos).
* **`routers/`:** Define las rutas HTTP, mapea entradas y salidas mediante esquemas Pydantic y delega la ejecución a los casos de uso correspondientes.

---

## 5. Gobernanza de Datos y Contratos de API

1. **Estrategia Spec-First:** La carpeta `specs/` almacena las especificaciones activas del sistema. Es obligatorio definir o actualizar la especificación correspondiente antes de modificar esquemas JSON o contratos de endpoints en el código fuente.
2. **Inmutabilidad de Contratos:** Queda prohibido alterar la estructura de entrada o respuesta de las APIs sin una actualización formal previa de la especificación técnica técnica en `specs/`.

---

## 6. Reglas Operativas Inviolables

1. **Política Estricta de Dependencias en Backend:** Se prohíbe la instalación o importación de paquetes externos en Python ajenos a las dependencias base del framework (`fastapi`, `pydantic`, `uvicorn`) y el entorno de pruebas (`pytest`). Toda necesidad técnica adicional debe resolverse con la **biblioteca estándar de Python** o ser consultada previamente presentando alternativas nativas.
2. **Delimitación del Entorno de Pruebas:** La automatización de pruebas se limita exclusivamente al **backend** (`pytest`). El frontend queda exento de suites de pruebas automatizadas.
