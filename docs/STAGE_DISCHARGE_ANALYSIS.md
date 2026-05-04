# Guía de análisis caudal–altura

Esta guía documenta el módulo `stage-discharge` de Aforix, usado para analizar la relación entre caudal medido y altura, nivel o profundidad del cauce.

El módulo se ejecuta desde la CLI con:

```bash
aforix analyze stage-discharge run -c configs/examples/main.yaml
```

También tiene un modo interactivo:

```bash
aforix analyze stage-discharge interactive -c configs/examples/main.yaml
```

## 1. Descripción general

El análisis caudal–altura permite construir y evaluar relaciones entre:

- `Q`: caudal medido, expresado en L/s;
- `H`: altura, nivel o profundidad del cauce, expresada en m.

El objetivo es comparar distintas fuentes de altura y ajustar curvas simples de tipo caudal–altura para cada punto e instrumento.

Dentro del pipeline de Aforix, este módulo se ubica después de la normalización y de la preparación de fuentes externas:

```text
raw -> ingest -> runs -> build-groups -> database/raw_canonical -> normalize -> database/normalized -> external sources -> analysis
```

El módulo usa:

- caudales y profundidades instrumentales desde `database/normalized`;
- alturas manuales desde `database/external/normalized/manual_stage`;
- configuración desde `analysis.stage_discharge` en `configs/examples/main.yaml`.

Cada ejecución genera una carpeta en:

```text
runs/analysis_stage_discharge/<timestamp>/
```

con CSVs, métricas, modelos ajustados, Excel y gráficos.

## 2. Fuentes de datos

### 2.1 Caudales normalizados

Los caudales se leen desde la base normalizada definida por:

```yaml
analysis:
  stage_discharge:
    input_dirs:
      normalized_root: database/normalized
```

El módulo intenta leer primero:

```text
database/normalized/Summary.csv
```

Si existe, usa esa tabla global. Si no existe, puede leer las tablas configuradas por instrumento, por ejemplo:

```yaml
instruments:
  nivus:
    summary_table: nivus/Summary
  flowtracker:
    summary_table: flowtracker/Summary
  molinete:
    summary_table: molinete/Summary
```

Las columnas principales esperadas son:

```text
station_id
measurement_date
measurement_time
instrument
q_total_ls
q_total_m3s
depth_mean_m
```

### 2.2 Alturas instrumentales

Las alturas o profundidades instrumentales pueden provenir de:

- `depth_mean_m`, desde `Summary`;
- `depth_max_m`, si existe en `Summary`;
- `depth_m` en `Points.csv`, usado para calcular una profundidad máxima por medición.

El cálculo de máxima desde `Points.csv` agrupa por:

```text
station_id
measurement_date
measurement_time
instrument
```

y toma el máximo de `depth_m`. Ese valor se incorpora como `instrument_stage_max_m`.

Cuando se solicita altura máxima instrumental, el módulo busca primero una columna compatible con:

```text
max_depth_m
instrument_stage_max_m
```

### 2.3 Alturas manuales

Las alturas manuales se leen desde:

```text
database/external/normalized/manual_stage/manual_stage.csv
```

Esta ruta se configura en:

```yaml
external_sources:
  manual_stage:
    enabled: true
    raw_dir: data/external/manual_stage
    normalized_dir: database/external/normalized/manual_stage
```

y en:

```yaml
analysis:
  stage_discharge:
    input_dirs:
      manual_stage_root: database/external/normalized/manual_stage
```

El archivo normalizado esperado es:

```text
manual_stage.csv
```

con columnas compatibles con:

```text
station_id
measurement_date
manual_stage_m
```

El módulo normaliza `station_id` y parsea `measurement_date`.

### 2.4 Fuente externa manual_stage

Las alturas manuales se gestionan como una fuente externa. Esto permite mantener separada la información medida en campo de los datos normalizados de instrumentos.

Si existe un comando de conversión externo para `manual_stage`, debe ejecutarse antes del análisis. Según el estado actual documentado en `main.yaml`, la fuente queda ubicada en:

```text
data/external/manual_stage                  -> raw manual stage
database/external/normalized/manual_stage   -> manual stage normalizado
```

## 3. Tipos de altura

El análisis puede usar alturas manuales, alturas instrumentales o ambas.

### 3.1 manual

Usa la columna:

```text
manual_stage_m
```

proveniente de `manual_stage.csv`.

