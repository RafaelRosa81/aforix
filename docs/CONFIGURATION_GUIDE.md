# Guía de configuración de Aforix

Esta guía explica cómo configurar Aforix desde cero para ejecutar el pipeline completo desde archivos raw hasta datos normalizados.

Está pensada para usuarios nuevos: no asume conocimiento previo del repo, de la estructura interna ni de los nombres de carpetas.

## 1. Qué es Aforix

Aforix es una biblioteca y CLI en Python para procesar datos de aforos hidráulicos provenientes de instrumentos como:

- FlowTracker;
- Molinete;
- Nivus;
- M9 / ADCP, previsto para una etapa posterior.

El objetivo es transformar archivos originales de campo en tablas trazables, consistentes y comparables entre instrumentos.

Pipeline operativo:

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

## 2. Qué debe preparar el usuario

Antes de ejecutar Aforix, el usuario debe tener:

1. El repo instalado en un entorno Python.
2. El archivo principal de configuración: `configs/examples/main.yaml`.
3. Los archivos raw de instrumentos dentro de `data/raw/`.
4. Los YAML de normalización en `configs/normalization/`.
5. Opcionalmente, archivos de configuración adicionales para exportaciones o análisis.

El usuario no debería modificar código Python para ejecutar un proyecto normal. La mayoría de los cambios operativos deben hacerse en YAML.

## 3. Estructura esperada de carpetas

Estructura típica:

```text
aforix/
├── configs/
│   ├── examples/
│   │   └── main.yaml
│   ├── normalization/
│   │   ├── flowtracker.yaml
│   │   ├── molinete.yaml
│   │   └── nivus.yaml
│   └── specs/
│       └── flowtracker.yaml
├── data/
│   └── raw/
│       ├── FT/
│       ├── ML/
│       ├── NV/
│       └── M9/
├── runs/
├── database/
│   ├── raw_canonical/
│   ├── normalized/
│   └── validation/
└── outputs/
```

Carpetas locales o generadas:

```text
data/
runs/
database/
outputs/
```

Estas carpetas no deberían versionarse en Git, salvo casos muy controlados de ejemplos pequeños.

## 4. Archivo principal: configs/examples/main.yaml

`main.yaml` controla rutas, instrumentos, etapas del pipeline, exportaciones y análisis.

Las secciones principales actuales son:

```yaml
project: ...
paths: ...
ingest: ...
build_groups: ...
normalize: ...
validation: ...
export: ...
external_sources: ...
analysis: ...
```

Cada sección se explica a continuación.

## 5. project

Ejemplo:

```yaml
project:
  name: aforix
  description: Pipeline para procesamiento de datos de aforos
  timezone: America/Montevideo
```

| Campo | Qué hace | Riesgo si está mal |
| --- | --- | --- |
| `name` | nombre del proyecto | bajo; se usa como metadata descriptiva |
| `description` | descripción del proyecto | bajo; sirve para documentación y claridad |
| `timezone` | zona horaria de referencia | medio; puede afectar interpretación futura de fechas/horas |

Recomendación: usar siempre una zona horaria explícita. Para Uruguay:

```yaml
timezone: America/Montevideo
```

## 6. paths

Ejemplo:

```yaml
paths:
  raw_data_dir: data/raw
  runs_root: runs
  database_root: database
```

| Campo | Qué hace | Si no existe | Riesgo de configurarlo mal |
| --- | --- | --- | --- |
| `raw_data_dir` | carpeta base donde el usuario coloca archivos originales | la ingesta no encontrará datos | alto |
| `runs_root` | carpeta donde se escriben corridas de ingesta | se crea o falla según etapa/permisos | medio |
| `database_root` | raíz de la base procesada | etapas posteriores no encontrarán outputs | alto |

Estructura derivada:

```text
data/raw/FT
data/raw/ML
data/raw/NV
data/raw/M9
runs/
database/raw_canonical
database/normalized
database/validation
```

## 7. ingest

