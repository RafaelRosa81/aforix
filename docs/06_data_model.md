# Modelo de datos de Aforix

Este documento describe las capas de datos y las tablas principales usadas por Aforix.

La referencia funcional del pipeline está en `docs/02_pipeline.md`. La arquitectura técnica está en `docs/ARCHITECTURE.md`.

## Capas de datos

Aforix organiza los datos en capas para separar archivos originales, salidas intermedias y datasets normalizados.

```text
raw -> runs -> database/raw_canonical -> database/normalized -> database/validation -> outputs
```

## raw

Contiene archivos originales generados por los instrumentos.

Ejemplos:

- archivos FlowTracker;
- planillas Molinete;
- archivos XML Nivus;
- archivos M9 / ADCP, pendiente de definición completa.

Reglas:

- no modificar manualmente los archivos raw;
- conservar los archivos originales como respaldo;
- cargar correctamente ID y nombre del punto en el instrumento antes de medir.

## runs

Contiene salidas por ejecución.

Ejemplo:

```text
runs/ingest_flowtracker/<timestamp>/outputs/
```

Uso principal:

- trazabilidad;
- auditoría;
- depuración;
- comparación entre ejecuciones.

## database/raw_canonical

Contiene datos estructurados, organizados y consolidados, pero todavía cercanos a cada instrumento.

Características:

- puede conservar nombres de columnas específicos del instrumento;
- puede tener tablas distintas según instrumento;
- es la entrada principal de la normalización.

## database/normalized

Contiene datos bajo un esquema común. Es la capa recomendada para validación, exportación y análisis.

Características:

- columnas homogéneas entre instrumentos;
- unidades consistentes;
- trazabilidad a instrumento, archivo fuente y ejecución;
- tablas comunes como `Summary` y `Points`.

## database/validation

Contiene reportes de validación aplicados sobre datos normalizados.

Ejemplos:

- chequeos de columnas requeridas;
- duplicados;
- completitud;
- rangos;
- consistencia hidráulica.

## outputs

Contiene salidas finales para usuarios, por ejemplo archivos Excel o CSV exportados.

## Identificadores comunes

Las tablas normalizadas deben preservar campos que permitan identificar cada medición.

| Campo | Descripción |
| --- | --- |
| `station_id` | Identificador corto y estable del punto de aforo. |
| `station_name` | Nombre descriptivo del punto de aforo. |
| `measurement_date` | Fecha de medición, preferentemente en formato `YYYYMMDD`. |
| `measurement_time` | Hora de medición, preferentemente en formato `HHMMSS`. |
| `instrument` | Instrumento de medición usado. |
| `source_file` | Archivo original del que proviene el dato. |
| `source_run_dir` | Carpeta de ejecución que generó el dato. |
| `run_id` | Identificador de la ejecución, si está disponible. |

## Tabla Summary

`Summary` representa una medición completa de caudal en un punto y momento determinados.

Cada fila debería corresponder a una medición agregada.

Columnas típicas:

| Campo | Descripción | Unidad sugerida |
| --- | --- | --- |
| `station_id` | ID del punto de aforo | texto |
| `station_name` | nombre del punto | texto |
| `measurement_date` | fecha de medición | `YYYYMMDD` |
| `measurement_time` | hora de medición | `HHMMSS` |
| `instrument` | instrumento usado | texto |
| `q_total_m3s` | caudal total | m³/s |
| `q_total_ls` | caudal total | l/s |
| `area_total_m2` | área mojada total | m² |
| `width_total_m` | ancho total | m |
| `velocity_mean_m_s` | velocidad media | m/s |
| `depth_mean_m` | profundidad media | m |
| `temperature_c` | temperatura | °C |
| `source_file` | archivo fuente | texto |
| `source_run_dir` | run fuente | texto |
| `run_id` | ID de ejecución | texto |

Uso recomendado:

- series de caudal por punto;
- comparación entre instrumentos;
- exportación resumida;
- validación contra suma de puntos.

## Tabla Points

`Points` representa posiciones, verticales o puntos internos de una medición.

Cada fila debería corresponder a una vertical o punto de medición dentro de un aforo.

Columnas típicas:

| Campo | Descripción | Unidad sugerida |
| --- | --- | --- |
| `station_id` | ID del punto de aforo | texto |
| `station_name` | nombre del punto | texto |
| `measurement_date` | fecha de medición | `YYYYMMDD` |
| `measurement_time` | hora de medición | `HHMMSS` |
| `instrument` | instrumento usado | texto |
| `point_index` | índice numérico del punto o vertical | entero |
| `point_label` | etiqueta del punto o vertical | texto |
| `distance_m` | distancia progresiva o posición transversal | m |
| `depth_m` | profundidad local | m |
| `velocity_mean_m_s` | velocidad media local | m/s |
| `area_m2` | área asociada al punto o vertical | m² |
| `q_m3s` | caudal parcial | m³/s |
| `q_ls` | caudal parcial | l/s |
| `percent_q` | porcentaje del caudal total | % |
| `temperature_c` | temperatura | °C |
| `source_file` | archivo fuente | texto |
| `source_run_dir` | run fuente | texto |
| `run_id` | ID de ejecución | texto |

Uso recomendado:

- validación hidráulica;
- control de distribución transversal;
- revisión de verticales;
- cálculo de sumas parciales por medición.

## Tabla Sections

`Sections` representa secciones, segmentos o divisiones internas del aforo cuando el instrumento las provee.

No todos los instrumentos generan esta tabla.

Usos posibles:

- reconstrucción de caudal parcial;
- enriquecimiento de `Points`;
- validación de área y distribución de caudal.

## Tabla Gates

`Gates` representa compuertas o estructuras asociadas al aforo cuando existen en el formato del instrumento.

No todos los instrumentos generan esta tabla.

## Relación entre Summary y Points

Para una misma medición, `Summary` y `Points` deberían poder relacionarse mediante claves comunes:

```text
station_id + measurement_date + measurement_time + instrument
```

Cuando exista trazabilidad suficiente, también pueden usarse:

```text
source_file + run_id
```

Chequeos típicos:

```text
sum(Points.q_m3s) ≈ Summary.q_total_m3s
sum(Points.area_m2) ≈ Summary.area_total_m2
```

Las diferencias aceptables dependen del instrumento, redondeos y criterios de cálculo.

## Unidades recomendadas

| Variable | Unidad normalizada |
| --- | --- |
| Caudal | m³/s y/o l/s |
| Área | m² |
| Ancho | m |
| Profundidad | m |
| Velocidad | m/s |
| Temperatura | °C |
| Distancia transversal | m |

## Reglas generales

- Mantener `station_id` estable entre instrumentos y campañas.
- Mantener `measurement_date` y `measurement_time` en formatos comparables.
- No usar columnas de análisis final como sustituto de datos raw o normalizados.
- No hacer análisis directamente sobre archivos raw si existe una tabla normalizada equivalente.
- Preservar trazabilidad siempre que sea posible.

## Campos pendientes o experimentales

Algunos campos pueden variar mientras se consolidan adaptadores o instrumentos nuevos.

En particular:

- M9 queda pendiente hasta analizar los formatos base;
- algunas columnas pueden existir solo para ciertos instrumentos;
- `Sections` y `Gates` pueden estar vacías para instrumentos que no las proveen.

## Próximos pasos recomendados

- Definir schemas mínimos obligatorios para `Summary` y `Points`.
- Documentar diferencias por instrumento.
- Agregar ejemplos reales anonimizados.
- Incorporar pruebas automáticas de validación de schemas.