En los pares analíticos queda como:

```text
stage_origin = manual
stage_type = manual
stage_source = manual_stage_m
```

### 3.2 instrument mean

Usa la profundidad media del instrumento:

```text
depth_mean_m
```

En los pares analíticos queda como:

```text
stage_origin = instrument
stage_type = mean
stage_source = depth_mean_m
```

### 3.3 instrument max

Usa la profundidad máxima instrumental. Puede provenir de:

```text
max_depth_m
instrument_stage_max_m
```

En los pares analíticos queda como:

```text
stage_origin = instrument
stage_type = max
```

### 3.4 depth_mode

Controla qué origen de altura se usa:

| Valor | Significado |
| --- | --- |
| `manual` | usa solo alturas manuales |
| `instrument` | usa solo alturas instrumentales |
| `both` | usa manuales e instrumentales |

También se aceptan algunos alias en español, como `ambas` para `both` e `instrumento` para `instrument`.

### 3.5 instrument_stage_mode

Controla qué tipo de altura instrumental se usa:

| Valor | Significado |
| --- | --- |
| `mean` | usa `depth_mean_m` |
| `max` | usa máxima instrumental |
| `both` | usa ambas |

También se aceptan alias como `media`, `maxima`, `máxima` y `ambas`.

## 4. Instrumentos y ranking

El análisis no está hardcodeado a un único instrumento. Los instrumentos se configuran en YAML.

Instrumentos actuales:

| Código | Nombre interno |
| --- | --- |
| `NV` | `nivus` |
| `FT` | `flowtracker` |
| `ML` | `molinete` |
| `M9` | `m9`, previsto para una etapa posterior |

En `configs/examples/main.yaml`, el módulo incluye configuración para:

```yaml
instruments:
  nivus:
    code: NV
  flowtracker:
    code: FT
  molinete:
    code: ML
```

### 4.1 Análisis por instrumento real

Cada fila conserva su instrumento original mediante la columna:

```text
instrument
```

El módulo genera grupos analíticos por instrumento real:

```text
analysis_group = nivus
analysis_group = flowtracker
analysis_group = molinete
```

### 4.2 Serie BEST

Además de los grupos por instrumento real, el módulo genera una serie consolidada:

```text
analysis_group = BEST
```

`BEST` se construye aplicando el ranking configurado por punto y fecha.

Ejemplo:

```yaml
instrument_selection:
  ranking:
    - nivus
    - flowtracker
    - molinete
```

Esto significa que, si hay más de una medición para el mismo `station_id` y `measurement_date`, se conserva la primera disponible según ese ranking.

### 4.3 Diferencia entre instrumento real y BEST

- Los grupos por instrumento real permiten evaluar cada instrumento individualmente.
- `BEST` permite trabajar con una serie consolidada por punto y fecha.

Esto ayuda a comparar curvas por instrumento y una curva final seleccionada por prioridad.

## 5. Configuración YAML

La sección principal es:

```yaml
analysis:
  stage_discharge:
    enabled: true

    input_dirs:
      normalized_root: database/normalized
      manual_stage_root: database/external/normalized/manual_stage

    output:
      run_output_root: runs/analysis_stage_discharge
      stable_output_dir: database/analysis/stage_discharge
      write_stable_copy: true

    selection:
      points: all
      instruments: all
      start_date: null
      end_date: null
      depth_mode: both
      instrument_stage_mode: both
      include_best_ranked: true

    instrument_selection:
      ranking:
        - nivus
        - flowtracker
        - molinete

    plotting:
      enabled: true
      max_plots: 40

    excel:
      enabled: true
```

### 5.1 input_dirs.normalized_root

Raíz de datos normalizados:

```yaml
normalized_root: database/normalized
```

### 5.2 input_dirs.manual_stage_root

Raíz de alturas manuales normalizadas:

```yaml
manual_stage_root: database/external/normalized/manual_stage
```

### 5.3 output.run_output_root

Carpeta raíz de corridas:

```yaml
run_output_root: runs/analysis_stage_discharge
```

Cada corrida crea un subdirectorio con timestamp.

### 5.4 instruments.<instrument>.enabled

Activa o desactiva instrumentos:

```yaml
instruments:
  nivus:
    enabled: true
  flowtracker:
    enabled: true
  molinete:
    enabled: true
```

### 5.5 instrument_selection.ranking

