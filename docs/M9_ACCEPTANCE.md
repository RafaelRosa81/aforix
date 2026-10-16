# Aceptación local del flujo SonTek M9

Este documento resume las pruebas del flujo Aforix M9 y sus límites. Para instrucciones de uso, contenido MAT y criterios de IVE, consulte la [guía de procesamiento M9](M9_PROCESSING_GUIDE.md). Para repetir la auditoría de una colección local, consulte [M9_LOCAL_AUDIT.md](M9_LOCAL_AUDIT.md).

## Pruebas de regresión de ingesta

El 16/10/2026 se procesaron en Windows 181 MAT con la configuración de metadatos M9 del repositorio. La ingesta terminó con `Processed OK: 181/181`. Se compararon los 362 CSV de Summary y Points con el run previo: nombres, filas y valores coinciden exactamente salvo `run_id` y `source_run_dir`, que identifican cada ejecución.

La suite completa ejecutada para la integración de M9 y metadata terminó con **358 pruebas aprobadas y 4 omitidas**; el CI del PR también aprobó. El cambio de metadata no alteró cálculos hidráulicos, normalización, IVE ni mapeos SIH.

## Auditoría del recorrido completo

La auditoría local aislada abarcó ingesta, consolidación, normalización, validación, generación SIH y cotejo de las exportaciones. En la colección auditada había 182 MAT: se procesaron 181 y se excluyó explícitamente `20170901153604.mat`, que no contenía las estructuras requeridas `System` y `Summary`. No se modificaron los MAT originales ni se cargaron datos al servidor SIH.

Se generaron y revisaron **125 exportaciones**. El manifiesto final informó:

| Estado | Registros | Interpretación |
| --- | ---: | --- |
| `OK` | 107 | Pasaron los controles de la auditoría local. |
| `REVISAR` | 74 | Se conservaron, pero tienen observaciones que deben evaluarse antes de decidir su uso. |
| `EXCLUIDO` | 1 | Archivo excluido explícitamente por carecer de estructuras necesarias. |

No hubo registros clasificados como `ERROR` en el resultado final de esa auditoría. Los motivos de revisión incluyeron claves estación/fecha/hora compartidas por varios MAT, distancias repetidas en Points, aforos para los que el IVE no se obtuvo y campos hidráulicos incompletos. Los conteos y el detalle por archivo están en `audit_manifest.csv` y `audit_issues.csv` del run auditado; los avisos no son aprobación automática.

## Alcance comprobado y límites

- Cada MAT conserva su propia transecta `Summary`/`Points`; no se promedian transectas de un mismo aforo.
- Se verificó la generación local de CSV de actuación y aforo, metadatos SIH y libros IVE cuando aplicaban. La importación de esos archivos en el servidor SIH del cliente no se probó.
- El IVE M9 es una adaptación del método común de Aforix aplicada a muestras proyectadas a la normal de la transecta; no es QRev ni una incertidumbre certificada por SonTek. El método y las condiciones que lo dejan no disponible están descritos en la guía M9.
- El radio hidráulico se estima desde el área reportada y el perímetro calculado del perfil de profundidad, con supuestos de borde descritos en la guía M9.
- La aceptación cubre los MAT procesados en la colección disponible; no acredita todas las versiones/formas de exportación de RiverSurveyor Live ni sustituye revisión hidrométrica.

## Resultados de cuatro transectas de referencia

En la prueba aislada anterior con cuatro MAT de la estación 133 y equipo SonTek M9 serie 4980, las cuatro mediciones tuvieron IVE calculable y se generaron cuatro CSV de actuación, cuatro CSV de aforo y cuatro libros IVE. Los valores son resultados de esa muestra específica:

| Inicio | Muestras | Caudal SIH (m³/s) | Radio estimado (m) | IVE (%) | Error IVE (m³/s) |
|---|---:|---:|---:|---:|---:|
| 11:17:21 | 281 | 4.715018498 | 0.892821063 | 1.915032676 | 0.096598715 |
| 11:23:45 | 157 | 5.028343663 | 0.978510224 | 3.670255242 | 0.191381237 |
| 11:27:06 | 182 | 5.664091985 | 0.976741921 | 3.190490979 | 0.191338685 |
| 11:30:24 | 138 | 5.070337733 | 0.993061540 | 3.776879797 | 0.201103757 |

Estos resultados confirman el recorrido de ejemplo y la consistencia del software para esos archivos; no eliminan los casos `REVISAR` de la colección histórica.