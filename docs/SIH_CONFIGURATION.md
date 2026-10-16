# Configuración del módulo SIH

Esta guía documenta la configuración actual del módulo SIH de Aforix.

El archivo principal es:

```text
configs/sih/sih.yaml
```

La configuración es declarativa: el código no debería hardcodear IDs SIH, nombres de columnas SIH, columnas fuente, umbrales ni nombres de salida.

## 1. Estructura general de sih.yaml

El YAML tiene una clave superior obligatoria:

```yaml
sih:
  enabled: true
  inputs: ...
  output: ...
  lookup_files: ...
  datetime: ...
  selection: ...
  defaults: ...
  station_mapping: ...
  lookup_tables: ...
  instruments: ...
```

El cargador exige que exista una clave superior `sih` y que sea un mapping YAML.

## 2. inputs

```yaml
inputs:
  normalized_input_dir: database/normalized
  raw_canonical_input_dir: database/raw_canonical
  quality_input_dir: database/analysis/quality_metrics
```

| Campo | Uso actual |
| --- | --- |
| `normalized_input_dir` | raíz desde donde se leen tablas normalizadas `Summary`; también es la fuente principal del modo interactivo |
| `raw_canonical_input_dir` | raíz desde donde se leen tablas raw canonical `Summary` durante la exportación final |
| `quality_input_dir` | reservado para integración futura con métricas de calidad |

Actualmente el export usa `normalized_input_dir` y `raw_canonical_input_dir`. `quality_input_dir` existe en configuración, pero no se usa todavía para construir las filas SIH.

En modo interactivo, `normalized_input_dir` se usa para detectar automáticamente instrumentos, estaciones y mediciones disponibles.

## 3. output

```yaml
output:
  output_dir: outputs/sih
  delimiter: ","
  encoding: utf-8-sig
  output_names:
    actuaciones: "ID_{export_id}_actuacion_{station_id}_{YYYYMMDD}_{HHMMSS}.csv"
    aforos: "ID_{export_id}_aforo_{station_id}_{YYYYMMDD}_{HHMMSS}.csv"
```

| Campo | Descripción |
| --- | --- |
| `output_dir` | carpeta donde se escriben los CSV SIH, la metadata y el selection CSV temporal interactivo |
| `delimiter` | separador CSV |
| `encoding` | encoding de salida |
| `output_names.actuaciones` | plantilla de nombre para CSV de actuaciones |
| `output_names.aforos` | plantilla de nombre para CSV de aforos |

Variables disponibles en plantillas:

```text
export_id
station_id
YYYYMMDD
HHMMSS
```

El encoding por defecto es `utf-8-sig`, conveniente para abrir CSVs en Excel en Windows.

## 4. lookup_files

```yaml
lookup_files:
  instrumentos: configs/sih/instrumentos.csv
  tipos_aforos: configs/sih/tipos_aforos.csv
  instrumentos_rangos: configs/sih/instrumentos_rangos.csv
```

Estos archivos son leídos por el módulo al iniciar la exportación final.

El modo interactivo no usa los lookups para mostrar instrumentos y estaciones. El modo interactivo detecta opciones desde normalized. Sin embargo, después de generar el selection CSV temporal, el runner batch sí carga los lookups y los usa para resolver IDs SIH.

El código también define un default para:

```text
configs/sih/estaciones.csv
```

aunque el `sih.yaml` actual no lo declara explícitamente y el station mapping actual usa modo directo desde normalized.

## 5. datetime

```yaml
datetime:
  source_date_column: measurement_date
  source_time_column: measurement_time
  output_format: "%d/%m/%Y %H:%M:%S"
  filename_date_format: "%Y%m%d"
  filename_time_format: "%H%M%S"
```