Define la prioridad para construir `BEST`:

```yaml
instrument_selection:
  ranking:
    - nivus
    - flowtracker
    - molinete
```

### 5.6 selection.points

Permite filtrar puntos:

```yaml
selection:
  points: all
```

También puede usarse una lista:

```yaml
selection:
  points:
    - P1
    - P8
    - P13
```

### 5.7 selection.start_date y selection.end_date

Permiten filtrar por rango de fechas:

```yaml
selection:
  start_date: 2025-01-01
  end_date: 2025-03-31
```

El filtro es inclusivo.

### 5.8 selection.depth_mode

Valores válidos:

```text
manual
instrument
both
```

### 5.9 selection.instrument_stage_mode

Valores válidos:

```text
mean
max
both
```

### 5.10 plotting.enabled y plotting.max_plots

Controlan generación de gráficos:

```yaml
plotting:
  enabled: true
  max_plots: 40
```

### 5.11 excel.enabled

Controla generación del reporte Excel:

```yaml
excel:
  enabled: true
```

## 6. Modo interactivo

Comando:

```bash
aforix analyze stage-discharge interactive -c configs/examples/main.yaml
```

El modo interactivo usa `main.yaml` como base. Al presionar Enter se mantienen los defaults.

Preguntas principales:

- instrumentos a usar, con códigos `NV`, `FT`, `ML`, `M9`;
- ranking de instrumentos;
- puntos a analizar;
- fecha inicial;
- fecha final;
- `depth_mode`;
- `instrument_stage_mode`;
- si se generan plots;
- cantidad máxima de plots;
- si se genera Excel.

Ejemplo de sesión:

```text
Stage-discharge interactive analysis
Using main YAML as defaults. Press Enter to keep defaults.

Instruments available: NV, FT, ML
Instruments to use [NV, FT, ML]: NV, FT, ML
Instrument ranking [NV, FT, ML]: NV, FT, ML
Points to analyze (all or comma-separated list) [all]: P1,P8,P13
Start date (YYYY-MM-DD or empty): 2025-01-01
End date (YYYY-MM-DD or empty): 2025-03-31
Depth mode [manual/instrument/both] [both]: both
Instrument stage mode [mean/max/both] [both]: mean
Generate plots? [y/N]: y
Maximum number of plots [40]: 10
Generate Excel report? [Y/n]: y
```

## 7. Modo avanzado por CLI

Comando base:

```bash
aforix analyze stage-discharge run -c configs/examples/main.yaml
```

Los flags CLI sobrescriben los defaults del YAML.

### 7.1 Flags disponibles

| Flag | Descripción |
| --- | --- |
| `--points` | puntos separados por coma, o `all` |
| `--start-date` | fecha inicial inclusiva, `YYYY-MM-DD` |
| `--end-date` | fecha final inclusiva, `YYYY-MM-DD` |
| `--instruments` | instrumentos separados por coma |
| `--ranking` | ranking separado por coma |
| `--depth-mode` | `manual`, `instrument` o `both` |
| `--instrument-stage-mode` | `mean`, `max` o `both` |
| `--plots / --no-plots` | activa o desactiva plots |
| `--excel / --no-excel` | activa o desactiva Excel |
| `--max-plots` | número máximo de plots |

### 7.2 Ejemplo Windows CMD

```bat
aforix analyze stage-discharge run -c configs/examples/main.yaml --points P1,P8,P13 --start-date 2025-01-01 --end-date 2025-03-31 --instruments NV,FT,ML --ranking NV,FT,ML --depth-mode both --instrument-stage-mode mean --no-plots --excel
```

### 7.3 Ejemplo Windows multilinea

```bat
aforix analyze stage-discharge run ^
  -c configs/examples/main.yaml ^
  --points P1,P8,P13 ^
  --start-date 2025-01-01 ^
  --end-date 2025-03-31 ^
  --instruments NV,FT,ML ^
  --ranking NV,FT,ML ^
  --depth-mode both ^
  --instrument-stage-mode mean ^
  --no-plots ^
  --excel
```

### 7.4 Listas en CMD

Correcto:

```bat
--instruments NV,FT,ML
```

Correcto:

```bat
--instruments "NV, FT, ML"
```

Incorrecto:

```bat
--instruments NV, FT, ML
```

Sin comillas, los espacios separan argumentos y pueden romper el parseo.

## 8. Matching y filtros

