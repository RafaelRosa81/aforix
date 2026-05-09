# Ejemplos batch de Aforix

Esta carpeta contiene ejemplos YAML para ejecutar flujos batch reproducibles en Aforix.

Un archivo batch describe una secuencia de comandos existentes de Aforix. No contiene lógica nueva: solo indica qué comando correr, con qué parámetros y en qué orden.

Guía formal completa:

```text
docs/BATCH_GUIDE.md
```

## 1. Comandos básicos

Validar un batch:

```bash
aforix batch check -b configs/batches/examples/check_only.yaml
```

Ver el plan:

```bash
aforix batch plan -b configs/batches/examples/full_ingest_pipeline.yaml
```

Simular ejecución:

```bash
aforix batch run -b configs/batches/examples/full_ingest_pipeline.yaml --dry-run
```

Ejecutar:

```bash
aforix batch run -b configs/batches/examples/full_ingest_pipeline.yaml
```

Listar comandos batch disponibles:

```bash
aforix batch list-commands
```

## 2. Estructura mínima de un batch

```yaml
version: 1

batch:
  id: check_only
  name: Check-only batch
  description: Validar configuración y sistema batch.

project:
  main_config: configs/examples/main.yaml

execution:
  output_dir: runs/batch
  create_manifest: true
  stop_on_error: true

variables:
  main_config: configs/examples/main.yaml

steps:
  - id: config_check
    command: config-check
    enabled: true
    params:
      config: ${main_config}
```

Campos principales:

| Campo | Descripción |
| --- | --- |
| `version` | versión del formato YAML batch |
| `batch.id` | identificador del batch |
| `project.main_config` | YAML principal de Aforix |
| `execution.output_dir` | raíz para salidas batch |
| `execution.create_manifest` | genera `manifest.json` |
| `variables` | valores reutilizables |
| `steps` | lista ordenada de comandos a ejecutar |

## 3. Catálogo de pipelines completos

| Archivo | Cuándo usarlo | Qué ejecuta |
| --- | --- | --- |
| `check_only.yaml` | primera prueba del sistema batch | `config-check` |
| `normalize_validate.yaml` | cuando `database/raw_canonical` ya existe | `config-check`, `normalize.run`, `validate.run` |
| `full_ingest_pipeline.yaml` | pipeline completo desde raw | ingest, build-groups, normalize, validate, export, análisis |
| `consolidated_data_pipeline.yaml` | trabajo rápido con datos ya consolidados | validate, export tables, quality, stage-discharge, section profiles |
| `analysis_pipeline.yaml` | correr análisis sobre normalized existente | quality, stage-discharge, section profiles |
| `sih_export_pipeline.yaml` | export SIH usando selección/config por defecto | export.sih |
| `sih_export_with_selection.yaml` | export SIH con selection CSV explícito | export.sih con `selection_file` |
| `correlation_gauges_vs_model.yaml` | aforos vs modelo | analysis.correlation `gauges_vs_model` |
| `correlation_gauges_vs_stations.yaml` | aforos vs estaciones, todos los pares | analysis.correlation `gauges_vs_stations` con `all_pairs` |
| `correlation_gauges_vs_stations_pairs.yaml` | aforos vs estaciones, pares explícitos | analysis.correlation `gauges_vs_stations` con `pairs` |
| `correlation_model_vs_stations.yaml` | modelo vs estaciones | analysis.correlation `model_vs_stations` |
| `custom_mixed_pipeline.yaml` | ejemplo libre/personalizable | combinación de config-check, export, análisis y SIH |

## 4. Catálogo de ejemplos atómicos

Los ejemplos atómicos están en:

```text
configs/batches/examples/atomic/
```

Cada archivo ejecuta una sola funcionalidad o un caso muy acotado. Son útiles para aprender parámetros y probar módulos de forma aislada.

