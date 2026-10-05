# Aforix — Consultas al cliente

Este archivo reúne decisiones que requieren definición del cliente antes de modificar comportamiento de producción.

## Estado

- **PENDIENTE** — requiere respuesta del cliente.
- **RESPONDIDA** — el cliente definió el criterio; debe registrarse la decisión antes de implementar.
- **IMPLEMENTADA** — la decisión del cliente ya fue incorporada y verificada.

## Consultas pendientes

| ID | Tema | Consulta al cliente | Motivo | Estado |
|---|---|---|---|---|
| CLIENT-001 / MAIN-020 | SIH — `id_operador` | ¿Qué espera SIH en `id_operador`: nombre/texto del operador, un código, o un ID/clave foránea? Si requiere ID/código, ¿cuál es el catálogo o regla autoritativa para mapear los operadores de FlowTracker, Molinete y Nivus? | En Molinete el raw contiene texto libre como `I. Pérez`; FlowTracker y Nivus aparecen vacíos. El repositorio no contiene un lookup autoritativo de operadores. No corresponde inventar IDs. | **PENDIENTE** |

## Criterio de implementación

Las respuestas del cliente deben trasladarse primero a una regla/configuración explícita y trazable. Los IDs o equivalencias de dominio no deben inferirse ni hardcodearse sin una fuente autoritativa.
