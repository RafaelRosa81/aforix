# Guía de análisis de correlación

Esta guía explica cómo usar el módulo de correlaciones de Aforix para comparar series de caudal provenientes de aforos, modelo hidrológico y estaciones DINAGUA.

El módulo se ejecuta desde la CLI con:

```bash
aforix analyze correlation run -c configs/examples/main.yaml
```

## 1. Objetivo del módulo

El análisis de correlación permite comparar dos series de caudal, ajustar una regresión lineal y generar métricas, tablas, gráficos y un Excel de auditoría.

El resultado principal es una relación del tipo:

```text
Y = a * X + b
```

donde `X` e `Y` dependen del workflow y de la configuración `analysis.correlation.variable_roles`.

## 2. Workflows soportados

### 2.1 gauges_vs_model

Compara puntos de aforo contra puntos del modelo hidrológico.

Usa:

- aforos normalizados desde `database/normalized/`;
- datos externos del modelo desde `external_sources.model.normalized_dir`.

El cruce se realiza por fecha exacta entre la serie diaria de aforos y la serie del modelo.

### 2.2 gauges_vs_stations

Compara puntos de aforo contra estaciones DINAGUA.

Usa:

- aforos normalizados desde `database/normalized/`;
- estaciones DINAGUA normalizadas desde `external_sources.dinagua.normalized_dir`.

Permite cruce exacto por fecha o cruce por ventana temporal mediante `--match-mode window`.

### 2.3 model_vs_stations

Compara puntos del modelo hidrológico contra estaciones DINAGUA.

Usa:

- datos externos del modelo desde `external_sources.model.normalized_dir`;
- estaciones DINAGUA normalizadas desde `external_sources.dinagua.normalized_dir`.

Actualmente cruza por fecha exacta.

## 3. Datos de entrada

### 3.1 Aforos normalizados

Los aforos deben estar normalizados previamente en:

```text
database/normalized/
```

El módulo lee principalmente tablas `Summary` de los instrumentos definidos en `measuring_instruments`.

### 3.2 Datos externos del modelo

Los datos normalizados del modelo se leen desde:

```yaml
external_sources:
  model:
    normalized_dir: database/external/normalized/model
```

El lector espera archivos del tipo:

```text
P{point}_model_data.csv
{point}_model_data.csv
```

con columnas:

```text
date
q(m3/s)
```

El caudal se convierte internamente a `q_model_l/s` multiplicando por 1000.

### 3.3 Datos externos DINAGUA

Los datos normalizados de DINAGUA se leen desde:

```yaml
external_sources:
  dinagua:
    normalized_dir: database/external/normalized/dinagua
```

El lector espera archivos del tipo:

```text
{station_id}_{timestep}_station_data.csv
```

con columnas mínimas:

```text
date
q(m3/s)
```

Para series horarias, también debe existir:

```text
time
```

El caudal se convierte internamente a `q_station_l/s` multiplicando por 1000.

### 3.4 Conversión de datos externos

Los datos externos se generan con:

```bash
aforix external convert-model -c configs/examples/main.yaml
aforix external convert-dinagua -c configs/examples/main.yaml
```

En Windows:

```bat
aforix external convert-model -c configs/examples/main.yaml
aforix external convert-dinagua -c configs/examples/main.yaml
```

Las rutas raw y normalizadas se definen en `main.yaml`:

```yaml
external_sources:
  model:
    raw_dir: database/external/raw/model
    normalized_dir: database/external/normalized/model

  dinagua:
    raw_dir: database/external/raw/dinagua
    normalized_dir: database/external/normalized/dinagua
```

En los archivos raw de DINAGUA, la columna de caudal puede llamarse `q`, `caudal`, `flow`, `valor` o `gasto`. El conversor normaliza esa columna a `q(m3/s)`, que es la columna usada por el módulo de correlación.

## 4. Configuración en main.yaml

### 4.1 external_sources

Define las carpetas de entrada raw y salida normalizada para fuentes externas:

```yaml
external_sources:
  model:
    raw_dir: database/external/raw/model
    normalized_dir: database/external/normalized/model
  dinagua:
    raw_dir: database/external/raw/dinagua
    normalized_dir: database/external/normalized/dinagua
```

### 4.2 output_root

Define dónde se guardan los resultados de correlación:

```yaml
analysis:
  correlation:
    output_root: runs/analysis_correlation
```

### 4.3 default_ranking

Define el orden de prioridad de instrumentos cuando hay más de una medición para el mismo punto y día:

```yaml
analysis:
  correlation:
    default_ranking:
      - NV
      - FT
      - ML
```

### 4.4 variable_roles

Define qué serie se usa como X y cuál como Y en cada workflow:

```yaml
analysis:
  correlation:
    variable_roles:
      gauges_vs_model:
        x: model
        y: gauge
      gauges_vs_stations:
        x: station
        y: gauge
      model_vs_stations:
        x: station
        y: model
```

Esta configuración no es solo metadata: controla realmente qué columna se usa como X y qué columna se usa como Y en la regresión.

La ecuación reportada se interpreta como:

```text
Y = a * X + b
```

Por ejemplo:

```yaml
gauges_vs_model:
  x: model
  y: gauge
```

produce:

```text
gauge = a * model + b
```

Mientras que:

```yaml
gauges_vs_model:
  x: gauge
  y: model
```

produce:

```text
model = a * gauge + b
```

Según el estado actual del código, `variable_roles` debe estar definido en la configuración. Si falta `x` o `y`, el workflow falla con un error claro.

### 4.5 measuring_instruments

Define los instrumentos de medición disponibles para construir series de aforos:

```yaml
measuring_instruments:
  - code: NV
    name: Nivus
    subdir: nivus
    summary_format: matrix
    flow_unit: l/s

  - code: FT
    name: FlowTracker
    subdir: flowtracker
    summary_format: wide
    flow_column: q_total_ls
    flow_unit: l/s

  - code: ML
    name: Molinete
    subdir: molinete
    summary_format: wide
    flow_column: caudal
    flow_unit: m3/s
```

El ranking debe usar los códigos definidos aquí.

## 5. Ranking de instrumentos

El ranking se aplica cuando hay más de una medición para el mismo punto y la misma fecha.

El proceso es:

1. Agrupar mediciones repetidas del mismo instrumento, punto y día.
2. Promediar esos duplicados.
3. Aplicar ranking entre instrumentos.
4. Conservar una única serie diaria por punto.

Ejemplo:

```bash
--ranking "NV ML FT"
```

Significa:

- si hay Nivus y Molinete para el mismo punto/día, gana Nivus;
- si no hay Nivus pero hay Molinete y FlowTracker, gana Molinete;
- si solo hay FlowTracker, se usa FlowTracker.

Los códigos se resuelven desde `measuring_instruments`, incluyendo `code`, `name` y `subdir`. No deberían hardcodearse en el análisis.

## 6. Variables X/Y y regresión

Cada workflow define columnas posibles:

| Workflow | Roles posibles |
| --- | --- |
| `gauges_vs_model` | `gauge`, `model` |
| `gauges_vs_stations` | `station`, `gauge` |
| `model_vs_stations` | `station`, `model` |

Los roles se traducen a columnas internas:

| Rol | Columna |
| --- | --- |
| `gauge` | `q_gauge_l/s` |
| `model` | `q_model_l/s` |
| `station` | `q_station_l/s` |

El Excel registra `x_role`, `y_role`, `x_column` e `y_column` en la hoja `RunConfig`.

## 7. Ejecución por CLI

### 7.1 gauges_vs_model con todos los puntos

```bash
aforix analyze correlation run -c configs/examples/main.yaml --type gauges_vs_model
```

Windows:

```bat
aforix analyze correlation run -c configs/examples/main.yaml --type gauges_vs_model
```

### 7.2 gauges_vs_model con puntos específicos

```bash
aforix analyze correlation run -c configs/examples/main.yaml --type gauges_vs_model --points "3 5 8"
```

También se acepta:

```bash
aforix analyze correlation run -c configs/examples/main.yaml --type gauges_vs_model --points "3,5,8"
```

### 7.3 gauges_vs_stations con todos los pares posibles

```bash
aforix analyze correlation run -c configs/examples/main.yaml --type gauges_vs_stations
```

Si no se pasan pares explícitos, el workflow intenta combinar estaciones disponibles con puntos disponibles.

### 7.4 gauges_vs_stations con pares explícitos

```bash
aforix analyze correlation run -c configs/examples/main.yaml --type gauges_vs_stations --pairs "[44 5] [115 11]"
```

Formato:

```text
[station point]
```

donde `station` es la estación DINAGUA y `point` es el punto de aforo.

### 7.5 gauges_vs_stations con cruce exacto

```bash
aforix analyze correlation run -c configs/examples/main.yaml --type gauges_vs_stations --pairs "[44 5] [115 11]" --match-mode exact
```

### 7.6 gauges_vs_stations con ventana temporal

```bash
aforix analyze correlation run -c configs/examples/main.yaml --type gauges_vs_stations --pairs "[44 5] [115 11]" --match-mode window --window-days 3
```

Esto busca coincidencias dentro de ±3 días.

### 7.7 model_vs_stations con pares explícitos

```bash
aforix analyze correlation run -c configs/examples/main.yaml --type model_vs_stations --pairs "[44 5] [115 11]"
```

Formato:

