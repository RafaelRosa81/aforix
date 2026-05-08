# Pipeline de procesamiento

Aforix transforma datos de aforos mediante un flujo por etapas. Este documento define la referencia principal del pipeline operativo.

## Flujo general

```text
raw
-> ingest
-> runs/.../raw_canonical
-> build-groups
-> database/raw_canonical
-> normalize
-> database/normalized
-> audit / validate / export / analysis
```

La idea central es separar claramente:

- los archivos originales del usuario;
- las salidas por corrida;
- la base canónica consolidada;
- la base normalizada común;
- las etapas posteriores de control, exportación y análisis.

## 1. raw

`raw` contiene archivos originales generados por cada instrumento.

Ubicación típica:

```text
data/raw/
```

Subcarpetas esperadas según `configs/examples/main.yaml`:

```text
data/raw/FT   # FlowTracker
data/raw/ML   # Molinete
data/raw/NV   # Nivus
data/raw/M9   # M9, previsto o experimental
```

Aforix no debería modificar directamente estos archivos. Son la fuente primaria de trazabilidad.

## 2. ingest

La etapa `ingest` lee archivos raw y genera salidas estructuradas por instrumento dentro de `runs/`.

Comandos:

```bash
aforix ingest flowtracker -c configs/examples/main.yaml
aforix ingest molinete -c configs/examples/main.yaml
aforix ingest nivus -c configs/examples/main.yaml
aforix ingest m9 -c configs/examples/main.yaml
```

En Windows CMD:

```bat
aforix ingest flowtracker -c configs/examples/main.yaml
aforix ingest molinete -c configs/examples/main.yaml
aforix ingest nivus -c configs/examples/main.yaml
aforix ingest m9 -c configs/examples/main.yaml
```

### 2.1 Metadata configurable

La ingesta usa `metadata_policy` para extraer metadata crítica de forma configurable desde YAML.

Campos principales:

```text
station_id
station_name
measurement_date
measurement_time
```

Esto evita hardcodear en Python de dónde sale cada dato. Cada instrumento puede definir fuentes y transformaciones propias.

Ejemplos de fuentes configurables:

```text
raw_field
path_regex
filename_regex
```

Ejemplos de transformaciones:

```text
strip
uppercase
remove_prefix
digits_only
```

El objetivo es que FlowTracker, Molinete y Nivus puedan poblar la misma metadata de trazabilidad aunque sus archivos raw tengan estructuras diferentes.

## 3. runs

Cada ejecución queda registrada en una carpeta independiente dentro de:

```text
runs/
```

Ejemplo conceptual:

```text
runs/ingest_flowtracker/<timestamp>/outputs/raw_canonical/flowtracker/
runs/ingest_molinete/<timestamp>/outputs/raw_canonical/molinete/
runs/ingest_nivus/<timestamp>/outputs/raw_canonical/nivus/
```

Esta capa permite:

- auditar resultados intermedios;
- comparar corridas;
- depurar errores de ingesta;
- repetir etapas sin modificar los raw originales;
- conservar trazabilidad hacia `source_run_dir` y `run_id`.

## 4. runs/.../raw_canonical

Cada corrida de ingesta genera una versión raw canonical por instrumento.

Esta salida ya no es el archivo raw original, pero todavía conserva nombres y estructura cercanos al instrumento. Es una capa intermedia entre raw y la base consolidada.

Ejemplos de grupos:

```text
Summary
Points
Sections
Gates
```

No todos los instrumentos producen todos los grupos. Por ejemplo, FlowTracker puede no producir `Sections` o `Gates`, mientras Nivus sí puede usarlos.

## 5. build-groups

`build-groups` consolida salidas de ingesta desde `runs/` hacia una base canónica estable:

```bash
aforix build-groups -c configs/examples/main.yaml
```

Salida principal:

```text
database/raw_canonical/
```

### 5.1 Selección configurable de runs

La selección de runs se controla desde:

```yaml
build_groups:
  use_latest_run_only: true
```

Cuando `use_latest_run_only` es `true`, Aforix usa solo la corrida más reciente compatible por fuente/instrumento. Esto reduce el riesgo de mezclar corridas antiguas y nuevas.

La configuración también puede contemplar listas explícitas:

```yaml
include_runs: [...]
exclude_runs: [...]
```

Estas listas permiten incluir o excluir corridas concretas cuando se necesita un control más fino.

### 5.2 Deduplicación

La deduplicación se controla con:

```yaml
build_groups:
  deduplicate: true
  deduplicate_by:
    - instrument
    - station_id
    - measurement_date
    - measurement_time
    - group
```

Su objetivo es evitar que la misma medición entre más de una vez en `database/raw_canonical`.

Configurar mal `deduplicate_by` puede eliminar registros que deberían mantenerse o conservar duplicados que deberían quitarse. Por eso conviene usar claves de trazabilidad estables.

### 5.3 Manifest

Cuando está habilitado:

```yaml
build_groups:
  manifest: true
```

Aforix genera manifiestos en:

```text
database/raw_canonical/_manifests/
```

El manifest permite auditar qué archivos/runs participaron en la consolidación.

## 6. database/raw_canonical

`database/raw_canonical` contiene datos consolidados, estructurados por instrumento y grupo, pero todavía cercanos a los formatos de origen.

Es la entrada principal de `normalize`.

Ejemplo conceptual:

```text
database/raw_canonical/flowtracker/
database/raw_canonical/molinete/
database/raw_canonical/nivus/
database/raw_canonical/_manifests/
```

