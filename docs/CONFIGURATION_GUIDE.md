# Guía de configuración de Aforix

Esta guía explica cómo preparar los datos, configurar el sistema y ejecutar el pipeline de Aforix. Está pensada para usuarios que no conocen la estructura interna del proyecto.

## 1. Objetivo

Aforix procesa datos de aforos provenientes de distintos instrumentos de medición:

- FlowTracker
- Molinete
- Nivus
- M9 / ADCP, pendiente hasta analizar archivos base

El objetivo es transformar archivos originales de instrumentos en tablas normalizadas, trazables y comparables entre instrumentos.

Pipeline general:

```text
raw -> ingest -> runs -> build-groups -> database/raw_canonical -> normalize -> database/normalized -> validate/export/analysis
```

## 2. Qué debe preparar el usuario

Antes de ejecutar Aforix, el usuario debe preparar:

1. Una carpeta con archivos raw de instrumentos.
2. Un archivo de configuración YAML, normalmente `configs/examples/main.yaml`.
3. Los archivos de normalización YAML dentro de `configs/normalization/`.
4. Un entorno Python con Aforix instalado.

El usuario no debería modificar el código fuente para correr un proyecto normal.

## 3. Estructura general de carpetas

La configuración de ejemplo define:

```yaml
paths:
  raw_data_dir: data/raw
  runs_root: runs
  database_root: database
```

Estructura local esperada:

```text
aforix/
├── configs/
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

Las carpetas `data/`, `runs/`, `database/` y `outputs/` son locales o generadas por el pipeline. No deberían versionarse en Git.

## 4. Dónde colocar los archivos raw

La carpeta base para datos raw se define en:

```yaml
paths:
  raw_data_dir: data/raw
```

Cada instrumento usa una subcarpeta definida en `ingest`:

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

Por lo tanto:

```text
data/raw/FT/   -> archivos FlowTracker
data/raw/ML/   -> archivos Molinete
data/raw/NV/   -> archivos Nivus
data/raw/M9/   -> archivos M9
```

## 5. Información mínima esperada por instrumento

Aforix necesita identificar cada medición mediante claves comunes:

```text
station_id
station_name
measurement_date
measurement_time
instrument
```

### 5.1 station_id

`station_id` es el identificador corto y estable del punto de aforo.

Ejemplos:

```text
P1
P8
P11
P911
```

Debe ser consistente entre instrumentos y campañas.

### 5.2 station_name

`station_name` es un nombre descriptivo del punto.

Ejemplos:

```text
Chamizo
San José
Pintado Berrondo
```

Cuando existe, se conserva para trazabilidad y salidas de usuario.

### 5.3 measurement_date y measurement_time

La fecha y hora normalmente se extraen automáticamente desde el archivo original del instrumento.

Formato normalizado esperado:

```text
measurement_date -> YYYYMMDD
measurement_time -> HHMMSS
```

### 5.4 Dónde cargar station_id y station_name en cada instrumento

El usuario debe cargar el ID y el nombre del punto durante la medición o en la planilla propia del instrumento. Esto evita problemas de trazabilidad, duplicados y errores al unir datos entre instrumentos.

| Instrumento | `station_id` / ID del punto | `station_name` / nombre del punto |
| --- | --- | --- |
| FlowTracker | `File_Name` / nombre del fichero | `Site_Name` / nombre del punto de aforo |
| Molinete | `ESTACION Nº:` | `NOMBRE:` |
| Nivus | `Número de referencia` | `Nombre del lugar de medición` |
| M9 | Pendiente hasta analizar archivos base | Pendiente hasta analizar archivos base |

Ejemplo recomendado:

| Campo | Valor |
| --- | --- |
| ID del punto | `P11` |
| Nombre del punto | `Arroyo San José - Punto 11` |

Usar siempre el mismo identificador para el mismo punto. Evitar variantes como `P11`, `P-11`, `Punto 11` y `11` para representar el mismo sitio, porque pueden ser interpretadas como puntos distintos.

## 6. Requisitos por instrumento

### 6.1 FlowTracker

Los archivos FlowTracker deben colocarse en:

```text
data/raw/FT/
```

Durante la ingesta, Aforix espera poder obtener:

- `station_id`
- `station_name` o `site_name`
- fecha y hora de inicio
- caudal total
- área total
- ancho total
- velocidad media
- profundidad media
- temperatura, si está disponible

En FlowTracker, cargar el ID del punto como `File_Name` y el nombre del punto como `Site_Name`.

### 6.2 Molinete

Los archivos Molinete deben colocarse en:

```text
data/raw/ML/
```

Si el archivo es Excel, la hoja esperada por defecto puede definirse en la configuración, por ejemplo:

```yaml
molinete:
  raw_subdir: ML
  sheet_name: CALCULO