| Campo | Uso |
| --- | --- |
| `source_date_column` | documenta columna fuente de fecha |
| `source_time_column` | documenta columna fuente de hora |
| `output_format` | formato usado para `fecha`, `fecha_inicio`, `fecha_fin` |
| `filename_date_format` | formato conceptual de fecha para nombres de archivo |
| `filename_time_format` | formato conceptual de hora para nombres de archivo |

En el código actual, la construcción de fecha/hora usa directamente `measurement_date` y `measurement_time` desde la fila normalizada o desde el selection CSV generado. El formato de salida se toma de `output_format`.

El modo interactivo normaliza fechas y horas antes de escribir el selection CSV temporal:

```text
2026-01-19 -> 20260119
14:18:00 -> 141800
94521 -> 094521
```

## 6. selection

```yaml
selection:
  default_mode: batch_file
  batch_file:
    enabled: true
    path: configs/sih/selection_template.csv
    columns:
      station_id: station_id
      measurement_date: measurement_date
      measurement_time: measurement_time
      instrument: instrument
      export_id: export_id
```

El modo batch usa el archivo indicado en `batch_file.path`, salvo que el usuario pase otro con `--selection-file`.

El archivo indicado debe contener estas columnas reales:

```text
station_id
measurement_date
measurement_time
instrument
export_id
```

La sección `columns` documenta el mapeo esperado, pero el código actual valida los nombres literales requeridos.

En modo interactivo, esta sección no define las opciones mostradas al usuario. El modo interactivo genera automáticamente un selection CSV temporal con las mismas columnas requeridas y luego lo pasa al mismo runner batch.

## 7. defaults

```yaml
defaults:
  empty_autogenerated_ids: true
  pendiente: false
  relevante: false
  id_perfil: null
```

En el código actual:

- `id`, `id_actuacion` e `id_perfil` salen vacíos en las filas generadas;
- `pendiente` y `relevante` se escriben como `False` en `sdh_actuaciones`.

La sección queda como referencia de comportamiento esperado y extensibilidad, pero no todos los valores son consumidos dinámicamente por el código actual.

## 8. station_mapping

```yaml
station_mapping:
  source:
    dataset: normalized
    table: Summary
    column: station_id
  mode: direct
```

El código actual resuelve `id_estacion` leyendo directamente la columna indicada, por defecto `station_id`, desde la medición normalizada.

Esto significa que el valor de `station_id` en normalized debe coincidir con el ID requerido por SIH o con el criterio definido por el usuario.

El modo interactivo también usa `station_id` para listar estaciones disponibles y construir el selection CSV temporal.

## 9. lookup_tables

```yaml
lookup_tables:
  instrumentos:
    file: instrumentos
    value_column: id
    match_columns:
      - marca
      - nro_serie
      - modelo
      - codigo
  tipos_aforos:
    file: tipos_aforos
    key_column: descripcion
    value_column: id
  instrumentos_rangos:
    file: instrumentos_rangos
    key_column: descripcion
    value_column: id
```

### 9.1 instrumentos

Define cómo resolver `id_instrumento`.

- `file: instrumentos` refiere al lookup cargado desde `lookup_files.instrumentos`.
- `value_column: id` indica qué columna devolver como ID SIH.
- `match_columns` define las columnas del lookup usadas para matching flexible.

Las columnas configuradas actualmente son:

```text
marca
nro_serie
modelo
codigo
```

### 9.2 tipos_aforos

Resuelve `id_tipo_aforo` cuando no se usa un valor directo.

Actualmente los instrumentos configurados resuelven `id_tipo_aforo` de forma declarativa con las claves adoptadas:

```text
FlowTracker -> VADEO -> 57
Molinete    -> VADEO -> 57
Nivus       -> VADEO -> 57
M9          -> BOTE  -> 59
```

Los instrumentos configurados tienen `id_tipo_actuacion: 4`. M9 usa las asociaciones declarativas `BOTE` y `ADCP`. El catálogo incluye la fila `503,SonTek,4980,M9,M9` para el equipo usado en la aceptación local; cada M9 con otro número de serie requiere su propia fila SIH.

