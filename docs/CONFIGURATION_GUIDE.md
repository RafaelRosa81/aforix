# Guía de configuración de Aforix

Esta guía explica cómo preparar los datos, configurar el sistema y ejecutar el pipeline de Aforix desde la ingesta de archivos raw hasta la normalización. Está pensada para usuarios que no conocen la estructura interna del proyecto.

---

## 1. Objetivo

Aforix procesa datos de aforos provenientes de distintos instrumentos de medición, actualmente:

- FlowTracker
- Molinete
- Nivus
- M9, pendiente de implementación completa

El objetivo del sistema es transformar archivos originales de instrumentos en tablas normalizadas, trazables y comparables entre instrumentos.

El pipeline general es:

```text
archivos raw
  ↓
ingest
  ↓
raw_canonical
  ↓
build-groups
  ↓
normalize
  ↓
validation / export / analysis
```

---

## 2. Qué debe preparar el usuario

Antes de ejecutar Aforix, el usuario debe preparar:

1. Una carpeta con archivos raw de instrumentos.
2. Un archivo de configuración YAML, normalmente `configs/examples/main.yaml`.
3. Los archivos de normalización YAML dentro de `configs/normalization/`.
4. Un entorno Python con Aforix instalado.

El usuario no debería modificar el código fuente para correr un proyecto normal.

---

## 3. Estructura general de carpetas

La configuración de ejemplo define:

```yaml
paths:
  raw_data_dir: data/raw
  runs_root: runs
  database_root: database
```

Por defecto, se espera esta estructura local:

```text
aforix/
├── configs/
│   ├── examples/
│   │   └── main.yaml
│   └── normalization/
│       ├── flowtracker.yaml
│       ├── molinete.yaml
│       └── nivus.yaml
├── data/
│   └── raw/
│       ├── FT/
│       ├── ML/
│       ├── NV/
│       └── M9/
├── runs/
├── database/
└── outputs/
```

Las carpetas `runs/`, `database/`, `outputs/` y `data/` son generadas o locales. No deberían versionarse en Git.

---

## 4. Dónde colocar los archivos raw

La carpeta base para datos raw se define en:

```yaml
paths:
  raw_data_dir: data/raw
```

Dentro de esa carpeta, cada instrumento tiene una subcarpeta definida en la sección `ingest`:

```yaml
ingest:
  flowtracker:
    raw_subdir: FT

  molinete:
    raw_subdir: ML

  nivus:
    raw_subdir: NV

  m9:
    raw_subdir: M9
```

Por lo tanto, el usuario debe colocar los datos en:

```text
data/raw/FT/   → archivos FlowTracker
data/raw/ML/   → archivos Molinete
data/raw/NV/   → archivos Nivus
data/raw/M9/   → archivos M9
```

---

## 5. Información mínima esperada por instrumento

Aforix necesita identificar cada medición mediante claves comunes:

```text
station_id
station_name
measurement_date
measurement_time
instrument
```

Estas columnas se generan durante la ingesta o se extraen de los archivos originales.

### 5.1 station_id

`station_id` es el identificador del punto de aforo, por ejemplo:

```text
P1
P8
P11
P911
```

Debe ser único dentro de una campaña o red de medición.

### 5.2 station_name

`station_name` es un nombre descriptivo del punto, por ejemplo:

```text
Chamizo
San José
Pintado Berrondo
```

Puede no existir en todos los instrumentos. Cuando existe, se conserva para trazabilidad y salidas de usuario.

### 5.3 measurement_date y measurement_time

La fecha y hora normalmente se extraen automáticamente desde el archivo original del instrumento.

El formato normalizado esperado es:

```text
measurement_date → YYYYMMDD
measurement_time → HHMMSS
```

Ejemplo:

```text
20251215
124600
```

---

## 6. Requisitos por instrumento

### 6.1 FlowTracker

Los archivos FlowTracker deben colocarse en:

```text
data/raw/FT/
```

Durante la ingesta, Aforix espera poder obtener:

- `station_id`
- `site_name` o `station_name`
- fecha y hora de inicio
- caudal total
- área total
- ancho total
- velocidad media
- profundidad media
- temperatura, si está disponible

En el YAML de normalización, `station_name` puede venir desde:

```yaml
station_name:
  sources:
    - station_name
    - site_name
```

El caudal total se normaliza desde columnas como:

```yaml
q_total_m3s:
  sources:
    - total_discharge_m3_s
    - total_discharge_m3s
    - discharge_m3_s
    - caudal_total_m3_s
```