```

En Molinete, cargar el ID del punto en `ESTACION Nº:` y el nombre del punto en `NOMBRE:`.

### 6.3 Nivus

Los archivos Nivus deben colocarse en:

```text
data/raw/NV/
```

En Nivus, cargar el ID del punto en `Número de referencia` y el nombre del punto en `Nombre del lugar de medición`.

En Nivus, los `Points` pueden enriquecerse usando información de `Sections` para reconstruir área, caudal parcial y porcentaje del caudal total.

### 6.4 M9

La carpeta M9 está prevista en la configuración:

```yaml
m9:
  enabled: true
  raw_subdir: M9
```

La forma correcta de cargar `station_id` y `station_name` para M9 queda pendiente hasta analizar el formato de los archivos base y definir el adaptador de ingesta correspondiente.

## 7. Archivo principal de configuración: main.yaml

El archivo principal controla rutas, instrumentos activos y etapas del pipeline.

Ejemplo:

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

### 7.1 paths

| Campo | Significado |
| --- | --- |
| `raw_data_dir` | carpeta donde el usuario coloca archivos raw |
| `runs_root` | carpeta donde se guardan ejecuciones |
| `database_root` | carpeta donde se guarda la base procesada |

### 7.2 ingest

Define instrumentos activos y subcarpetas raw.

### 7.3 build_groups

Define cómo se construye `database/raw_canonical`.

### 7.4 normalize

Define dónde están los datos raw canonical, dónde guardar normalizados y dónde buscar los YAML de normalización.

### 7.5 validation

Define chequeos de calidad y consistencia.

### 7.6 export

Define salidas de tablas y Excel.

## 8. YAML de normalización

Los archivos en `configs/normalization/` definen cómo convertir columnas crudas o raw canonical a columnas normalizadas.

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

También pueden definirse columnas derivadas, por ejemplo:

```yaml
q_total_ls:
  from: q_total_m3s
  operation: multiply
  value: 1000
```

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

### 9.4 Normalizar

```bash
aforix normalize run -c configs/examples/main.yaml
```

### 9.5 Validar

```bash
aforix validate run -c configs/examples/main.yaml
```

### 9.6 Exportar tablas

```bash
aforix export tables -c configs/examples/main.yaml --interactive
```

## 10. Outputs principales

- `runs/`: registros y salidas de cada ejecución.
- `database/raw_canonical/`: datos extraídos y organizados por instrumento.
- `database/normalized/`: datos normalizados bajo un esquema común.
- `database/validation/`: reportes de validación.
- `outputs/`: salidas exportadas para usuario.

## 11. Errores frecuentes

### 11.1 La configuración no encuentra los datos raw

Revisar `paths.raw_data_dir` y las subcarpetas configuradas en `ingest`.

### 11.2 Falta station_id

Verificar que el ID del punto esté cargado en el campo correcto del instrumento.

### 11.3 No aparece station_name

Verificar que el nombre del punto esté cargado en el campo correcto del instrumento. Si el instrumento no lo provee, lo importante es conservar un `station_id` completo y consistente.

### 11.4 Fechas u horas mal formateadas

El formato final esperado es `YYYYMMDD` para fechas y `HHMMSS` para horas.

### 11.5 Nivus no reconstruye bien Points

Revisar que existan `Points` y `Sections` correspondientes. Para algunos cálculos, Aforix usa `Sections` para enriquecer `Points`.

## 12. Checklist para usuario nuevo

- [ ] Instalé Aforix en el entorno Python.
- [ ] Preparé `configs/examples/main.yaml`.
- [ ] Coloqué archivos raw en la subcarpeta correspondiente.
- [ ] Cargué correctamente el ID del punto en el instrumento.
- [ ] Cargué correctamente el nombre del punto en el instrumento.
- [ ] Ejecuté `aforix config-check`.
- [ ] Ejecuté la ingesta correspondiente.
- [ ] Ejecuté `aforix build-groups`.
- [ ] Ejecuté `aforix normalize run`.
- [ ] Ejecuté `aforix validate run`.
- [ ] Revisé los outputs en `database/normalized` y `database/validation`.

## 13. Recomendación final

Para usuarios nuevos, se recomienda empezar con un único instrumento y pocas mediciones. Una vez validado el flujo completo, se pueden agregar más instrumentos y campañas.