```text
[station point]
```

Aquí `point` es el punto del modelo.

### 7.8 model_vs_stations con todos los pares

```bash
aforix analyze correlation run -c configs/examples/main.yaml --type model_vs_stations --all-pairs
```

### 7.9 Opciones comunes

```text
--ranking "NV FT ML"
--timestep daily
--start-date YYYYMMDD
--end-date YYYYMMDD
--interactive
```

Ejemplo multilinea en Windows:

```bat
aforix analyze correlation run ^
  -c configs/examples/main.yaml ^
  --type gauges_vs_stations ^
  --pairs "[44 5] [115 11]" ^
  --match-mode window ^
  --window-days 3 ^
  --ranking "NV FT ML"
```

## 8. Modo interactivo

Ejecutar:

```bash
aforix analyze correlation run -c configs/examples/main.yaml --interactive
```

El modo interactivo pregunta:

- tipo de correlación;
- ranking de instrumentos para workflows con aforos;
- timestep para workflows con estaciones;
- pares para workflows con estaciones;
- puntos para `gauges_vs_model`;
- rango de fechas para `gauges_vs_model`.

Según el estado actual del código, algunas opciones avanzadas como `--match-mode window`, `--window-days` y `--all-pairs` son más claras usando CLI parametrizado.

## 9. Ventanas temporales

`match_mode` controla cómo se cruzan fechas en `gauges_vs_stations`:

- `exact`: cruza por la misma fecha.
- `window`: para cada fecha de aforo busca una estación dentro de ±`window_days` y usa la fecha más cercana.

Ejemplo:

```bash
aforix analyze correlation run -c configs/examples/main.yaml --type gauges_vs_stations --pairs "[44 5]" --match-mode window --window-days 3
```

Según el estado actual del código, `model_vs_stations` usa cruce exacto por fecha y no aplica ventana temporal.

## 10. Outputs generados

Los resultados se guardan bajo:

```text
runs/analysis_correlation/
```

### 10.1 gauges_vs_model

Estructura:

```text
runs/analysis_correlation/gauges_vs_model/instruments_{ranking}/{points_label}/
```

Ejemplos:

```text
runs/analysis_correlation/gauges_vs_model/instruments_NV_FT_ML/all_points/
runs/analysis_correlation/gauges_vs_model/instruments_NV_FT_ML/points_3_5_8/
```

Archivos:

```text
P{point}_gauge_vs_model_{start}_{end}.csv
summary_gauges_vs_model_{ranking}_{start}_{end}.csv
correlation_gauges_vs_model_{ranking}_{start}_{end}.xlsx
plots/
```

### 10.2 gauges_vs_stations

Estructura:

```text
runs/analysis_correlation/gauges_vs_stations/{timestep}/instruments_{ranking}/match_{match_mode}_window_{window_days}/{pairs_label}/
```

Archivos:

```text
S{station}_P{point}_gauges_vs_stations_{timestep}_{match_mode}_{start}_{end}.csv
summary_gauges_vs_stations_{timestep}_{match_mode}_window_{window_days}.csv
correlation_gauges_vs_stations_{timestep}_{ranking}_{match_mode}_window_{window_days}.xlsx
plots/
```

### 10.3 model_vs_stations

Estructura:

```text
runs/analysis_correlation/model_vs_stations/{timestep}/
```

Archivos:

```text
S{station}_Pm{point}_model_vs_stations_{timestep}.csv
summary_model_vs_stations_{timestep}.csv
correlation_model_vs_stations_{timestep}.xlsx
plots/
```

### 10.4 Excel

Cada Excel incluye:

- `RunConfig`: parámetros de ejecución;
- `SummaryMetrics`: resumen de métricas;
- hojas individuales por punto o par;
- gráficos de dispersión y serie temporal.

`RunConfig` incluye, según workflow:

```text
analysis_type
x_role
y_role
x_column
y_column
ranking
points/pairs
paths
timestep
match_mode
window_days
```

Si el archivo Excel está abierto y no se puede sobrescribir, Aforix intenta guardar versiones alternativas con sufijo `_v2`, `_v3`, etc.

## 11. Métricas

Las métricas se calculan sobre valores de referencia `a` y comparación `b`, o sobre `Y` y `Y_pred` según la columna reportada.

### 11.1 R²

Usa `sklearn.metrics.r2_score`.

```text
R² = 1 - Σ(y - ŷ)² / Σ(y - mean(y))²
```

Valores más cercanos a 1 indican mejor ajuste. Con menos de 2 datos devuelve `NaN`.

### 11.2 Pearson r

Usa `scipy.stats.pearsonr`.

```text
r = cov(x,y) / (std(x) * std(y))
```