La sección `ingest` define cómo leer archivos raw de cada instrumento.

Ejemplo resumido:

```yaml
ingest:
  flowtracker:
    enabled: true
    raw_subdir: FT
    spec_path: configs/specs/flowtracker.yaml

  molinete:
    enabled: true
    raw_subdir: ML
    sheet_name: CALCULO

  nivus:
    enabled: true
    raw_subdir: NV

  m9:
    enabled: true
    raw_subdir: M9
```

### 7.1 enabled

```yaml
enabled: true
```

Indica si el instrumento está activo en la configuración.

Valores:

```text
true
false
```

Si está en `false`, el instrumento debería omitirse en procesos que respeten esa configuración.

### 7.2 raw_subdir

```yaml
raw_subdir: FT
```

Define la subcarpeta dentro de `paths.raw_data_dir`.

Ejemplos:

| Instrumento | `raw_subdir` | Ruta final |
| --- | --- | --- |
| FlowTracker | `FT` | `data/raw/FT` |
| Molinete | `ML` | `data/raw/ML` |
| Nivus | `NV` | `data/raw/NV` |
| M9 | `M9` | `data/raw/M9` |

Si se configura mal, Aforix no encontrará los archivos raw.

### 7.3 spec_path

Ejemplo FlowTracker:

```yaml
spec_path: configs/specs/flowtracker.yaml
```

Define un archivo de especificación auxiliar para la ingesta de FlowTracker.

Si el instrumento no usa spec, puede no existir ese campo.

### 7.4 sheet_name

Ejemplo Molinete:

```yaml
sheet_name: CALCULO
```

Indica la hoja Excel a leer para Molinete.

Riesgo: si se configura como una hoja inexistente, la ingesta de Molinete falla o no encuentra datos.

Para los archivos actuales de Molinete, la hoja esperada es:

```text
CALCULO
```

## 8. metadata_policy

`metadata_policy` define cómo extraer metadata crítica de cada medición.

Campos principales:

```text
station_id
station_name
measurement_date
measurement_time
```

Antes, parte de esta lógica podía estar hardcodeada en Python. Ahora se controla desde YAML.

Ejemplo conceptual:

```yaml
metadata_policy:
  station_id:
    strategy: first_non_empty
    sources:
      - type: raw_field
        key: station_id
      - type: path_regex
        pattern: "P(?P<value>\\d{1,4})"
    transforms:
      - strip
      - uppercase
      - name: remove_prefix
        value: "P"
      - digits_only
    normalize:
      digits_only: true
```

### 8.1 strategy

Ejemplo:

```yaml
strategy: first_non_empty
```

`first_non_empty` significa que Aforix prueba las fuentes en orden y toma el primer valor no vacío.

Riesgo: el orden importa. Si una fuente imprecisa aparece antes que una fuente confiable, puede elegirse una metadata incorrecta.

### 8.2 sources

`sources` define de dónde intentar leer el dato.

Tipos usados actualmente:

| Tipo | Qué hace |
| --- | --- |
| `raw_field` | lee un campo extraído desde el archivo raw |
| `path_regex` | extrae información desde la ruta del archivo |
| `filename_regex` | extrae información desde el nombre del archivo |

#### raw_field

```yaml
- type: raw_field
  key: station_id
```

Busca una clave ya extraída por el parser del instrumento.

#### path_regex

```yaml
- type: path_regex
  pattern: "P(?P<value>\\d{1,4})"
```

Busca un patrón en la ruta completa.

Debe contener un grupo llamado:

```text
value
```

#### filename_regex

```yaml
- type: filename_regex
  pattern: "(?P<value>\\d{8})_\\d{6}"
```

Busca un patrón en el nombre del archivo.

También debe usar un grupo:

```text
value
```

### 8.3 transforms

Transformaciones aplicadas al valor extraído.

Usadas actualmente:

| Transformación | Qué hace |
| --- | --- |
| `strip` | elimina espacios al inicio y final |
| `uppercase` | convierte a mayúsculas |
| `remove_prefix` | elimina un prefijo configurado |
| `digits_only` | conserva solo dígitos |

Ejemplo:

```yaml
transforms:
  - strip
  - uppercase
  - name: remove_prefix
    value: "P"
  - digits_only
```

Esto convierte valores como:

```text
" p011 " -> "11"
```

### 8.4 normalize

Normaliza fechas, horas o IDs.

Ejemplo para fecha:

```yaml
normalize:
  input_formats:
    - "%Y%m%d"
    - "%Y-%m-%d"
    - "%Y/%m/%d"
    - "%Y-%m-%d %H:%M:%S"
  output_format: "%Y%m%d"
```

Ejemplo para hora:

```yaml
normalize:
  input_formats:
    - "%H%M%S"
    - "%H:%M:%S"
    - "%H:%M"
  output_format: "%H%M%S"
```

Formato recomendado final:

```text
measurement_date -> YYYYMMDD
measurement_time -> HHMMSS
```

### 8.5 Política por instrumento

#### FlowTracker

`station_id` puede venir de:

```text
station_id
file_name
nombre_del_fichero
input_file
fallback_station_id
path_regex Pxxxx
```

`station_name` puede venir de:

```text
site_name
station_name
nom_del_punto_de_aforo
```

`measurement_date` y `measurement_time` pueden venir de campos como:

```text
start_date_time
start_date_and_time
fecha_y_hora_de_inicio
```

#### Molinete

`station_id` puede venir de:

```text
station_id
fallback_station_id
path_regex Pxxxx
```

`station_name` viene de:

```text
station_name
```

Fecha y hora vienen de:

```text
measurement_date
measurement_time
```

#### Nivus

`station_id` puede venir de:

```text
station_id
ref
reference
fallback_station_id
path_regex Pxxxx
```

Fecha y hora pueden venir de:

```text
measurement_date
measurement_time
timestamp_time
filename_regex
```

## 9. Dónde cargar station_id y station_name en campo

El usuario debe cargar el ID y el nombre del punto durante la medición o en la planilla del instrumento.

| Instrumento | `station_id` / ID del punto | `station_name` / nombre del punto |
| --- | --- | --- |
| FlowTracker | `File_Name` / nombre del fichero | `Site_Name` / nombre del punto de aforo |
| Molinete | `ESTACION Nº:` | `NOMBRE:` |
| Nivus | `Número de referencia` | `Nombre del lugar de medición` |
| M9 | Pendiente hasta analizar archivos base | Pendiente hasta analizar archivos base |

Recomendaciones:

- usar siempre el mismo ID para el mismo punto;
- evitar variantes como `P11`, `P-11`, `Punto 11`, `11` para el mismo sitio;
- revisar que la metadata resultante quede en `runs/.../raw_canonical` antes de consolidar.

## 10. build_groups

`build_groups` consolida salidas de ingesta desde `runs/` hacia:

```text
database/raw_canonical
```

Ejemplo actual:

```yaml
build_groups:
  enabled: true
  input_runs_root: runs
  output_dir: database/raw_canonical

  use_latest_run_only: true

  deduplicate: true
  deduplicate_by:
    - instrument
    - station_id
    - measurement_date
    - measurement_time
    - group

  manifest: true

  groups:
    - Summary
    - Points
    - Sections
    - Gates

  concat_groups:
    - Summary

  sources:
    - flowtracker
    - molinete
    - nivus
```

### 10.1 enabled

Activa o desactiva la etapa.

### 10.2 input_runs_root

Raíz donde se buscan corridas:

```yaml
input_runs_root: runs
```

### 10.3 output_dir

Destino consolidado:

```yaml
output_dir: database/raw_canonical
```

### 10.4 use_latest_run_only

```yaml
use_latest_run_only: true
```

Cuando está en `true`, usa solo la corrida más reciente compatible por fuente/instrumento.

Ventaja: evita mezclar accidentalmente corridas viejas y nuevas.