Esto significa que el usuario no necesita que el archivo raw tenga exactamente los nombres canónicos, pero sí debe existir la información para que el ingest la extraiga.

---

### 6.2 Molinete

Los archivos Molinete deben colocarse en:

```text
data/raw/ML/
```

La configuración actual indica:

```yaml
molinete:
  raw_subdir: ML
  sheet_name: Datos
```

Por lo tanto, si el archivo es Excel, la hoja esperada por defecto es `Datos`.

Aforix espera poder obtener:

- `station_id`
- `nombre` o `station_name`
- fecha y hora de medición
- caudal total en m³/s
- área
- ancho
- profundidad media
- velocidad media
- puntos o verticales de medición

En el YAML de normalización, `station_name` puede venir desde:

```yaml
station_name:
  sources:
    - station_name
    - nombre
```

El caudal total se normaliza desde:

```yaml
q_total_m3s:
  sources:
    - q_total_m3s
    - q_m3s
    - total_discharge_m3s
    - total_discharge_m3_s
```

---

### 6.3 Nivus

Los archivos Nivus deben colocarse en:

```text
data/raw/NV/
```

Aforix espera obtener:

- `station_id`
- `name` o `station_name`
- fecha y hora de medición
- caudal en l/s
- área en m²
- ancho
- profundidad media
- velocidad media
- temperatura
- Points
- Sections
- Gates

En Nivus, el caudal suele venir en litros por segundo:

```yaml
q_total_ls:
  sources:
    - q_total_ls
    - total_discharge_ls
    - q [l/s]
```

Aforix deriva `q_total_m3s` dividiendo por 1000:

```yaml
q_total_m3s:
  operation: divide
  value: 1000
```

Además, para `Points`, Aforix puede enriquecer la información usando `Sections`. Esto permite reconstruir por punto:

- área
- caudal parcial
- porcentaje del caudal total

---

### 6.4 M9

La carpeta M9 está prevista en la configuración:

```yaml
m9:
  enabled: true
  raw_subdir: M9
```

Sin embargo, la ingesta M9 todavía debe considerarse pendiente o experimental hasta que el adaptador esté completamente implementado y validado.

---

## 7. Archivo principal de configuración: main.yaml

El archivo principal controla rutas, instrumentos activos y etapas del pipeline.

Ejemplo de estructura:

```yaml
project:
  name: aforix
  description: Pipeline para procesamiento de datos de aforos
  timezone: America/Montevideo

paths:
  raw_data_dir: data/raw
  runs_root: runs
  database_root: database

ingest:
  flowtracker:
    enabled: true
    raw_subdir: FT

  molinete:
    enabled: true
    raw_subdir: ML

  nivus:
    enabled: true
    raw_subdir: NV
```

### 7.1 project

Define metadatos generales del proyecto.

### 7.2 paths

Define carpetas principales:

| Campo | Significado |
|---|---|
| `raw_data_dir` | carpeta donde el usuario coloca archivos raw |
| `runs_root` | carpeta donde se guardan ejecuciones |
| `database_root` | carpeta donde se guarda la base procesada |

### 7.3 ingest

Define instrumentos activos y subcarpetas raw.

### 7.4 build_groups

Define cómo se construye `database/raw_canonical`.

Ejemplo:

```yaml
build_groups:
  enabled: true
  input_runs_root: runs
  output_dir: database/raw_canonical
```

### 7.5 normalize

Define dónde están los datos raw canonical, dónde guardar normalizados y dónde buscar los YAML de normalización.

```yaml
normalize:
  enabled: true
  registry_dir: configs/normalization
  input_dir: database/raw_canonical
  output_dir: database/normalized
```

### 7.6 validation

Define chequeos de calidad y consistencia.

### 7.7 export

Define salidas de tablas y Excel.

---

## 8. YAML de normalización

Los archivos en:

```text
configs/normalization/
```

definen cómo convertir columnas crudas o raw canonical a columnas canónicas.

Ejemplo:

```yaml
instrument: flowtracker

tables:
  Summary:
    columns:
      station_id:
        source: station_id
        dtype: string

      q_total_m3s:
        sources:
          - total_discharge_m3_s
          - discharge_m3_s
        dtype: float
```

### 8.1 source vs sources

Usar `source` cuando hay una sola columna posible:

```yaml
station_id:
  source: station_id
```

Usar `sources` cuando puede haber varias alternativas:

```yaml
station_name:
  sources:
    - station_name
    - site_name
```

