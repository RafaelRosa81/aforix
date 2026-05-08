# Guía de análisis de perfiles de sección

Esta guía documenta el análisis `section-profiles` de Aforix.

El módulo permite generar perfiles de sección por medición a partir de datos normalizados de `Points`. El resultado principal es un Excel con una hoja por medición, incluyendo una tabla de datos, un resumen y un gráfico nativo editable de Excel.

El comando base es:

```bash
aforix analyze section-profiles run -c configs/examples/main.yaml
```

## 1. Objetivo del análisis

`section-profiles` sirve para visualizar y revisar perfiles transversales de mediciones de aforo.

Permite comparar variables de `Points`, por ejemplo:

- profundidad respecto a distancia;
- velocidad respecto a distancia;
- caudal parcial respecto a punto de medición;
- porcentaje de caudal respecto a distancia.

El análisis trabaja sobre datos ya normalizados. No procesa archivos raw de instrumentos.

Dentro del pipeline general de Aforix se ubica en la etapa de análisis:

```text
raw -> ingest -> runs -> build-groups -> database/raw_canonical -> normalize -> database/normalized -> validate/export/analysis
```

## 2. Fuentes de datos

### 2.1 No usa el consolidado Points.csv

Este módulo no usa directamente:

```text
database/normalized/Points.csv
```

En cambio, lee los archivos `Points` por instrumento.

### 2.2 Lee Points por instrumento

La raíz de datos normalizados se configura en:

```yaml
analysis:
  section_profiles:
    input_dirs:
      normalized_root: database/normalized
```

Cada instrumento define su propia carpeta de `Points`:

```yaml
analysis:
  section_profiles:
    instruments:
      nivus:
        points_table: nivus/Points
      flowtracker:
        points_table: flowtracker/Points
      molinete:
        points_table: molinete/Points
```

Por lo tanto, las rutas esperadas son:

```text
database/normalized/nivus/Points/*.csv
database/normalized/flowtracker/Points/*.csv
database/normalized/molinete/Points/*.csv
```

### 2.3 Instrumentos actuales

El bloque actual de configuración incluye:

| Instrumento interno | Código | Carpeta Points |
| --- | --- | --- |
| `nivus` | `NV` | `nivus/Points` |
| `flowtracker` | `FT` | `flowtracker/Points` |
| `molinete` | `ML` | `molinete/Points` |

## 3. Configuración en main.yaml

La configuración principal está en:

```yaml
analysis:
  section_profiles:
    enabled: true

    input_dirs:
      normalized_root: database/normalized

    output:
      run_output_root: runs/analysis_section_profiles
      stable_output_dir: database/analysis/section_profiles
      write_stable_copy: false

    selection:
      points: all
      instruments: all
      start_date: null
      end_date: null

    defaults:
      x_axis: distance_m
      y_axis: depth_m
      chart_type: scatter

    allowed:
      x_columns:
        - distance_m
        - point_index
        - station_id
      y_columns:
        - depth_m
        - velocity_mean_m_s
        - area_m2
        - q_m3s
        - q_ls
        - percent_q
        - temperature_c
      chart_types:
        - scatter
        - bar

    instruments:
      nivus:
        enabled: true
        code: NV
        points_table: nivus/Points
      flowtracker:
        enabled: true
        code: FT
        points_table: flowtracker/Points
      molinete:
        enabled: true
        code: ML
        points_table: molinete/Points

    excel:
      enabled: true
      include_summary: true
      include_chart: true
      chart_anchor: H2
      sheet_name_template: "{station_id}_{measurement_date}_{instrument_code}"
      output_name_template: "section_profile_{y_axis}_by_{x_axis}_{instrument_tag}_{points_tag}_{date_range}.xlsx"
```

### 3.1 input_dirs.normalized_root

Define la raíz de datos normalizados:

```yaml
normalized_root: database/normalized
```

### 3.2 output.run_output_root

Define dónde se guardan las corridas:

```yaml
run_output_root: runs/analysis_section_profiles
```

Cada ejecución crea una subcarpeta con timestamp.

### 3.3 selection

Define filtros por defecto:

```yaml
selection:
  points: all
  instruments: all
  start_date: null
  end_date: null
```

Los filtros también pueden sobrescribirse por CLI.

### 3.4 defaults

Define ejes y tipo de gráfico por defecto:

```yaml
defaults:
  x_axis: distance_m
  y_axis: depth_m
  chart_type: scatter
```

### 3.5 allowed

Define listas sugeridas de columnas y tipos de gráfico.