Riesgo: si la corrida más reciente está incompleta, puede dejar fuera datos válidos de corridas anteriores.

### 10.5 include_runs y exclude_runs

Permiten controlar explícitamente qué runs usar o ignorar.

Estas listas esperan IDs de corrida, no rutas completas. El ID corresponde al nombre de la carpeta final del run, por ejemplo `20260501_120000`.

Ejemplo conceptual:

```yaml
include_runs:
  - "20260501_120000"
exclude_runs:
  - "20260425_090000"
```

Uso recomendado:

- `include_runs`: cuando se quiere consolidar una lista conocida de corridas;
- `exclude_runs`: cuando se quiere omitir una corrida defectuosa;
- no mezclar con `use_latest_run_only` sin revisar el comportamiento esperado.

### 10.6 deduplicate

```yaml
deduplicate: true
```

Activa eliminación de duplicados durante la consolidación.

### 10.7 deduplicate_by

Define las columnas usadas para identificar duplicados.

```yaml
deduplicate_by:
  - instrument
  - station_id
  - measurement_date
  - measurement_time
  - group
```

Riesgo: si la clave es demasiado amplia, puede eliminar datos válidos. Si es demasiado débil, puede conservar duplicados.

### 10.8 manifest

```yaml
manifest: true
```

Genera manifiestos en:

```text
database/raw_canonical/_manifests
```

Sirve para auditar qué runs y archivos participaron en la consolidación.

### 10.9 groups

Define grupos a consolidar:

```yaml
groups:
  - Summary
  - Points
  - Sections
  - Gates
```

### 10.10 concat_groups

Define qué grupos se concatenan en un archivo consolidado:

```yaml
concat_groups:
  - Summary
```

### 10.11 sources

Define instrumentos/fuentes a incluir:

```yaml
sources:
  - flowtracker
  - molinete
  - nivus
```

## 11. normalize

`normalize` convierte `database/raw_canonical` en tablas bajo esquema común.

Ejemplo actual:

```yaml
normalize:
  enabled: true
  registry_dir: configs/normalization
  input_dir: database/raw_canonical
  output_dir: database/normalized

  write_policy: overwrite

  groups:
    - Summary
    - Points
    - Sections
    - Gates

  concat_groups:
    - Summary
    - Points

  sources:
    - flowtracker
    - molinete
    - nivus
```

### 11.1 registry_dir

Carpeta con reglas YAML de normalización:

```text
configs/normalization
```

Archivos esperados:

```text
configs/normalization/flowtracker.yaml
configs/normalization/molinete.yaml
configs/normalization/nivus.yaml
```

### 11.2 input_dir

Entrada de normalize:

```text
database/raw_canonical
```

### 11.3 output_dir

Salida de normalize:

```text
database/normalized
```

### 11.4 write_policy

```yaml
write_policy: overwrite
```

Valores soportados:

| Valor | Qué hace | Cuándo usarlo |
| --- | --- | --- |
| `overwrite` | sobrescribe outputs existentes e informa la acción | desarrollo, reprocesamiento controlado |
| `fail_if_exists` | detiene la normalización si el output ya existe | producción, evitar reemplazos accidentales |

### 11.5 groups

Grupos que se intentan normalizar:

```yaml
groups:
  - Summary
  - Points
  - Sections
  - Gates
```

### 11.6 concat_groups

Grupos para los que se generan salidas concatenadas:

```yaml
concat_groups:
  - Summary
  - Points
```

### 11.7 sources

Instrumentos a normalizar:

```yaml
sources:
  - flowtracker
  - molinete
  - nivus
```

## 12. Archivos de normalización

Los YAML en `configs/normalization/` definen cómo mapear columnas de cada instrumento a un esquema común.

Ubicaciones actuales:

```text
configs/normalization/flowtracker.yaml
configs/normalization/molinete.yaml
configs/normalization/nivus.yaml
```

También existe:

```text
configs/specs/flowtracker.yaml
```

