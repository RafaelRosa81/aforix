# Aforix

Aforix es una biblioteca y herramienta de línea de comandos en Python para procesar datos de aforos provenientes de distintos instrumentos de medición.

El objetivo es construir un pipeline **consistente, trazable e independiente del instrumento** para transformar archivos originales de campo en datos normalizados, validables y listos para análisis.

Instrumentos actualmente contemplados:

- FlowTracker
- Molinete
- Nivus
- M9, previsto pero pendiente de implementación completa

---

## Estado actual

Aforix cuenta actualmente con:

- Ingesta de datos FlowTracker
- Ingesta de datos Molinete
- Ingesta de datos Nivus
- Construcción de base `raw_canonical`
- Normalización mediante registry YAML
- Validación de datasets normalizados
- Exportación interactiva y avanzada de tablas
- Documentación de arquitectura y configuración

---

## Documentación principal

Para usuarios nuevos, comenzar por:

- [Guía de configuración](docs/CONFIGURATION_GUIDE.md): cómo preparar carpetas, archivos raw, YAML y ejecutar el pipeline.
- [Arquitectura del proyecto](docs/ARCHITECTURE.md): diseño general, módulos y flujo de datos.
- [AGENTS.md](AGENTS.md): reglas de trabajo para agentes/Codex y desarrollo asistido.

---

## Pipeline general

El flujo principal es:

```text
archivos raw
   ↓
ingest
   ↓
runs/<etapa>/<timestamp>/outputs
   ↓
build-groups
   ↓
database/raw_canonical
   ↓
normalize
   ↓
database/normalized
   ↓
validate / export / analysis
```

La idea central es que cada instrumento pueda tener su propio formato de origen, pero que el resultado normalizado use columnas comunes como:

```text
station_id
station_name
measurement_date
measurement_time
instrument
q_total_m3s
q_total_ls
area_total_m2
```

---

## Estructura del proyecto

```text
src/aforix/
├── analysis/          # Funciones de análisis hidrológico/estadístico
├── cli/               # Interfaz de línea de comandos Typer
├── config/            # Carga y validación de configuración
├── database/          # Consolidación de bases locales
├── export/            # Exportación de resultados y tablas
├── filters/           # Filtros sobre grupos de datos
├── groups/            # Construcción de raw_canonical
├── ingest/            # Lectura de archivos por instrumento
├── normalize/         # Normalización mediante registry YAML
├── runs/              # Manejo de carpetas de ejecución
└── validation/        # Validación de datasets normalizados
```

Carpetas locales generadas o usadas por el pipeline:

```text
data/                  # Archivos raw locales del usuario
runs/                  # Ejecuciones trazables del pipeline
database/
├── raw_canonical/     # Datos extraídos y organizados por instrumento
├── normalized/        # Datos normalizados bajo esquema común
└── validation/        # Reportes de validación
outputs/               # Exportaciones para usuario
```

Estas carpetas no deberían versionarse en Git.

---

## Instalación

Desde la raíz del repositorio:

```bash
pip install -e .
```

Activar entorno, si se usa Conda:

```bash
conda activate aforix
```

Verificar que el CLI esté disponible:

```bash
aforix --help
```

---

## Configuración

El archivo principal de configuración es:

```text
configs/examples/main.yaml
```

Define, entre otras cosas:

- rutas principales (`data/raw`, `runs`, `database`)
- instrumentos habilitados
- subcarpetas raw por instrumento
- grupos a construir
- registry de normalización
- validaciones
- salidas de exportación

Ejemplo:

```yaml
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

Antes de ejecutar el pipeline, revisar la guía completa:

```text
docs/CONFIGURATION_GUIDE.md
```

---

## Datos raw

Por defecto, los archivos originales deben colocarse en:

```text
data/raw/FT/   # FlowTracker
data/raw/ML/   # Molinete
data/raw/NV/   # Nivus
data/raw/M9/   # M9, pendiente/experimental
```

Cada medición debe poder identificarse mediante:

```text
station_id
station_name, si existe
measurement_date
measurement_time
instrument
```

La fecha y hora normalmente se extraen automáticamente desde el archivo original del instrumento.

---

## Comandos principales

### Validar configuración

```bash
aforix config-check -c configs/examples/main.yaml
```

### Ingestar datos

```bash
aforix ingest flowtracker -c configs/examples/main.yaml
aforix ingest molinete -c configs/examples/main.yaml
aforix ingest nivus -c configs/examples/main.yaml
```

### Construir raw_canonical

```bash
aforix build-groups -c configs/examples/main.yaml
```

Salida principal:

```text
database/raw_canonical/
├── flowtracker/
├── molinete/
└── nivus/
```

### Normalizar

```bash
aforix normalize run -c configs/examples/main.yaml
```

Salidas principales:

```text
database/normalized/
├── flowtracker/
├── molinete/
├── nivus/
├── Summary.csv
└── Points.csv
```

### Validar

```bash
aforix validate run -c configs/examples/main.yaml
```

Salida principal:

```text
database/validation/
```

### Exportar tablas

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

## Normalización

Aforix usa un registry de normalización declarativo en:

```text
configs/normalization/
├── flowtracker.yaml
├── molinete.yaml
└── nivus.yaml
```

Estos archivos definen cómo convertir columnas propias de cada instrumento a columnas canónicas. Esto permite agregar o ajustar instrumentos sin modificar directamente la lógica central del normalizador.

Ejemplo conceptual:

```yaml
q_total_m3s:
  sources:
    - total_discharge_m3_s
    - q_m3s
  dtype: float
```

También pueden definirse columnas derivadas, transformaciones y reglas simples de calidad.

---

## Esquemas canónicos principales

### Summary

`Summary` representa una medición completa de caudal.

Columnas típicas:

```text
station_id
station_name
measurement_date
measurement_time
instrument
q_total_m3s
q_total_ls
area_total_m2
width_total_m
velocity_mean_m_s
depth_mean_m
temperature_c
source_file
source_run_dir
run_id
```

### Points

`Points` representa puntos, verticales o posiciones internas de una medición.

Columnas típicas:

```text
station_id
station_name
measurement_date
measurement_time
instrument
point_index
point_label
distance_m
depth_m
velocity_mean_m_s
area_m2
q_m3s
q_ls
percent_q
temperature_c
source_file
source_run_dir
run_id
```

En Nivus, los `Points` pueden enriquecerse usando información de `Sections` para reconstruir área, caudal parcial y porcentaje de caudal.

---

## Export tables

El módulo `export tables` permite generar tablas desde la base normalizada estable.

Permite seleccionar:

- tabla normalizada (`Summary`, `Points`, etc.)
- instrumento (`flowtracker`, `molinete`, `nivus` o `all`)
- puntos/estaciones
- parámetros
- rango de fechas
- agrupación (`none`, `monthly`, `daily`)
- formato (`xlsx` o `csv`)

Las salidas se guardan en la carpeta configurada en `export.tables.output_dir`.

---

## Notas importantes

- `data/`, `runs/`, `database/` y `outputs/` son carpetas locales o generadas; no deben subirse al repositorio.
- La ingesta M9 está prevista, pero debe considerarse pendiente o experimental.
- El sistema está diseñado para que nuevos instrumentos se integren mediante configuración y specs de normalización.
- Las funciones de análisis se deben construir sobre `database/normalized`, no sobre archivos raw sueltos.

---

## Próximos pasos del proyecto

- Completar ingesta M9.
- Migrar funciones analíticas existentes de qSL.
- Consolidar reportes de análisis hidrológico.
- Fortalecer trazabilidad mediante manifests por ejecución.
- Agregar pruebas automáticas y linting.

---

## Autor

Rafael Rosa