### 9.3 instrumentos_rangos

Resuelve `id_instrumentos_rangos` usando las claves adoptadas:

```text
FlowTracker -> Velocimetro -> 11
Molinete    -> Velocimetro -> 11
Nivus       -> Acustico    -> 10
M9          -> ADCP        -> 12
```

Estas asociaciones son decisiones declarativas del proyecto. No deben implementarse como alias semánticos hardcodeados en Python.

## 10. instruments

Cada instrumento bajo `sih.instruments` define cómo mapear datos Aforix hacia SIH.

Instrumentos actuales:

```text
flowtracker
molinete
nivus
m9
```

`m9` está configurado como `enabled: true`. La fila SIH del M9 debe coincidir con marca, número de serie y modelo presentes en el Summary raw canonical.

Para el M9, `radio_hidraulico` se toma de `Summary.hydraulic_radius_m`, calculado como área reportada dividida por el perímetro mojado del perfil de profundidades. El método y el supuesto de interpolación lineal de las distancias a las márgenes se registran en `hydraulic_radius_method`. La guía de DINAGUA recomienda QRev para M9; Aforix calcula aquí un IVE análogo sobre sus muestras de 1 s y lo identifica como `IVE_ADAPTADO_M9`, sin atribuirle equivalencia con QRev. La salida SIH agrega `incertidumbre_IVE` (fracción relativa), `error_IVE` (m³/s usando Q mid-section) y `calidad_IVE`. `sih_export_metadata.csv` conserva método y estado del cálculo.

El modo interactivo recorre esta sección y solo intenta cargar instrumentos con `enabled: true`.

### 10.1 Campos comunes

| Campo | Descripción |
| --- | --- |
| `enabled` | habilita o deshabilita el instrumento; también controla si aparece en modo interactivo |
| `normalized_name` | nombre esperado en datos normalizados |
| `id_tipo_actuacion` | ID directo de tipo de actuación |
| `tipo_aforo_lookup` | clave para lookup de tipos de aforo |
| `instrumentos_rangos_lookup` | clave para lookup de rangos de instrumento |
| `instrument_lookup_fields` | mapeo para resolver `id_instrumento` |
| `raw_canonical_fields` | campos SIH que vienen desde raw canonical |
| `normalized_fields` | campos SIH que vienen desde normalized |
| `quality` | configuración futura de métricas de calidad |

## 11. instrument_lookup_fields

Ejemplo FlowTracker:

```yaml
instrument_lookup_fields:
  marca: null
  nro_serie: null
  modelo: instrument
  codigo: null
```

Ejemplo Molinete:

```yaml
instrument_lookup_fields:
  marca: null
  nro_serie: helice
  modelo: molinete
  codigo: null
```

Ejemplo Nivus:

```yaml
instrument_lookup_fields:
  marca: null
  nro_serie: null
  modelo: instrument
  codigo: null
```

Cada clave (`marca`, `nro_serie`, `modelo`, `codigo`) corresponde a una columna del lookup `instrumentos.csv`.

Cada valor corresponde a una columna del raw canonical `Summary`. Si el valor es `null`, ese criterio se ignora.

## 12. raw_canonical_fields

Define qué campos SIH continúan tomándose desde raw canonical. Los datos de operador, escalas y fechas de inicio/fin se toman ahora desde el `Summary` normalizado.

Ejemplo Molinete:

```yaml
raw_canonical_fields:
  id_operador: null
  lectura_escala: null
  escala_inicio: null
  escala_fin: null
  escala_media: escala_media_m
  observaciones: observaciones
  radio_hidraulico: radio_hidraulico_m
```

Si el raw canonical no existe o una columna no existe, el campo resultante queda vacío.

Campos que siguen usando raw canonical:

```text
escala_media
observaciones
radio_hidraulico
```

## 13. normalized_fields

Define qué campos SIH se toman desde normalized.