que se usa como especificación auxiliar de ingesta FlowTracker.

### 12.1 source

Usar cuando hay una columna única:

```yaml
station_id:
  source: station_id
```

### 12.2 sources

Usar cuando puede haber varias columnas alternativas:

```yaml
station_name:
  sources:
    - station_name
    - site_name
```

Aforix toma la primera disponible con datos.

### 12.3 columnas derivadas

Ejemplo conceptual:

```yaml
q_total_ls:
  from: q_total_m3s
  operation: multiply
  value: 1000
```

## 13. validation

La sección `validation` configura controles sobre `database/normalized`.

Ejemplo:

```yaml
validation:
  enabled: true
  strict: false
  input_dir: database/normalized
  output_dir: database/validation
```

### 13.1 traceability_columns

Columnas esperadas para trazabilidad:

```yaml
traceability_columns:
  - station_id
  - station_name
  - measurement_date
  - measurement_time
  - instrument
  - source_file
  - source_run_dir
  - run_id
```

### 13.2 keys

Clave base para identificar mediciones:

```yaml
keys:
  - instrument
  - station_id
  - measurement_date
  - measurement_time
```

### 13.3 checks

Chequeos activables:

```yaml
checks:
  required_columns: true
  duplicates: true
  completeness: true
  ranges: true
  hydraulic_consistency: true
```

### 13.4 required_columns

Define columnas obligatorias por grupo.

Ejemplo `Summary`:

```text
station_id
station_name
measurement_date
measurement_time
instrument
source_file
source_run_dir
run_id
q_total_m3s
q_total_ls
area_total_m2
```

Ejemplo `Points`:

```text
station_id
station_name
measurement_date
measurement_time
instrument
source_file
source_run_dir
run_id
point_index
distance_m
depth_m
area_m2
q_m3s
q_ls
```

### 13.5 completeness

Define columnas críticas que no deberían quedar vacías.

### 13.6 hydraulic_consistency

Define tolerancias entre agregados de `Points` y valores de `Summary`.

```yaml
hydraulic_consistency:
  q_tolerance_pct: 1.0
  area_tolerance_pct: 1.0
```

### 13.7 ranges

Define rangos aceptables para variables.

Ejemplo:

```yaml
ranges:
  Summary:
    area_total_m2:
      min: 0
    temperature_c:
      min: -5
      max: 45
```

## 14. export

Configura exportaciones generales.

```yaml
export:
  tables:
    enabled: true
    input_dir: database/normalized
    output_dir: outputs/tables

  excel:
    enabled: true
    input_dir: database/normalized
    output_dir: outputs/excel
```

Estas salidas trabajan preferentemente sobre `database/normalized`.

La exportación SIH tiene documentación específica:

```text
docs/SIH_EXPORT.md
docs/SIH_CONFIGURATION.md
docs/SIH_MATCHING.md
docs/SIH_TROUBLESHOOTING.md
```

## 15. external_sources

Define fuentes externas usadas por análisis.

```yaml
external_sources:
  model:
    raw_dir: database/external/raw/model
    normalized_dir: database/external/normalized/model

  dinagua:
    raw_dir: database/external/raw/dinagua
    normalized_dir: database/external/normalized/dinagua

  manual_stage:
    enabled: true
    raw_dir: data/external/manual_stage
    normalized_dir: database/external/normalized/manual_stage
```

### 15.1 model

Datos externos de modelo hidrológico.

### 15.2 dinagua

Datos externos de estaciones DINAGUA.

### 15.3 manual_stage

Datos manuales de altura/nivel usados por análisis caudal-altura.

## 16. analysis

La sección `analysis` configura módulos posteriores.

### 16.1 correlation

```yaml
analysis:
  correlation:
    output_root: runs/analysis_correlation
    default_ranking:
      - NV
      - FT
      - ML
```

Controla salidas, ranking de instrumentos y roles de variables para análisis de correlación.

Guía específica:

```text
docs/CORRELATION_GUIDE.md
```

### 16.2 quality_metrics

```yaml
quality_metrics:
  enabled: true
  input_dirs:
    normalized_root: database/normalized
    raw_canonical_root: database/raw_canonical
  output_root: runs/analysis_quality_metrics
```

Guía específica:

```text
docs/QUALITY_METRICS_GUIDE.md
```

### 16.3 section_profiles

Configura análisis de perfiles de sección.

Guía específica:

```text
docs/SECTION_PROFILES_ANALYSIS.md
```

### 16.4 stage_discharge

Configura análisis caudal-altura.

Guía específica:

```text
docs/STAGE_DISCHARGE_ANALYSIS.md
```

## 17. Auditoría del pipeline

Después de normalizar, se recomienda ejecutar:

```bash
python scripts/audit_pipeline_outputs.py
```

Windows CMD:

```bat
python scripts\audit_pipeline_outputs.py
```

El audit revisa:

- columnas esperadas;
- duplicados;
- consistencia hidráulica;
- consistencia de unidades;
- rangos básicos.

No reemplaza `aforix validate run`; lo complementa.

## 18. Flujo recomendado desde cero

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

## 19. Errores frecuentes

### 19.1 Aforix no encuentra archivos raw

Revisar:

```text
paths.raw_data_dir
ingest.<instrument>.raw_subdir
```

### 19.2 Falta station_id

Revisar:

- que el ID esté cargado en el campo correcto del instrumento;
- `metadata_policy.station_id.sources`;
- transformaciones como `remove_prefix` o `digits_only`.

### 19.3 Fechas u horas incorrectas

Revisar:

- `metadata_policy.measurement_date.normalize.input_formats`;
- `metadata_policy.measurement_time.normalize.input_formats`;
- que la salida final sea `YYYYMMDD` y `HHMMSS`.

### 19.4 build-groups mezcla corridas no deseadas

Revisar:

```yaml
use_latest_run_only
include_runs
exclude_runs
```

### 19.5 Aparecen duplicados

Revisar:

```yaml
deduplicate
deduplicate_by
```

Luego ejecutar audit.

### 19.6 normalize sobrescribe archivos

Revisar:

```yaml
write_policy: overwrite
```

Si se quiere prevenir sobrescritura:

```yaml
write_policy: fail_if_exists
```

### 19.7 El audit marca caudales negativos

No necesariamente es error. Los caudales negativos pueden representar dirección de flujo o situaciones hidráulicas específicas. Revisar caso por caso.

## 20. Checklist para usuario nuevo

- [ ] Instalé Aforix con `pip install -e .`.
- [ ] Revisé `configs/examples/main.yaml`.
- [ ] Coloqué archivos raw en `data/raw/FT`, `data/raw/ML` o `data/raw/NV`.
- [ ] Cargué correctamente el ID del punto en el instrumento.
- [ ] Cargué correctamente el nombre del punto en el instrumento.
- [ ] Revisé `metadata_policy` del instrumento.
- [ ] Ejecuté `aforix config-check`.
- [ ] Ejecuté la ingesta correspondiente.
- [ ] Revisé outputs en `runs/.../raw_canonical`.
- [ ] Ejecuté `aforix build-groups`.
- [ ] Revisé manifest en `database/raw_canonical/_manifests` si está habilitado.
- [ ] Ejecuté `aforix normalize run`.
- [ ] Ejecuté `python scripts/audit_pipeline_outputs.py`.
- [ ] Ejecuté `aforix validate run`.
- [ ] Revisé `database/normalized` y `database/validation`.

## 21. Recomendación final

Para usuarios nuevos, se recomienda empezar con un único instrumento y pocas mediciones. Una vez validado el flujo completo, agregar más instrumentos y campañas.

Cuando se cambie una política importante, como `metadata_policy`, `deduplicate_by` o `write_policy`, conviene volver a correr el pipeline completo y revisar audit/validation antes de exportar o analizar datos.