Varía entre -1 y 1. Valores cercanos a 1 indican correlación lineal positiva fuerte. Con menos de 2 datos o series problemáticas devuelve `NaN`.

### 11.3 RMSE

Implementado con NumPy.

```text
RMSE = sqrt(mean((a - b)^2))
```

Menor es mejor. Penaliza errores grandes.

### 11.4 MAE

Implementado con NumPy.

```text
MAE = mean(abs(a - b))
```

Menor es mejor. Es menos sensible a outliers que RMSE.

### 11.5 MAPE

Implementado con NumPy.

```text
MAPE = 100 * mean(abs((b - a) / a))
```

Menor es mejor. Ignora valores donde `a = 0`; si todos son cero, devuelve `NaN`.

### 11.6 PBIAS

Implementado con NumPy.

```text
PBIAS = 100 * Σ(b - a) / Σ(a)
```

Valores cercanos a 0 son mejores. Si la suma de `a` es cero, devuelve `NaN`.

### 11.7 NSE

Implementado con NumPy.

```text
NSE = 1 - Σ(a - b)^2 / Σ(a - mean(a))^2
```

Valores cercanos a 1 son mejores. Si la serie `a` es constante, devuelve `NaN`.

## 12. Reproducibilidad y auditoría

La hoja `RunConfig` es clave para auditar resultados. Permite verificar:

- qué workflow se ejecutó;
- qué roles X/Y se usaron;
- qué columnas internas alimentaron la regresión;
- qué ranking se aplicó;
- qué puntos o pares fueron procesados;
- qué rutas de entrada y salida se usaron.

Para comprobar la orientación de la regresión, revisar en el Excel:

1. Hoja `RunConfig`: `x_role`, `y_role`, `x_column`, `y_column`.
2. Hoja `SummaryMetrics`: `Linear equation`, `X role`, `Y role`.

Ambas deben coincidir.

## 13. Troubleshooting

### No se generan outputs

Revisar que existan datos normalizados, datos externos y fechas en común. Si no hay filas válidas, el workflow puede crear carpeta pero no Excel final.

### No hay intersección de fechas

Revisar los formatos de fecha y el rango temporal. Para `gauges_vs_stations`, probar `--match-mode window --window-days 3`.

### DINAGUA normalizado está vacío

Ejecutar:

```bash
aforix external convert-dinagua -c configs/examples/main.yaml
```

Verificar que el raw tenga columnas reconocibles de fecha y caudal. El caudal raw puede llamarse `q`, `caudal`, `flow`, `valor` o `gasto`.

### Fechas mal parseadas

El conversor DINAGUA usa `dayfirst=True`. En archivos normalizados, revisar que `date` sea parseable por Pandas.

### No aparece un punto esperado

Revisar que exista tanto en aforos como en modelo o estación según el workflow. Los puntos suelen normalizarse removiendo prefijo `P`.

### Ranking no parece respetarse

Revisar `analysis.correlation.default_ranking`, `measuring_instruments` y la columna `source` en los CSV exportados.

### --pairs no genera hojas

Verificar formato:

```text
[station point]
```

Ejemplo:

```text
[44 5] [115 11]
```

En `model_vs_stations`, si no se usa `--pairs`, debe usarse `--all-pairs`.

### Excel abierto

Si el Excel de salida está abierto, Aforix intenta guardar otra versión con sufijo `_v2`, `_v3`, etc.

### Comandos rápidos de revisión

```bash
python -c "import pandas as pd; print(pd.read_csv('database/external/normalized/dinagua/44_daily_station_data.csv').head())"
```

```bash
python -c "import pandas as pd; print(pd.read_csv('database/external/normalized/model/P5_model_data.csv').head())"
```

## 14. Flujo recomendado para usuario nuevo

1. Ejecutar el pipeline principal de aforos hasta `database/normalized`.
2. Colocar datos raw externos en:

```text
database/external/raw/model
database/external/raw/dinagua
```

3. Convertir externos:

```bash
aforix external convert-model -c configs/examples/main.yaml
aforix external convert-dinagua -c configs/examples/main.yaml
```

4. Revisar archivos normalizados externos.
5. Ejecutar `gauges_vs_model`:

```bash
aforix analyze correlation run -c configs/examples/main.yaml --type gauges_vs_model
```

6. Ejecutar `gauges_vs_stations` con pares explícitos:

```bash
aforix analyze correlation run -c configs/examples/main.yaml --type gauges_vs_stations --pairs "[44 5] [115 11]"
```

7. Ejecutar `model_vs_stations`:

```bash
aforix analyze correlation run -c configs/examples/main.yaml --type model_vs_stations --pairs "[44 5] [115 11]"
```

8. Revisar Excel, `SummaryMetrics`, `RunConfig`, CSVs y plots.
