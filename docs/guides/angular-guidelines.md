# docs/guides/angular-guidelines.md

# Angular v20+ Guidelines

## 1. Componentes y Metadata

- **Metadata limpia:** Incluir únicamente configuraciones no predeterminadas en `@Component`. Omitir `standalone: true` y `changeDetection`.
- **Sintaxis autocerrada:** Usar sintaxis autocerrada (ej. `<app-card />`) cuando el componente no reciba proyección de contenido (`<ng-content>`).

## 2. Templates y Control Flow

- **Control flow nativo:** Usar exclusivamente `@if`, `@for` (con `track` obligatorio) y `@switch`. Prohibido el uso de directivas estructurales tradicionales (`*ngIf`, `*ngFor`, `*ngSwitch`).
- **Bindings nativos:** Usar `[class]` directamente en los elementos HTML. Evitar `ngClass` salvo excepciones complejas justificadas.

## 3. Estado Reactivo y Propiedades (Signals)

- **Propiedades del componente:** Usar exclusivamente `input()`, `input.required()`, `output()` y `model()`. Prohibidos los decoradores `@Input()` y `@Output()`.
- **Estado local:** Utilizar `signal()` para estado local, `computed()` para valores derivados y `linkedSignal()` para derivados reescribibles.
- **Uso de `effect()`:** Reservar exclusivamente para integración con APIs imperativas externas (ej. `localStorage`, monitoreo). Prohibido usar `effect()` para sincronizar estado entre señales.

## 4. Inyección de Dependencias

- **Función `inject()`:** Inyectar todas las dependencias mediante `inject()`. Prohibida la inyección a través de los parámetros del constructor.

## 5. Comunicación HTTP

- **Lectura de datos (GET):** Preferir `httpResource` para peticiones asíncronas de lectura.
- **Mutaciones (POST/PUT/DELETE):** Usar `HttpClient` encapsulado exclusivamente dentro de servicios dedicados.

## 6. Nomenclatura

- **Intent over Role:** Nombrar las clases según su propósito funcional, omitiendo el sufijo `Component` (ej. `UserProfile` en lugar de `UserProfileComponent`).