| Archivo | Comando batch | Qué muestra |
| --- | --- | --- |
| `atomic/config_check.yaml` | `config-check` | validación mínima de configuración |
| `atomic/ingest_flowtracker.yaml` | `ingest.flowtracker` | ingesta FlowTracker |
| `atomic/ingest_molinete.yaml` | `ingest.molinete` | ingesta Molinete Excel |
| `atomic/ingest_nivus.yaml` | `ingest.nivus` | ingesta Nivus XML |
| `atomic/ingest_m9.yaml` | `ingest.m9` | ingesta M9/ADCP, si está disponible |
| `atomic/build_groups.yaml` | `build-groups` | consolidación hacia `database/raw_canonical` |
| `atomic/normalize_run.yaml` | `normalize.run` | normalización hacia `database/normalized` |
| `atomic/validate_run.yaml` | `validate.run` | validación de datasets normalizados |
| `atomic/export_tables_summary_monthly.yaml` | `export.tables` | Summary mensual con todos los parámetros de export |
| `atomic/export_tables_points_sections.yaml` | `export.tables` | Points/Sections/Gates sin agregación |
| `atomic/export_sih_default.yaml` | `export.sih` | SIH con selection por defecto |
| `atomic/export_sih_selection_file.yaml` | `export.sih` | SIH con `selection_file` explícito |
| `atomic/analysis_quality.yaml` | `analysis.quality` | métricas de calidad y agregaciones |
| `atomic/analysis_stage_discharge.yaml` | `analysis.stage-discharge` | caudal-altura con depth modes y outputs |
| `atomic/analysis_section_profiles.yaml` | `analysis.section-profiles` | perfiles de sección y tipos de gráficos |
| `atomic/correlation_gauges_vs_model.yaml` | `analysis.correlation` | aforos vs modelo |
| `atomic/correlation_gauges_vs_stations.yaml` | `analysis.correlation` | aforos vs estaciones DINAGUA |
| `atomic/correlation_model_vs_stations.yaml` | `analysis.correlation` | modelo vs estaciones DINAGUA |

## 5. Parámetros frecuentes

### 5.1 config

Casi todos los comandos reciben:

```yaml
config: ${main_config}
```

Normalmente apunta a:

```text
configs/examples/main.yaml
```

### 5.2 points

Lista de puntos. Según el comando puede usarse con o sin prefijo `P`.

Ejemplos:

```yaml
points: P1,P8,P13
points: 1,8,13
```

Revisar el ejemplo atómico correspondiente para el formato esperado.

### 5.3 instruments

Lista de instrumentos.

Ejemplo:

```yaml
instruments: NV,FT,ML
```

### 5.4 dates

Rango de fechas.

```yaml
start_date: 2025-01-01
end_date: 2025-12-31
```

En `export.tables` se usan:

```yaml
early_date: 2025-01-01
late_date: 2025-12-31
```

### 5.5 export.tables

Parámetros reales:

```yaml
config: configs/examples/main.yaml
table: Summary          # Summary, Points, Sections, Gates
instrument: all         # all, flowtracker, molinete, nivus, m9
points: P1,P8,P13       # opcional
parameters: q_total_ls  # opcional
early_date: 2025-01-01  # opcional
late_date: 2025-12-31   # opcional
grouping: monthly       # monthly, daily, none
format: xlsx            # xlsx, csv
flat: false             # true, false
aggregation: mean       # mean, sum, min, max, count
```

### 5.6 export.sih

Parámetros reales:

```yaml
config: configs/examples/main.yaml
sih_config: configs/sih/sih.yaml
selection_file: configs/sih/selection_template.csv
```

En batch, `interactive: true` no está soportado.

### 5.7 analysis.quality

Parámetros reales:

```yaml
aggregation: monthly  # measurement, daily, monthly
points: P1,P8,P13
yyyymm: 202501,202502
all_months: false     # true, false
```

### 5.8 analysis.stage-discharge

Parámetros reales:

```yaml
points: P1,P8,P13
start_date: 2025-01-01
end_date: 2026-12-31
instruments: NV,FT,ML
ranking: NV,FT,ML
depth_mode: both              # manual, instrument, both
instrument_stage_mode: both   # mean, max, both
plots: true                   # true, false
excel: true                   # true, false
max_plots: 20
```

### 5.9 analysis.section-profiles

Parámetros reales:

```yaml
instruments: NV,FT,ML
points: P1,P8,P13
start_date: 2025-01-01
end_date: 2026-12-31
x_axis: progr_m       # columna real del dataset
y_axis: prof_m        # columna real del dataset
chart_type: line      # scatter, line
```

En batch, `interactive: true` no está soportado.

### 5.10 analysis.correlation pairs

Formato de pares:

```yaml
pairs: "[44 5] [115 11]"
```

En `gauges_vs_stations`:

```text
[station point]
```

En `model_vs_stations`:

```text
[station model_point]
```

Opciones frecuentes:

```yaml
type: gauges_vs_stations  # gauges_vs_model, gauges_vs_stations, model_vs_stations
timestep: daily           # daily, monthly
match_mode: exact         # exact, window
window_days: 3
all_pairs: false          # true, false
ranking: NV FT ML
```

Mantener los pares entre comillas para evitar problemas YAML.

## 6. manifest.json

Cuando `create_manifest: true`, cada corrida escribe:

```text
runs/batch/<run_id>/manifest.json
```

El manifest registra:

```text
batch_id
run_id
status
timestamps locales y UTC
steps
outputs
warnings
errors
metrics
metadata
```

Información típica por step:

```text
status
duration
outputs
warnings
errors
cpu/ram
input_size_mb
output_size_mb
rows_processed
files_written
metadata específica del comando
```

El manifest es el archivo principal para auditar qué ocurrió en una ejecución batch.

## 7. Warnings comunes

### 7.1 Success sin archivos escritos

Algunos análisis pueden terminar técnicamente bien pero sin outputs:

```text
status = success
files_written = 0
warnings = [...]
```

Casos frecuentes:

- no hay datos para los puntos seleccionados;
- no hay cruce de fechas;
- filtros demasiado restrictivos;
- faltan datos externos normalizados;
- no hay perfiles/secciones disponibles.

### 7.2 correlation sin outputs

Puede ocurrir en:

```text
analysis.correlation
```

Especialmente si no hay intersección entre aforos, modelo o estaciones DINAGUA.

### 7.3 section-profiles sin outputs

Puede ocurrir si no existen datos normalizados suficientes para construir perfiles con los filtros elegidos.

## 8. Orden recomendado para usuarios nuevos

### Primera prueba

```bash
aforix batch check -b configs/batches/examples/check_only.yaml
aforix batch plan -b configs/batches/examples/check_only.yaml
aforix batch run -b configs/batches/examples/check_only.yaml --dry-run
aforix batch run -b configs/batches/examples/check_only.yaml
```

### Pipeline completo desde raw

```bash
aforix batch check -b configs/batches/examples/full_ingest_pipeline.yaml
aforix batch plan -b configs/batches/examples/full_ingest_pipeline.yaml
aforix batch run -b configs/batches/examples/full_ingest_pipeline.yaml --dry-run
aforix batch run -b configs/batches/examples/full_ingest_pipeline.yaml
```

### Ejemplo atómico

```bash
aforix batch check -b configs/batches/examples/atomic/export_tables_summary_monthly.yaml
aforix batch plan -b configs/batches/examples/atomic/export_tables_summary_monthly.yaml
aforix batch run -b configs/batches/examples/atomic/export_tables_summary_monthly.yaml --dry-run
aforix batch run -b configs/batches/examples/atomic/export_tables_summary_monthly.yaml
```

## 9. Buenas prácticas

- Empezar con `check_only.yaml`.
- Usar `batch plan` antes de correr.
- Usar `--dry-run` antes de la ejecución real.
- Revisar `manifest.json` después de cada corrida.
- Mantener parámetros repetidos en `variables`.
- Comentar los YAML propios.
- Copiar un ejemplo existente antes de crear un batch nuevo.
- Usar pocos puntos y fechas acotadas al probar.
- Revisar warnings aunque el batch termine exitosamente.

## 10. Validación rápida de todos los ejemplos atómicos

```bash
aforix batch check -b configs/batches/examples/atomic/config_check.yaml
aforix batch check -b configs/batches/examples/atomic/ingest_flowtracker.yaml
aforix batch check -b configs/batches/examples/atomic/ingest_molinete.yaml
aforix batch check -b configs/batches/examples/atomic/ingest_nivus.yaml
aforix batch check -b configs/batches/examples/atomic/ingest_m9.yaml
aforix batch check -b configs/batches/examples/atomic/build_groups.yaml
aforix batch check -b configs/batches/examples/atomic/normalize_run.yaml
aforix batch check -b configs/batches/examples/atomic/validate_run.yaml
aforix batch check -b configs/batches/examples/atomic/export_tables_summary_monthly.yaml
aforix batch check -b configs/batches/examples/atomic/export_tables_points_sections.yaml
aforix batch check -b configs/batches/examples/atomic/export_sih_default.yaml
aforix batch check -b configs/batches/examples/atomic/export_sih_selection_file.yaml
aforix batch check -b configs/batches/examples/atomic/analysis_quality.yaml
aforix batch check -b configs/batches/examples/atomic/analysis_stage_discharge.yaml
aforix batch check -b configs/batches/examples/atomic/analysis_section_profiles.yaml
aforix batch check -b configs/batches/examples/atomic/correlation_gauges_vs_model.yaml
aforix batch check -b configs/batches/examples/atomic/correlation_gauges_vs_stations.yaml
aforix batch check -b configs/batches/examples/atomic/correlation_model_vs_stations.yaml
```

## 11. Pruebas del proyecto

Después de modificar ejemplos batch o documentación relacionada:

```bash
pytest
```