Ejemplo:

```yaml
normalized_fields:
  ancho: width_total_m
  caudal: q_total_m3s
  profundidad: depth_mean_m
  seccion: area_total_m2
  velocidad_media: velocity_mean_m_s
  id_operador: operador
  lectura_escala: escala_inicio
  escala_inicio: escala_inicio
  escala_fin: escala_fin
  fecha_inicio: fecha_inicio
  fecha_fin: fecha_fin
```

El código actual usa para `sdh_aforos`:

```text
ancho
caudal
profundidad
seccion
velocidad_media
escala_inicio
escala_fin
fecha_inicio
fecha_fin
```

`fecha_inicio` se crea durante la normalización. En FlowTracker y Molinete se combina `measurement_date` con `measurement_time`; en Nivus se copia `stime` desde el raw. `fecha_fin` se normaliza así:

- FlowTracker: `Fecha` y `Hora` de la última fila de Datos complementarios. Si hay una sola fila, se usa para ambos extremos de escala. Si no existe la tabla, los campos que dependen de ella se exportan como `S/D`.
- Molinete: `measurement_date` combinado con `end_time`. Si `Esc. Fin.:` no existe o contiene `-`, `escala_fin` toma `escala_inicio`.
- Nivus: el `etime` del nivel general del aforo. `escala_inicio`, `escala_fin` y `operador` quedan vacíos y configurables para el futuro.

En la actuación, `lectura_escala` toma `escala_inicio`. `id_operador` se formatea para SIH: los nombres de dos partes quedan como iniciales mayúsculas (`TIAGO POREN` → `TP`), las abreviaturas en mayúsculas conservan sus dos primeras letras (`IPAMBC` → `IP`), los valores separados por guion bajo conservan el primer componente (`MV_HG_RR` → `MV`), los nombres separados por punto quedan como iniciales (`M.Reyes` → `MR`) y los demás formatos conservan el primer token.

## 14. quality

Ejemplo Nivus:

```yaml
quality:
  enabled: true
  source: quality_metrics
  parameter: "CG(%)"
  thresholds:
    bueno:
      min: 70
    regular:
      min: 40
      max_lt: 70
    malo:
      max_lt: 40
```

Según el estado actual del código, esta sección está preparada para integración futura, pero no se usa todavía para poblar `nivel_confiabilidad` ni otros campos de salida.

Esto está registrado como MAIN-022. Antes de implementar la integración debe definirse el contrato SIH de `nivel_confiabilidad` (por ejemplo, si espera una etiqueta, un ID o un valor). No se debe inferir esa semántica únicamente a partir del nombre del campo.

## 15. Cómo agregar un nuevo instrumento

Para agregar un instrumento nuevo:

1. Confirmar que existe en normalized y raw canonical.
2. Agregar una entrada en `sih.instruments`.
3. Definir `enabled: true` si debe aparecer en modo interactivo.
4. Definir `normalized_name`.
5. Definir `id_tipo_actuacion`, `tipo_aforo_lookup` e `instrumentos_rangos_lookup`.
6. Configurar `instrument_lookup_fields`.
7. Configurar `raw_canonical_fields`.
8. Configurar `normalized_fields`.
9. Agregar filas necesarias en lookups CSV.
10. Probarlo en modo interactivo para verificar que aparece en instrumentos disponibles.
11. Agregar filas de prueba en `selection_template.csv` para modo batch.
12. Ejecutar `aforix export sih` y revisar `sih_export_metadata.csv`.

## 16. Recomendaciones de formato futuro

El código actual tolera algunas variantes de fecha/hora al buscar mediciones. Sin embargo, para reducir errores se recomienda unificar:

```text
measurement_date -> YYYYMMDD
measurement_time -> HHMMSS
```

Esto aplica especialmente a `selection_template.csv`, al selection CSV temporal generado por modo interactivo y a futuras salidas normalizadas de Aforix.
