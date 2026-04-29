# Aforix

Aforix es una biblioteca en Python para procesar datos de aforos (mediciones de caudal) provenientes de distintos instrumentos (FlowTracker, Molinete, Nivus, M9).

El objetivo es construir un **pipeline consistente, trazable e independiente del instrumento** para el procesamiento de datos hidrológicos.

---

## 🚀 Estado actual

✔ Ingesta FlowTracker
✔ Ingesta Molinete
✔ Ingesta Nivus
✔ Construcción de grupos de datos
✔ Normalización (Summary + Points)
✔ Validación hidráulica

---

## 🧠 Descripción del pipeline

El flujo actual es:

```text
DATOS RAW
   ↓
INGESTA (por instrumento)
   ↓
RAW CANONICAL (por instrumento)
   ↓
BUILD GROUPS (unificación)
   ↓
NORMALIZACIÓN (schema común)
   ↓
VALIDACIÓN (consistencia hidráulica)
```

---

## 📂 Estructura del proyecto

```text
src/aforix/
├── ingest/            # Lectura de datos por instrumento
├── normalize/         # Normalización a esquema canónico
├── groups/            # Construcción de datasets unificados
├── analysis/          # (futuro)
├── export/            # (futuro)
├── cli/               # Interfaz de línea de comandos
```

Datos generados (NO versionados):

```text
runs/                  # Ejecuciones del pipeline
database/
├── raw_canonical/     # Datos por instrumento
├── data_groups/       # Datos combinados
├── normalized/        # Datos normalizados
├── validation/        # Resultados de validación
```

---

## ⚙️ Instalación

```bash
pip install -e .
```

Activar entorno:

```bash
conda activate aforix
```

---

## 📥 Ingesta de datos

### FlowTracker

```bash
aforix ingest flowtracker --config configs/examples/main.yaml
```

### Molinete

```bash
aforix ingest molinete --config configs/examples/main.yaml
```

### Nivus

```bash
aforix ingest nivus --config configs/examples/main.yaml
```

---

## 🔗 Construcción de grupos

Unifica todos los instrumentos en datasets comunes:

```bash
aforix build-groups --config configs/examples/main.yaml
```

Salida:

```text
database/data_groups/
├── Summary/summary_all.csv
├── Points/points_all.csv
├── Sections/sections_all.csv
├── Gates/gates_all.csv
```

---

## 🔄 Normalización

### Summary

```bash
aforix normalize summary --config configs/examples/main.yaml
```

Salida:

```text
database/normalized/Summary/summary_normalized.csv
```

---

### Points

```bash
aforix normalize points --config configs/examples/main.yaml
```

Salida:

```text
database/normalized/Points/points_normalized.csv
```

---

## 📊 Validación hidráulica

Verifica la consistencia entre Summary y Points:

```bash
python scripts/validate_hydraulic_consistency.py
```

Chequeos realizados:

```text
SUM(points.q_m3s) ≈ summary.q_total_m3s
SUM(points.area_m2) ≈ summary.area_total_m2
```

Tolerancia:

```text
±1% → aceptable
```

---

## 🧩 Esquema canónico

### Summary

```text
instrument
station_id
measurement_date
measurement_time
q_total_m3s
area_total_m2
width_total_m
velocity_mean_m_s
depth_mean_m
temperature_c
```

---

### Points

```text
instrument
station_id
measurement_date
measurement_time
point_index
distance_m
depth_m
velocity_mean_m_s
area_m2
q_m3s
percent_q
```

---

## ⚠️ Notas importantes

* Las carpetas `database/` y `runs/` no se versionan.
* FlowTracker no provee Sections ni Gates (actualmente vacíos).
* En Nivus, los Points se enriquecen usando información de Sections.
* La normalización permite comparar instrumentos bajo un mismo esquema.

---

## 🔜 Próximos pasos

* Ingesta M9
* Módulo de control de calidad (QC)
* Registry (comparación entre instrumentos)
* Migración de funciones existentes de qSL

---

## 👤 Autor

Rafael Rosa