### 8.1 Matching manual–instrumento

El matching entre aforos y alturas manuales se realiza por:

```text
station_id
measurement_date
```

La fecha se normaliza a formato `YYYY-MM-DD`.

Actualmente no hay tolerancia temporal implementada. Si la altura manual está en una fecha distinta, no se vincula.

### 8.2 Filtro por puntos

Los puntos se normalizan internamente. Ejemplos equivalentes:

```text
P1
p01
1
```

se convierten a:

```text
P1
```

El filtro se aplica antes de construir pares analíticos, ajustar modelos, generar plots y generar Excel.

### 8.3 Filtro por fechas

El filtro por fechas se aplica sobre `measurement_date`.

Ejemplo:

```bash
aforix analyze stage-discharge run -c configs/examples/main.yaml --start-date 2025-01-01 --end-date 2025-03-31
```

## 9. Modelos de regresión

Variables:

```text
Q = caudal [L/s]
H = altura/profundidad/nivel [m]
```

Modelos implementados actualmente:

| Modelo | Ecuación |
| --- | --- |
| `poly1` | `Q = a·H + b` |
| `poly2` | `Q = a·H² + b·H + c` |
| `power` | `Q = a·H^b` |

Los coeficientes se guardan en:

```text
stage_discharge_fits.csv
```

y en la hoja `Fits` del Excel.

La hoja `Fits` incluye una guía genérica de ecuaciones y coeficientes `a`, `b`, `c`.

### 9.1 Criterios mínimos

El mínimo general es:

```text
3 puntos válidos
```

Además:

- `poly2` requiere al menos 3 puntos;
- `power` requiere valores positivos de `H` y `Q`, y al menos 3 puntos positivos.

### 9.2 Nota sobre power_log

`power_log` aparece listado en `interactive_defaults.models` del YAML, pero según el estado actual de `fitting.py` el ajuste efectivo procesa `poly1`, `poly2` y `power`.

## 10. Métricas

Las métricas se calculan comparando `Q` observado contra `Q` predicho.

| Columna en Excel | Columna base | Unidad | Interpretación |
| --- | --- | --- | --- |
| `r2_dimensionless` | `r2` | adimensional | mayor es mejor; cercano a 1 indica mejor ajuste |
| `rmse_ls` | `rmse` | L/s | menor es mejor |
| `mae_ls` | `mae` | L/s | menor es mejor |
| `nrmse_ratio` | `nrmse` | adimensional | RMSE dividido por caudal medio |
| `bias_ls` | `bias` | L/s | sesgo medio; cercano a 0 es mejor |
| `pbias_pct` | `pbias_pct` | % | sesgo porcentual; cercano a 0 es mejor |
| `nse_dimensionless` | `nse` | adimensional | actualmente coincide con `r2` en la implementación |

El mejor modelo se selecciona por grupo usando `r2` como criterio por defecto.

La salida se guarda en:

```text
stage_discharge_best_models.csv
```

y en la hoja `BestModels` del Excel.

## 11. Outputs por corrida

Cada corrida genera:

```text
runs/analysis_stage_discharge/<timestamp>/
```

Archivos principales:

| Archivo | Contenido |
| --- | --- |
| `stage_discharge_analysis_pairs.csv` | pares finales `Q-H` usados para fitting |
| `stage_discharge_matched_pairs.csv` | pares medidos con altura manual cuando existe |
| `stage_discharge_matched_pairs_diagnostic.csv` | salida diagnóstica completa del matching |
| `stage_discharge_fits.csv` | coeficientes por modelo y grupo |
| `stage_discharge_metrics.csv` | métricas por modelo y grupo |
| `stage_discharge_best_models.csv` | mejor modelo por grupo |
| `stage_discharge_log.csv` | métricas de control de filas y grupos |
| `stage_discharge_report.xlsx` | reporte Excel |
| `plots/` | gráficos generados |
| `plots/plot_log.csv` | log de generación de gráficos |

### 11.1 Excel

El Excel contiene:

- `README`;
- `AnalysisPairs`;
- `Fits`;
- `Metrics`;
- `BestModels`;
- hojas por punto y grupo, por ejemplo `P1_BEST`, `P1_nivus`, `P8_flowtracker`.

Las hojas por punto/grupo incluyen columnas:

```text
stage_manual_m
stage_mean_m
stage_max_m
```

