# Guía batch de Aforix

Esta guía documenta la infraestructura batch de Aforix para ejecutar flujos reproducibles mediante archivos YAML.

## 1. Qué es un batch

Un batch es una receta declarativa que indica a Aforix qué comandos ejecutar, en qué orden y con qué parámetros.

Un batch no reemplaza los comandos CLI existentes. Los orquesta.

Ejemplo conceptual:

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

## 2. Qué problema resuelve

El sistema batch permite:

- repetir pipelines completos sin escribir muchos comandos manualmente;
- documentar una corrida como YAML versionable;
- validar un flujo antes de ejecutarlo;
- generar un plan de ejecución;
- ejecutar en modo dry-run;
- registrar resultados por step;
- guardar un `manifest.json` con trazabilidad;
- recolectar métricas operativas;
- detectar warnings cuando una etapa termina sin outputs.

## 3. Relación con la CLI existente

Cada step batch apunta a un comando registrado.

Ejemplo:

```yaml
- id: normalize
  command: normalize.run
  params:
    config: configs/examples/main.yaml
```

Ese step reutiliza la lógica existente de normalización. El batch no implementa normalización propia.

Flujo conceptual:

```text
batch YAML -> loader -> validator -> planner -> registry -> comando Aforix -> CommandResult -> manifest.json
```

## 4. Comandos CLI batch

### 4.1 batch check

Valida estructura YAML y comandos registrados.

```bash
aforix batch check -b configs/batches/examples/check_only.yaml
```

Úselo antes de ejecutar un batch nuevo.

### 4.2 batch plan

Muestra el plan de ejecución sin correr los comandos.

```bash
aforix batch plan -b configs/batches/examples/full_ingest_pipeline.yaml
```

Sirve para revisar orden, IDs y comandos.

### 4.3 batch run --dry-run

Simula la ejecución sin ejecutar los comandos reales.

```bash
aforix batch run -b configs/batches/examples/full_ingest_pipeline.yaml --dry-run
```

Útil para verificar que el runner puede resolver el batch completo.

### 4.4 batch run

Ejecuta el batch real.

```bash
aforix batch run -b configs/batches/examples/full_ingest_pipeline.yaml
```

### 4.5 batch list-commands

Lista comandos disponibles en el registry batch.

```bash
aforix batch list-commands
```

## 5. Registry de comandos

El registry es el catálogo interno que asocia nombres batch con funciones reales de Aforix.

Ejemplos de comandos registrados:

```text
config-check
ingest.flowtracker
ingest.molinete
ingest.nivus
ingest.m9
build-groups
normalize.run
validate.run
export.tables
export.sih
analysis.quality
analysis.stage-discharge
analysis.section-profiles
analysis.correlation
```

El usuario no debería inventar nombres de comandos. Debe usar `aforix batch list-commands` para ver los disponibles.

## 6. Estructura YAML

### 6.1 version

```yaml
version: 1
```

Versión del formato batch.

### 6.2 batch

```yaml
batch:
  id: full_ingest_pipeline
  name: Full ingest pipeline
  description: End-to-end ingest, grouping, normalization, validation, export and analysis pipeline.
```

| Campo | Significado |
| --- | --- |
| `id` | identificador estable del batch |
| `name` | nombre legible |
| `description` | descripción para usuarios |

### 6.3 project

```yaml
project:
  main_config: configs/examples/main.yaml
```

Ruta al YAML principal de Aforix.

### 6.4 execution

```yaml
execution:
  output_dir: runs/batch
  create_manifest: true
  stop_on_error: true
  continue_on_error: false
```

| Campo | Significado |
| --- | --- |
| `output_dir` | carpeta raíz para salidas batch |
| `create_manifest` | si debe escribir `manifest.json` |
| `stop_on_error` | detener al primer error |
| `continue_on_error` | permitir continuar luego de errores, si está soportado por la configuración |

### 6.5 variables

```yaml
variables:
  main_config: configs/examples/main.yaml
  export_format: xlsx
  grouping: monthly
```

Las variables permiten evitar repetir valores.

Se usan así:

```yaml
config: ${main_config}
format: ${export_format}
```

### 6.6 steps

```yaml
steps:
  - id: normalize
    command: normalize.run
    enabled: true
    params:
      config: ${main_config}
```

| Campo | Significado |
| --- | --- |
| `id` | identificador único del step dentro del batch |
| `command` | comando registrado en batch registry |
| `enabled` | permite activar/desactivar el step |
| `params` | parámetros enviados al comando |

## 7. CommandResult

Los comandos batch instrumentados devuelven un resultado operacional llamado `CommandResult`.

Su objetivo es informar al runner qué ocurrió durante el step.

Conceptualmente puede incluir:

