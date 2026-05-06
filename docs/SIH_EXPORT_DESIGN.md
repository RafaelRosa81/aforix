# SIH Export Module Design

## Objective

Generate SIH-compatible CSV exports from Aforix normalized and raw_canonical datasets.

The module must:

- be fully configuration-driven;
- avoid hardcoded SIH IDs in Python;
- support multiple instruments progressively;
- preserve traceability;
- support interactive and advanced CLI modes;
- support massive/batch export selection.

---

## Expected CLI

Interactive mode:

```bash
aforix export sih -c configs/examples/main.yaml --interactive
```

Advanced mode:

```bash
aforix export sih -c configs/examples/main.yaml \
  --selection-file configs/sih/selection_template.csv
```

Future advanced options may include:

```bash
--stations P8 P11
--instruments nivus flowtracker
--early-date 20251201
--late-date 20260131
```

---

## Massive Selection Strategy

The recommended massive-input workflow is a CSV selection file.

Example:

```csv
station_id,measurement_date,measurement_time,instrument,export_id
P1,20251201,103000,flowtracker,EXP001
P8,20251215,124600,nivus,EXP002
```

This strategy is:

- reproducible;
- auditable;
- Git-trackable;
- easy to edit in Excel;
- easy to validate automatically.

Each row represents one measurement export.

---

## Output Naming

Each measurement generates:

- one actuaciones CSV;
- one aforos CSV.

Output names:

```text
ID_{export_id}_actuacion_{station_id}_{YYYYMMDD}_{HHMMSS}.csv
ID_{export_id}_aforo_{station_id}_{YYYYMMDD}_{HHMMSS}.csv
```

The measurement metadata comes from normalized Summary tables.

---

## Proposed Package Structure

```text
src/aforix/export/sih/
├── __init__.py
├── cli.py
├── config.py
├── interactive.py
├── runner.py
├── inputs.py
├── mappings.py
├── schema.py
├── writers.py
└── validation.py
```

---

## Data Sources

Priority order:

1. normalized
2. raw_canonical
3. workbook lookup sheets
4. YAML/module config
5. interactive/manual values

---

## SIH Workbook Sheets

Workbook sheets:

- sdh_actuaciones
- sdh_aforos
- estaciones
- instrumentos
- tipos_aforos
- instrumentos_rangos

---

## Key Design Rules

- No SIH IDs hardcoded in Python.
- No instrument-specific column names hardcoded in Python.
- All mappings configurable.
- All thresholds configurable.
- All output names configurable.
- All date formats configurable.