El modo interactivo usa estas listas y las cruza con las columnas realmente disponibles en los datos seleccionados.

### 3.6 instruments

Cada instrumento define:

- `enabled`: si se incluye en la carga;
- `code`: código visible para usuario;
- `points_table`: ruta relativa a `normalized_root`.

### 3.7 excel

Controla el reporte Excel:

| Campo | Uso |
| --- | --- |
| `include_readme` | si está presente, controla hoja `README`; por defecto se incluye |
| `include_index` | si está presente, controla hoja `Index`; por defecto se incluye |
| `chart_anchor` | celda donde se inserta el gráfico |
| `sheet_name_template` | plantilla para hojas de medición |
| `output_name_template` | plantilla del archivo de salida |

En el YAML actual aparecen `include_summary` e `include_chart`, pero el escritor Excel actual usa `include_readme` e `include_index` como controles explícitos de las hojas generales, y siempre genera gráficos para las hojas de medición si existen datos y columnas válidas.

## 4. Formas de ejecución

### 4.1 Ejecución simple

```bash
aforix analyze section-profiles run -c configs/examples/main.yaml
```

Windows CMD:

```bat
aforix analyze section-profiles run -c configs/examples/main.yaml
```

### 4.2 Ejecución avanzada con argumentos

```bash
aforix analyze section-profiles run -c configs/examples/main.yaml --instruments nivus,flowtracker --points P1,P5,P8 --start-date 2025-01-01 --end-date 2026-02-28 --x-axis distance_m --y-axis depth_m --chart-type scatter
```

Windows CMD multilínea:

```bat
aforix analyze section-profiles run ^
  -c configs/examples/main.yaml ^
  --instruments nivus,flowtracker ^
  --points P1,P5,P8 ^
  --start-date 2025-01-01 ^
  --end-date 2026-02-28 ^
  --x-axis distance_m ^
  --y-axis depth_m ^
  --chart-type scatter
```

### 4.3 Instrumentos por código o nombre

El modo interactivo acepta códigos como `NV`, `FT`, `ML` y los traduce a nombres internos.

En modo avanzado, `--instruments` se copia al filtro como lista. Para máxima compatibilidad con el código actual, se recomienda usar nombres internos:

```bat
--instruments nivus,flowtracker,molinete
```

Si se usan códigos en CLI avanzado:

```bat
--instruments NV,FT
```

verificar el resultado en el Excel, porque el filtrado final compara contra la columna interna `instrument`.

### 4.4 Ejecución interactiva

```bash
aforix analyze section-profiles run -c configs/examples/main.yaml --interactive
```

El modo interactivo muestra opciones detectadas dinámicamente desde los datos.

Preguntas principales:

```text
Available instruments: FT, ML, NV
Select instrument codes, comma-separated, empty = all:
Available points:
Select points, comma-separated, empty = all:
Available date range for selected data:
Start date YYYY-MM-DD, empty = no start filter:
End date YYYY-MM-DD, empty = no end filter:
Available X columns:
X axis:
Available Y columns:
Y axis:
Available chart types:
Chart type:
```

Ejemplo:

```text
Interactive section profiles mode
Available instruments: FT, ML, NV
Select instrument codes, comma-separated, empty = all: NV,FT
Available points: P1, P3, P5, P8, P11
Select points, comma-separated, empty = all: P1,P5,P8,P11
Available date range for selected data: 2025-01-01 to 2026-02-28
Start date YYYY-MM-DD, empty = no start filter: 2025-01-01
End date YYYY-MM-DD, empty = no end filter: 2026-02-28
Available X columns: distance_m, point_index, station_id
X axis [distance_m]: distance_m
Available Y columns: depth_m, velocity_mean_m_s, area_m2, q_m3s, q_ls, percent_q, temperature_c
Y axis [depth_m]: velocity_mean_m_s
Available chart types: scatter, bar
Chart type [scatter]: bar
```

## 5. Variables disponibles

### 5.1 Columnas típicas para X

```text
distance_m
point_index
station_id
```

### 5.2 Columnas típicas para Y

```text
depth_m
velocity_mean_m_s
area_m2
q_m3s
q_ls
percent_q
temperature_c
```

### 5.3 Columnas disponibles dinámicamente

Solo se pueden usar columnas presentes en los datos seleccionados.

Si una columna no existe después de aplicar filtros, el módulo falla con un mensaje como:

```text
Column 'percent_q' is not available. Available columns: [...]
```