```text
status
outputs
warnings
errors
metrics
metadata
```

Esto permite que el batch construya un `manifest.json` útil, en vez de limitarse a indicar que un comando terminó o falló.

## 8. manifest.json

Cada ejecución batch puede generar:

```text
runs/batch/<run_id>/manifest.json
```

El manifest registra información de la corrida y de cada step.

Información típica por corrida:

```text
batch_id
run_id
status
started_at_local
started_at_utc
finished_at_local
finished_at_utc
duration
```

Información típica por step:

```text
id
command
status
duration
outputs
warnings
errors
metrics
metadata
```

## 9. Métricas por step

La infraestructura batch puede registrar métricas operativas.

Métricas generales:

```text
duration
CPU
RAM
```

Métricas reportadas por comandos instrumentados:

```text
input_size_mb
output_size_mb
rows_processed
files_written
```

No todos los comandos reportan todas las métricas. Algunas dependen del tipo de etapa.

## 10. Warnings y errores

### 10.1 Warnings

Un step puede terminar correctamente y aun así generar warnings.

Ejemplos:

```text
analysis.correlation terminó sin generar outputs
analysis.section-profiles terminó sin escribir archivos
```

Esto no necesariamente es un error de ejecución. Puede indicar que no hubo cruce de fechas, puntos o datos suficientes.

### 10.2 Errors

Los errores indican que el step falló.

Si `stop_on_error: true`, el batch se detiene.

## 11. Pipelines batch disponibles

Los ejemplos están en:

```text
configs/batches/examples/
```

Ejemplos actuales:

| Archivo | Uso principal |
| --- | --- |
| `check_only.yaml` | validar infraestructura batch y config principal |
| `normalize_validate.yaml` | normalizar y validar datos ya consolidados |
| `full_ingest_pipeline.yaml` | pipeline completo desde ingest hasta análisis |
| `consolidated_data_pipeline.yaml` | trabajar desde datos ya consolidados |
| `analysis_pipeline.yaml` | ejecutar análisis sobre datos normalizados |
| `sih_export_pipeline.yaml` | exportación SIH con selección por defecto |
| `sih_export_with_selection.yaml` | exportación SIH con selection CSV explícito |
| `correlation_gauges_vs_model.yaml` | correlación aforos vs modelo |
| `correlation_gauges_vs_stations.yaml` | correlación aforos vs estaciones DINAGUA |
| `correlation_gauges_vs_stations_pairs.yaml` | correlación aforos vs estaciones con pares explícitos |
| `correlation_model_vs_stations.yaml` | correlación modelo vs estaciones DINAGUA |
| `custom_mixed_pipeline.yaml` | ejemplo mixto personalizable |

## 12. Buenas prácticas

1. Ejecutar primero `batch check`.
2. Ejecutar luego `batch plan`.
3. Probar `batch run --dry-run`.
4. Recién después ejecutar `batch run`.
5. Mantener YAMLs simples y comentados.
6. Usar variables para rutas y parámetros repetidos.
7. Empezar con pocos puntos y fechas acotadas.
8. Revisar siempre `manifest.json`.
9. Revisar warnings aunque el batch termine en success.
10. Versionar YAMLs importantes.

## 13. Troubleshooting

### 13.1 El batch no valida

Ejecutar:

```bash
aforix batch check -b <archivo.yaml>
```

Revisar:

- indentación YAML;
- `version`;
- `batch.id`;
- `steps`;
- nombres de comandos;
- parámetros requeridos.

### 13.2 Comando no registrado

Ejecutar:

```bash
aforix batch list-commands
```

Usar exactamente el nombre listado.

### 13.3 El batch termina success pero no hay outputs

Revisar warnings en `manifest.json`.

Casos frecuentes:

- no hay datos para los puntos seleccionados;
- no hay cruce de fechas;
- un análisis no encontró suficiente información;
- filtros demasiado restrictivos.

### 13.4 Correlation no genera outputs

Puede ocurrir si no hay intersección entre aforos y datos externos.

Revisar:

- `points`;
- `pairs`;
- `all_pairs`;
- `start_date` / `end_date`;
- `match_mode`;
- `window_days`;
- datos externos normalizados.

### 13.5 Section profiles no genera outputs

Puede ocurrir si no hay datos suficientes de perfiles/secciones para los puntos o instrumentos elegidos.

Revisar:

- `points`;
- `instruments`;
- rango de fechas;
- existencia de `Points` normalizados con columnas requeridas.

## 14. Comandos para probar

```bash
aforix batch check -b configs/batches/examples/check_only.yaml
aforix batch plan -b configs/batches/examples/full_ingest_pipeline.yaml
aforix batch run -b configs/batches/examples/full_ingest_pipeline.yaml --dry-run
pytest
```
