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

## 3. Catálogo de ejemplos

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

## 4. Parámetros frecuentes

### 4.1 config

Casi todos los comandos reciben:

```yaml
config: ${main_config}
```

Normalmente apunta a:

```text
configs/examples/main.yaml
```

### 4.2 points

Lista de puntos. Según el comando puede usarse con o sin prefijo `P`.

Ejemplos:

```yaml
points: P1,P8,P13
points: 1,8,13
```

Revisar la guía específica de cada módulo para el formato exacto.

### 4.3 instruments

Lista de instrumentos.

Ejemplo:

```yaml
instruments: NV,FT,ML
```

### 4.4 dates

Rango de fechas.

```yaml
start_date: 2025-01-01
end_date: 2025-12-31
```

En algunos comandos antiguos puede aparecer como:

```yaml
early_date: 2025-01-01
late_date: 2025-12-31
```

### 4.5 export.tables

Parámetros frecuentes:

```yaml
table: Summary          # Summary, Points, Sections, Gates
instrument: nivus       # opcional; instrumento específico
points: P1,P8,P13       # opcional; filtra puntos
parameters: q_total_ls  # opcional; columnas/variables
early_date: 2025-01-01  # opcional; fecha inicial
late_date: 2025-12-31   # opcional; fecha final
grouping: monthly       # none, daily, monthly
format: xlsx            # xlsx o csv
aggregation: mean       # mean, sum u otra agregación soportada por export
```

### 4.6 analysis.correlation pairs

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

Mantener los pares entre comillas para evitar problemas YAML.

## 5. manifest.json

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

## 6. Warnings comunes

### 6.1 Success sin archivos escritos

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

### 6.2 correlation sin outputs

Puede ocurrir en:

```text
analysis.correlation
```

Especialmente si no hay intersección entre aforos, modelo o estaciones DINAGUA.

### 6.3 section-profiles sin outputs

Puede ocurrir si no existen datos normalizados suficientes para construir perfiles con los filtros elegidos.

## 7. Orden recomendado para usuarios nuevos

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

### Trabajo con datos ya consolidados

```bash
aforix batch run -b configs/batches/examples/consolidated_data_pipeline.yaml
```

### Análisis solamente

```bash
aforix batch run -b configs/batches/examples/analysis_pipeline.yaml
```

### SIH

```bash
aforix batch run -b configs/batches/examples/sih_export_pipeline.yaml
```

## 8. Buenas prácticas

- Empezar con `check_only.yaml`.
- Usar `batch plan` antes de correr.
- Usar `--dry-run` antes de la ejecución real.
- Revisar `manifest.json` después de cada corrida.
- Mantener parámetros repetidos en `variables`.
- Comentar los YAML propios.
- Copiar un ejemplo existente antes de crear un batch nuevo.
- Usar pocos puntos y fechas acotadas al probar.
- Revisar warnings aunque el batch termine exitosamente.

## 9. Validación rápida de todos los ejemplos

Ejemplo manual:

```bash
aforix batch check -b configs/batches/examples/check_only.yaml
aforix batch check -b configs/batches/examples/normalize_validate.yaml
aforix batch check -b configs/batches/examples/full_ingest_pipeline.yaml
aforix batch check -b configs/batches/examples/consolidated_data_pipeline.yaml
aforix batch check -b configs/batches/examples/analysis_pipeline.yaml
aforix batch check -b configs/batches/examples/sih_export_pipeline.yaml
aforix batch check -b configs/batches/examples/sih_export_with_selection.yaml
aforix batch check -b configs/batches/examples/correlation_gauges_vs_model.yaml
aforix batch check -b configs/batches/examples/correlation_gauges_vs_stations.yaml
aforix batch check -b configs/batches/examples/correlation_gauges_vs_stations_pairs.yaml
aforix batch check -b configs/batches/examples/correlation_model_vs_stations.yaml
aforix batch check -b configs/batches/examples/custom_mixed_pipeline.yaml
```

## 10. Pruebas del proyecto

Después de modificar ejemplos batch o documentación relacionada:

```bash
pytest
```