El modo interactivo ayuda a evitar ese error porque muestra las columnas disponibles para la selección actual.

## 6. Salidas generadas

### 6.1 Carpeta de corrida

Cada ejecución genera una carpeta en:

```text
runs/analysis_section_profiles/<timestamp>/
```

### 6.2 Archivo Excel

El nombre del archivo se construye con la plantilla:

```text
section_profile_{y_axis}_by_{x_axis}_{instrument_tag}_{points_tag}_{date_range}.xlsx
```

Ejemplo:

```text
section_profile_depth_m_by_distance_m_nivus-flowtracker_P1-P5-P8_20250101_20260228.xlsx
```

### 6.3 Hojas del Excel

El Excel puede incluir:

- `README`;
- `Index`;
- una hoja por medición.

La hoja `README` resume:

- archivo de salida;
- fuente de datos;
- eje X;
- eje Y;
- tipo de gráfico;
- estructura del reporte.

La hoja `Index` resume cada medición incluida:

```text
sheet_name
station_id
measurement_date
measurement_time
instrument
instrument_code
n_rows
source_file
```

Cada hoja por medición incluye:

1. resumen de metadata;
2. tabla de datos `Points`;
3. gráfico nativo Excel.

### 6.4 Gráficos nativos Excel

Los gráficos se generan con `openpyxl`.

Tipos disponibles actualmente:

- `scatter`;
- `bar`.

Al estar dentro del Excel, los gráficos son editables por el usuario.

## 7. Robustez y trazabilidad

### 7.1 Metadata desde filename

El módulo puede inferir metadatos desde nombres como:

```text
P1_Points_20250121_085327.csv
```

Esto permite inferir:

```text
station_id = P1
measurement_date = 2025-01-21
measurement_time = 08:53:27
```

### 7.2 Corrección de fechas inválidas

Si la fecha del CSV es inválida, nula o aparece como `1970-01-01`, el módulo puede reemplazarla por la fecha inferida desde el nombre del archivo.

### 7.3 Evitar pérdida silenciosa de datos

El agrupamiento usa:

```python
groupby(..., dropna=False)
```

Esto evita perder mediciones cuando falta `measurement_time`.

### 7.4 Nombres únicos de hojas

Excel limita los nombres de hoja y no permite duplicados.

El módulo sanitiza nombres de hojas, limita su longitud y usa `unique_sheet_name()` para evitar colisiones.

### 7.5 Orden de datos

El módulo no fuerza ordenamiento por `distance_m`. El orden de los datos dentro de cada archivo se preserva.

## 8. Errores comunes y diagnóstico

### Columna no disponible

Ejemplo:

```text
Column 'percent_q' is not available. Available columns: [...]
```

Solución:

- revisar que la columna exista en los archivos seleccionados;
- usar modo interactivo para ver columnas disponibles;
- cambiar `--x-axis` o `--y-axis`.

### Sin datos después de filtros

Puede ocurrir por:

- puntos inexistentes;
- instrumentos mal escritos;
- fechas fuera del rango real;
- carpetas `Points` vacías.

### Instrumentos o puntos mal escritos

Los puntos se normalizan, por ejemplo:

```text
P1
p01
1
```

se tratan como `P1`.

Para instrumentos en modo avanzado, se recomienda usar nombres internos:

```text
nivus
flowtracker
molinete
```

### Fechas fuera de rango

El modo interactivo muestra el rango de fechas disponible para los datos seleccionados.

### Diferencia entre códigos y nombres internos

- Códigos: `NV`, `FT`, `ML`.
- Nombres internos: `nivus`, `flowtracker`, `molinete`.

El modo interactivo acepta códigos. En CLI avanzado, preferir nombres internos.

## 9. Buenas prácticas

- Usar modo interactivo para explorar datos y columnas disponibles.
- Usar modo avanzado para corridas reproducibles.
- Guardar el comando usado cuando se reporten resultados.
- Revisar la hoja `Index` para confirmar qué mediciones fueron incluidas.
- Verificar `n_rows` por medición.
- No editar manualmente archivos normalizados antes del análisis.
- Empezar con pocos puntos y luego ampliar la selección.

## 10. Relación con otros módulos

`section-profiles` es un análisis independiente dentro de:

```text
aforix analyze
```

Está integrado a Aforix, pero no depende de `stage-discharge`.

Puede complementar:

- revisión de perfiles transversales por campaña;
- comparación entre instrumentos;
- diagnóstico de datos antes de análisis caudal-altura;
- análisis futuros de curvas y consistencia hidráulica.