Si una fuente de altura no está disponible, la columna queda vacía.

En el reporte Excel se eliminan columnas de baja utilidad como:

```text
station_name
original_source_file
source_run_dir
```

Las columnas de trazabilidad:

```text
normalized_source_table
run_id
```

se mantienen y se mueven al final.

## 12. Interpretación práctica

### 12.1 Manual vs mean vs max

- `manual`: representa mediciones externas tomadas en campo.
- `mean`: representa profundidad media del instrumento.
- `max`: representa profundidad máxima instrumental.

Comparar estas fuentes permite evaluar cuál explica mejor el caudal medido.

### 12.2 Comparación entre instrumentos

Las hojas y grupos por instrumento permiten comparar curvas separadas para Nivus, FlowTracker y Molinete.

### 12.3 BEST

`BEST` combina instrumentos según el ranking configurado. Es útil cuando se quiere una única serie por punto y fecha.

### 12.4 R² alto o bajo

Un `r2_dimensionless` alto sugiere que la curva ajustada explica bien la variabilidad del caudal en los datos disponibles.

Un valor bajo puede indicar:

- pocos puntos;
- mediciones con mucho ruido;
- relación caudal–altura débil;
- problemas de matching;
- mezcla de condiciones hidráulicas distintas.

### 12.5 Pocos puntos

Con pocos puntos, una curva puede parecer buena pero no ser robusta. Revisar siempre `n_points` en `Fits` y `Metrics`.

## 13. Troubleshooting

### No aparecen puntos esperados

Revisar:

- `selection.points`;
- `--points`;
- existencia del punto en `Summary.csv`;
- normalización de IDs (`P1`, `p01`, `1`).

### El rango de fechas deja el dataset vacío

Revisar `measurement_date` en los datos normalizados y el formato `YYYY-MM-DD` usado en CLI.

### El Excel tiene pocas hojas

Puede ocurrir si:

- hay pocos pares analíticos válidos;
- `depth_mode` excluyó fuentes disponibles;
- no hay suficientes puntos para ajustar modelos;
- los filtros redujeron demasiado el dataset.

### No se generan plots

Revisar:

```yaml
plotting:
  enabled: true
```

También revisar `--no-plots` y `--max-plots`.

### Error por listas con espacios en CMD

Usar listas sin espacios:

```bat
--instruments NV,FT,ML
```

O con comillas:

```bat
--instruments "NV, FT, ML"
```

### No hay suficientes puntos para ajustar modelos

El fitting requiere al menos 3 puntos válidos. Revisar `stage_discharge_analysis_pairs.csv`.

### Diferencias entre modo interactivo y CLI avanzado

El modo interactivo parte de los defaults del YAML. El CLI avanzado sobrescribe directamente valores específicos.

## 14. Ejemplos completos

### 14.1 Ejemplo interactivo

```bat
aforix analyze stage-discharge interactive -c configs/examples/main.yaml
```

### 14.2 Ejemplo avanzado con puntos y fechas

```bat
aforix analyze stage-discharge run ^
  -c configs/examples/main.yaml ^
  --points P1,P8,P13 ^
  --start-date 2025-01-01 ^
  --end-date 2025-03-31 ^
  --instruments NV,FT,ML ^
  --ranking NV,FT,ML ^
  --depth-mode both ^
  --instrument-stage-mode mean ^
  --excel
```

### 14.3 Solo alturas manuales

```bat
aforix analyze stage-discharge run -c configs/examples/main.yaml --depth-mode manual
```

### 14.4 Solo instrumentos con altura máxima

```bat
aforix analyze stage-discharge run -c configs/examples/main.yaml --depth-mode instrument --instrument-stage-mode max
```

### 14.5 Sin plots

```bat
aforix analyze stage-discharge run -c configs/examples/main.yaml --no-plots --excel
```

### 14.6 Pocos gráficos

```bat
aforix analyze stage-discharge run -c configs/examples/main.yaml --max-plots 10
```

## 15. Cierre y trabajo futuro

Este módulo reemplaza en Aforix la funcionalidad equivalente de qSL para análisis caudal–altura.

Trabajo futuro posible:

- implementar `date_tolerance_days` para matching temporal flexible;
- definir ranking hidráulico más avanzado;
- consolidar export de curvas finales si se requiere un formato separado;
- integrar salidas de caudal–altura en reportes generales de Aforix;
- completar integración futura de M9.
