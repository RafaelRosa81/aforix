# Guía de métricas de calidad de medición

Esta guía documenta el módulo de análisis de métricas de calidad de medición de Aforix.

El módulo se ejecuta desde la CLI con:

```bash
aforix analyze quality run -c configs/examples/main.yaml
```

## 1. Descripción general

El módulo de calidad calcula una métrica agregada de calidad de medición a partir de datos normalizados y datos raw canonical.

Actualmente el cálculo implementado es `CG(%)` para mediciones Nivus.

El módulo se ubica en la etapa de análisis del pipeline:

```text
raw -> ingest -> runs -> build-groups -> database/raw_canonical -> normalize -> database/normalized -> validate/export/analysis
```

El análisis usa:

- datos normalizados desde `database/normalized/`;
- datos raw canonical desde `database/raw_canonical/`;
- configuración desde `analysis.quality_metrics` en `main.yaml`.

Los resultados se escriben en:

```text
runs/analysis_quality_metrics/<timestamp>/
```

## 2. Alcance actual

Según el estado actual del código, el módulo está implementado para:

- Nivus.

El diseño de configuración separa instrumentos bajo:

```yaml
analysis:
  quality_metrics:
    instruments:
      nivus:
        ...
```

Esto permite extender el módulo a otros instrumentos en el futuro, como FlowTracker o Molinete. Actualmente, sin embargo, el procesamiento efectivo está implementado solo para Nivus.

## 3. Inputs del módulo

### 3.1 Datos normalizados

La raíz de datos normalizados se configura en:

```yaml
analysis:
  quality_metrics:
    input_dirs:
      normalized_root: database/normalized
```

Para Nivus, la tabla usada es:

```yaml
analysis:
  quality_metrics:
    instruments:
      nivus:
        tables:
          normalized_points: nivus/Points
```

Por defecto, esto resuelve a:

```text
database/normalized/nivus/Points/
```

El módulo itera archivos `*.csv` dentro de esa carpeta.

### 3.2 Variable clave: percent_q

La columna de peso se configura como:

```yaml
analysis:
  quality_metrics:
    instruments:
      nivus:
        columns:
          weight_column: percent_q
```

`percent_q` representa el porcentaje de caudal asociado a cada punto o fila de `Points`.

En el flujo de normalización de Nivus, `percent_q` ya debe estar alineado a `Points`. Es decir, el módulo de calidad no reconstruye `percent_q`: lo lee desde los datos normalizados.

En el diseño actual de normalización, `percent_q` proviene de la combinación de información de `Sections` hacia `Points`, incluyendo la composición de bordes cuando corresponde. Por ejemplo, las contribuciones de borde pueden combinar primera + segunda sección y última + penúltima sección antes de quedar alineadas a `Points`.

### 3.3 Datos raw canonical

La raíz raw canonical se configura en:

```yaml
analysis:
  quality_metrics:
    input_dirs:
      raw_canonical_root: database/raw_canonical
```

Para Nivus, la tabla usada es:

```yaml
analysis:
  quality_metrics:
    instruments:
      nivus:
        tables:
          raw_points: nivus/Points
```

Por defecto, esto resuelve a:

```text
database/raw_canonical/nivus/Points/
```

Para cada archivo normalizado, el módulo busca un archivo raw con el mismo nombre dentro de `raw_points`.

### 3.4 Detección de tq[%]

La columna `tq` se detecta dinámicamente en el archivo raw canonical de `Points`.

El código acepta variantes normalizadas de:

```text
tq [%]
tq(%)
tq
```

El módulo distingue explícitamente `tq` de otras columnas como:

```text
atq[%]
hq[%]
```

Solo se usa `tq`. Si no se encuentra una columna compatible, el archivo queda registrado con error en el log.

## 4. Definición del cálculo de CG(%)

Para cada fila `i`:

- `percent_q_i` es el porcentaje de caudal leído desde la columna configurada, normalmente `percent_q`;
- `tq_i` es el valor de calidad `tq` leído desde el raw canonical de Nivus.

El código implementa:

```text
CG(%) = 100 * Σ((percent_q_i / 100) * tq_i) / Σ(percent_q_i)
```

El cálculo se realiza después de convertir ambas series a valores numéricos y descartar pares con valores faltantes.

Detalles importantes:

- `percent_q_i` se toma en valor absoluto.
- `tq_i` proviene del instrumento en el archivo raw canonical.
- Ambas series deben estar alineadas por fila entre `normalized Points` y `raw Points`.
- Si no hay datos válidos, el archivo queda registrado como error.
- Si la suma de pesos es cero, el archivo queda registrado como error.