Esta capa debe conservar columnas de trazabilidad como:

```text
station_id
station_name
measurement_date
measurement_time
instrument
source_file
source_run_dir
run_id
```

## 7. normalize

`normalize` convierte datos canónicos en tablas comparables entre instrumentos.

Comando:

```bash
aforix normalize run -c configs/examples/main.yaml
```

Salida principal:

```text
database/normalized/
```

La normalización usa specs YAML desde:

```text
configs/normalization/
```

Ejemplos:

```text
configs/normalization/flowtracker.yaml
configs/normalization/molinete.yaml
configs/normalization/nivus.yaml
```

### 7.1 Política de escritura

La escritura de outputs normalizados se controla con:

```yaml
normalize:
  write_policy: overwrite
```

Valores soportados:

| Valor | Comportamiento |
| --- | --- |
| `overwrite` | permite sobrescribir outputs normalizados existentes e informa la acción |
| `fail_if_exists` | detiene la normalización si el archivo de salida ya existe |

Usar `overwrite` es cómodo durante desarrollo. Usar `fail_if_exists` es más seguro cuando se quiere evitar reemplazar resultados por accidente.

### 7.2 Groups, concat_groups y sources

La configuración controla qué grupos normalizar:

```yaml
normalize:
  groups:
    - Summary
    - Points
    - Sections
    - Gates
```

Qué grupos concatenar además de mantener salidas por archivo:

```yaml
normalize:
  concat_groups:
    - Summary
    - Points
```

Y qué fuentes procesar:

```yaml
normalize:
  sources:
    - flowtracker
    - molinete
    - nivus
```

## 8. database/normalized

`database/normalized` contiene datasets bajo un esquema común. Es la capa recomendada para:

- auditoría;
- validación;
- exportación;
- análisis.

Columnas de trazabilidad esperadas:

```text
station_id
station_code
station_name
measurement_date
measurement_time
instrument
source_file
source_run_dir
run_id
```

Grupos típicos:

```text
Summary
Points
Sections
Gates
```

Columnas hidráulicas principales:

```text
q_total_m3s
q_total_ls
area_total_m2
width_total_m
depth_mean_m
velocity_mean_m_s
point_index
distance_m
depth_m
area_m2
q_m3s
q_ls
```

## 9. audit

Aforix incluye un script de auditoría técnica del pipeline:

```bash
python scripts/audit_pipeline_outputs.py
```

En Windows CMD:

```bat
python scripts\audit_pipeline_outputs.py
```

Este script audita principalmente:

```text
database/raw_canonical
database/normalized
```

Revisa:

- columnas esperadas;
- duplicados por grupo;
- consistencia hidráulica entre `Summary` y `Points`;
- consistencia de unidades m3/s ↔ L/s;
- rangos básicos;
- casos informativos como caudales negativos.

Importante: caudales negativos pueden ser válidos en ciertos contextos hidráulicos. El audit los marca como información, no necesariamente como error.

También marca Nivus `Gates` como `not_checked` hasta definir una clave única confiable.

El audit no reemplaza `validate`. Es una revisión técnica amplia de outputs del pipeline, útil para control operativo y diagnóstico.

## 10. validate

`validate` ejecuta validaciones configuradas formalmente sobre los datasets normalizados.

```bash
aforix validate run -c configs/examples/main.yaml
```

Salida principal:

```text
database/validation/
```

Puede revisar:

- columnas requeridas;
- duplicados;
- completitud;
- rangos;
- consistencia hidráulica.

`validate` se configura desde la sección `validation` de `configs/examples/main.yaml`.

## 11. export

`export` genera salidas orientadas a usuarios finales.

Ejemplos:

```bash
aforix export tables -c configs/examples/main.yaml --interactive
aforix export excel -c configs/examples/main.yaml
aforix export sih -c configs/examples/main.yaml
```

Estas salidas deben consumir preferentemente `database/normalized`.

## 12. analysis

`analysis` incluye procesos hidrológicos o estadísticos posteriores.

Ejemplos documentados:

```text
correlation
quality_metrics
stage_discharge
section_profiles
```

Esta capa debe trabajar sobre `database/normalized` o fuentes externas normalizadas configuradas.

## 13. Flujo recomendado completo

```bash
aforix config-check -c configs/examples/main.yaml
aforix ingest flowtracker -c configs/examples/main.yaml
aforix ingest molinete -c configs/examples/main.yaml
aforix ingest nivus -c configs/examples/main.yaml
aforix build-groups -c configs/examples/main.yaml
aforix normalize run -c configs/examples/main.yaml
python scripts/audit_pipeline_outputs.py
aforix validate run -c configs/examples/main.yaml
```

Windows CMD:

```bat
aforix config-check -c configs/examples/main.yaml
aforix ingest flowtracker -c configs/examples/main.yaml
aforix ingest molinete -c configs/examples/main.yaml
aforix ingest nivus -c configs/examples/main.yaml
aforix build-groups -c configs/examples/main.yaml
aforix normalize run -c configs/examples/main.yaml
python scripts\audit_pipeline_outputs.py
aforix validate run -c configs/examples/main.yaml
```

## Principios

- Separar responsabilidades por etapa.
- Mantener trazabilidad desde archivos originales hasta salidas finales.
- Persistir resultados intermedios.
- Usar configuración YAML para reproducibilidad.
- Evitar hardcodear metadata de instrumentos en Python.
- Incorporar nuevos instrumentos mediante adaptadores y reglas de normalización.
- Auditar outputs antes de usarlos en exportación o análisis.