Aforix toma la primera columna disponible con datos.

### 8.2 derived

Permite crear columnas derivadas.

Ejemplo:

```yaml
q_total_ls:
  from: q_total_m3s
  operation: multiply
  value: 1000
```

### 8.3 required

Define columnas obligatorias. Si faltan, la normalización o validación debe reportarlo.

### 8.4 transforms

Aplica transformaciones comunes:

```yaml
transforms:
  - name: strip_strings
  - name: numeric_commas_to_dots
  - name: enforce_dtypes
```

### 8.5 qc

Define reglas simples de calidad, por ejemplo valores no negativos:

```yaml
qc:
  non_negative:
    - q_total_m3s
    - area_total_m2
```

---

## 9. Pipeline de uso

### 9.1 Verificar configuración

```bash
aforix config-check -c configs/examples/main.yaml
```

### 9.2 Ingestar datos

```bash
aforix ingest flowtracker -c configs/examples/main.yaml
aforix ingest molinete -c configs/examples/main.yaml
aforix ingest nivus -c configs/examples/main.yaml
```

### 9.3 Construir raw canonical

```bash
aforix build-groups -c configs/examples/main.yaml
```

Esto genera:

```text
database/raw_canonical/
├── flowtracker/
├── molinete/
└── nivus/
```

### 9.4 Normalizar

```bash
aforix normalize run -c configs/examples/main.yaml
```

Esto genera:

```text
database/normalized/
├── flowtracker/
├── molinete/
├── nivus/
├── Summary.csv
└── Points.csv
```

### 9.5 Validar

```bash
aforix validate run -c configs/examples/main.yaml
```

Esto genera reportes en:

```text
database/validation/
```

### 9.6 Exportar tablas

Modo interactivo:

```bash
aforix export tables -c configs/examples/main.yaml --interactive
```

Modo avanzado:

```bash
aforix export tables -c configs/examples/main.yaml \
  --table Summary \
  --instrument all \
  --parameters q_total_m3s q_total_ls area_total_m2 \
  --grouping monthly \
  --format xlsx
```

---

## 10. Outputs principales

### 10.1 runs/

Contiene registros y salidas de cada ejecución.

Ejemplo:

```text
runs/ingest_flowtracker/<timestamp>/
runs/normalize/<timestamp>/
runs/validate/<timestamp>/
```

### 10.2 database/raw_canonical/

Contiene datos extraídos y organizados por instrumento.

### 10.3 database/normalized/

Contiene datos normalizados bajo un esquema común.

### 10.4 database/validation/

Contiene reportes de validación.

### 10.5 outputs/

Contiene salidas exportadas para usuario.

---

## 11. Errores frecuentes

### 11.1 La configuración no encuentra los datos raw

Revisar:

```yaml
paths:
  raw_data_dir: data/raw
```

y las subcarpetas:

```yaml
ingest:
  flowtracker:
    raw_subdir: FT
```

### 11.2 Falta station_id

Verificar que el archivo raw o la estructura de carpetas permita identificar el punto de aforo.

### 11.3 No aparece station_name

Puede ser normal si el instrumento no provee nombre del punto. Lo importante es que `station_id` esté completo.

### 11.4 Fechas u horas mal formateadas

El formato final esperado es:

```text
YYYYMMDD
HHMMSS
```

### 11.5 Nivus no reconstruye bien Points

Revisar que existan `Points` y `Sections` correspondientes. Para algunos cálculos, Aforix usa `Sections` para enriquecer `Points`.

---

## 12. Checklist para usuario nuevo

Antes de correr el sistema:

- [ ] Instalé Aforix en el entorno Python.
- [ ] Preparé `configs/examples/main.yaml`.
- [ ] Coloqué archivos raw en `data/raw/FT`, `data/raw/ML`, `data/raw/NV` o `data/raw/M9`.
- [ ] Verifiqué que cada medición tenga un `station_id`.
- [ ] Revisé que el instrumento tenga fecha y hora de medición.
- [ ] Ejecuté `aforix config-check`.
- [ ] Ejecuté la ingesta correspondiente.
- [ ] Ejecuté `aforix build-groups`.
- [ ] Ejecuté `aforix normalize run`.
- [ ] Ejecuté `aforix validate run`.
- [ ] Revisé los outputs en `database/normalized` y `database/validation`.

---

## 13. Recomendación final

Para usuarios nuevos, se recomienda empezar con un único instrumento y pocas mediciones. Una vez validado el flujo completo, se pueden agregar más instrumentos y campañas.