## 5. Lógica de procesamiento

El flujo implementado es:

1. Cargar configuración desde `analysis.quality_metrics`.
2. Resolver rutas de `normalized_root`, `raw_canonical_root` y `output_root`.
3. Iterar archivos CSV dentro de `database/normalized/nivus/Points/`.
4. Parsear metadatos desde el nombre del archivo.
5. Aplicar filtros de puntos y meses, si fueron definidos.
6. Buscar el archivo raw correspondiente con el mismo nombre en `database/raw_canonical/nivus/Points/`.
7. Leer `Points` normalizado y raw.
8. Verificar existencia de `percent_q` en normalizado.
9. Detectar columna `tq` en raw.
10. Verificar que ambos archivos tengan la misma cantidad de filas.
11. Calcular `CG(%)`.
12. Registrar resultado en `cg_measurements.csv`.
13. Registrar estado del archivo en `cg_log.csv`.
14. Generar `CG.xlsx`.

El patrón de nombre esperado para archivos `Points` es:

```text
P{point}_Points_{YYYYMMDD}_{HHMMSS}.csv
```

La parte horaria es opcional en el código. Si falta, se usa `000000`.

## 6. Agregación temporal

La opción `--aggregation` acepta:

```text
measurement
daily
monthly
```

El campo `period` se construye así:

| aggregation | period |
| --- | --- |
| `measurement` | `YYYYMMDD_HHMMSS` |
| `daily` | `YYYYMMDD` |
| `monthly` | `YYYYMM` |

El Excel usa `period` como columnas de la hoja `CG`.

## 7. Outputs

### 7.1 Directorio de salida

Cada ejecución genera una carpeta con timestamp dentro de:

```text
runs/analysis_quality_metrics/
```

Ejemplo:

```text
runs/analysis_quality_metrics/20260503_145530/
```

### 7.2 Archivos generados

El módulo genera:

```text
cg_measurements.csv
cg_log.csv
CG.xlsx
```

### 7.3 cg_measurements.csv

Contiene un registro por medición procesada correctamente.

Columnas principales:

```text
point
date
time
period
cg
file
```

### 7.4 cg_log.csv

Contiene el estado de cada archivo evaluado.

Puede incluir:

```text
file
status
reason
point
date
time
tq_column
weight_column
error
```

Estados posibles según el flujo:

- `ok`;
- `skipped`;
- `missing_raw`;
- `error`.

### 7.5 CG.xlsx

El Excel incluye estas hojas:

#### CG

Tabla pivote de resultados.

- Filas: puntos (`P1`, `P2`, etc.).
- Columnas: `period`.
- Valores: promedio de `CG(%)` para ese punto y período.

#### Log

Detalle del procesamiento de archivos:

- estado por archivo;
- errores;
- columna `tq` detectada;
- columna de peso usada.

#### Measurements

Detalle de mediciones procesadas correctamente.

#### Charts

Contiene un gráfico por punto.

- Eje X: fecha o mes, según agregación.
- Eje Y: `CG(%)`.

## 8. CLI

### 8.1 Modo básico

```bash
aforix analyze quality run -c configs/examples/main.yaml
```

Por defecto usa:

```text
aggregation = daily
```

### 8.2 Modo interactivo

```bash
aforix analyze quality run -c configs/examples/main.yaml --interactive
```

El modo interactivo muestra puntos y meses disponibles, y pregunta:

- puntos a incluir;
- meses `YYYYMM` a incluir;
- tipo de agregación.

Si no se seleccionan meses, se usan todos los meses disponibles.

### 8.3 Filtro por puntos

```bash
aforix analyze quality run -c configs/examples/main.yaml --points 1,2,21
```

Los puntos pueden escribirse con o sin prefijo `P`.

### 8.4 Filtro por meses

```bash
aforix analyze quality run -c configs/examples/main.yaml --yyyymm 202412,202501
```

El formato esperado es `YYYYMM`.

### 8.5 Todos los meses

```bash
aforix analyze quality run -c configs/examples/main.yaml --all-months
```

### 8.6 Agregación por medición

```bash
aforix analyze quality run -c configs/examples/main.yaml --aggregation measurement
```

### 8.7 Agregación diaria

```bash
aforix analyze quality run -c configs/examples/main.yaml --aggregation daily
```

### 8.8 Agregación mensual

```bash
aforix analyze quality run -c configs/examples/main.yaml --aggregation monthly
```

### 8.9 Ejemplo Windows multilinea

```bat
aforix analyze quality run ^
  -c configs/examples/main.yaml ^
  --points 1,2,21 ^
  --yyyymm 202412,202501 ^
  --aggregation monthly
```

## 9. Configuración YAML

La configuración principal está bajo:

```yaml
analysis:
  quality_metrics:
    enabled: true
    input_dirs:
      normalized_root: database/normalized
      raw_canonical_root: database/raw_canonical
    output_root: runs/analysis_quality_metrics

    instruments:
      nivus:
        enabled: true
        tables:
          normalized_points: nivus/Points
          raw_points: nivus/Points
        columns:
          weight_column: percent_q
```

### 9.1 input_dirs

Define las raíces de entrada:

| Campo | Descripción |
| --- | --- |
| `normalized_root` | raíz de datos normalizados |
| `raw_canonical_root` | raíz de datos raw canonical |

### 9.2 output_root

Define dónde se guardan las ejecuciones:

```yaml
output_root: runs/analysis_quality_metrics
```

### 9.3 instruments.nivus

Define tablas y columnas usadas para Nivus.

| Campo | Descripción |
| --- | --- |
| `tables.normalized_points` | ruta relativa a `normalized_root` |
| `tables.raw_points` | ruta relativa a `raw_canonical_root` |
| `columns.weight_column` | columna de pesos, normalmente `percent_q` |

## 10. Diseño y extensibilidad

El diseño separa:

- configuración (`config.py`);
- cálculo de métricas (`metrics.py`);
- ejecución y generación de outputs (`runner.py`);
- CLI (`cli.py`).

Actualmente el procesamiento efectivo está centrado en Nivus. Para extender a otro instrumento, el diseño debería incorporar una rama específica de lectura y cálculo para ese instrumento, manteniendo:

- rutas definidas por configuración;
- columnas definidas por configuración;
- outputs reproducibles;
- logs de auditoría.

Ejemplos de extensiones futuras:

- FlowTracker: cálculo de métricas de calidad basado en columnas propias del instrumento.
- Molinete: cálculo de métricas derivadas de planillas y controles manuales.

## 11. Consideraciones importantes

### 11.1 Alineación entre normalized y raw

El cálculo exige que el archivo `Points` normalizado y el raw correspondiente tengan la misma cantidad de filas.

Si las longitudes difieren, el archivo queda registrado como error.

### 11.2 Dependencia de la normalización

El módulo presupone que `percent_q` ya está correctamente calculado y alineado en `normalized/nivus/Points`.

### 11.3 Sensibilidad a nombres de columnas

La columna de peso se toma de configuración. Si `percent_q` no existe, el archivo falla.

La columna `tq` se detecta dinámicamente, pero solo se aceptan variantes de `tq`, no `atq` ni `hq`.

### 11.4 Validación previa

Se recomienda ejecutar validación antes del análisis:

```bash
aforix validate run -c configs/examples/main.yaml
```

## 12. Buenas prácticas

- Ejecutar el pipeline completo hasta `database/normalized` antes del análisis.
- Ejecutar `validate` antes de calcular métricas de calidad.
- Revisar `cg_log.csv` después de cada corrida.
- Revisar la hoja `Log` del Excel.
- Confirmar que los puntos y meses esperados estén presentes.
- Usar primero `--aggregation measurement` para depurar, y luego `daily` o `monthly` para reportes.

## 13. Troubleshooting

### No se genera CG.xlsx

Revisar si existen archivos en:

```text
database/normalized/nivus/Points/
database/raw_canonical/nivus/Points/
```

### Muchos archivos aparecen como missing_raw

Verificar que los archivos raw tengan exactamente el mismo nombre que los archivos normalizados.

### Error por longitud distinta

El módulo exige la misma cantidad de filas en `Points` normalizado y raw. Revisar si la normalización filtró o reordenó filas.

### Falta percent_q

Revisar la normalización de Nivus y la configuración:

```yaml
weight_column: percent_q
```

### No se encuentra tq

Revisar que el raw canonical incluya una columna compatible con:

```text
tq [%]
tq(%)
tq
```

`atq` y `hq` no se usan para el cálculo.

### No aparecen puntos esperados

Revisar el patrón de nombres:

```text
P{point}_Points_{YYYYMMDD}_{HHMMSS}.csv
```

### No aparecen meses esperados

Revisar que los nombres de archivo contengan fechas válidas y que el filtro `--yyyymm` use formato `YYYYMM`.
