# Batch Examples

This directory contains example batch pipelines for validating, running, exporting and analyzing Aforix data.

Each file is a YAML recipe that can be executed with:

```bash
aforix batch run -b configs/batches/examples/<batch_file>.yaml
```

---

# Basic validation

## `check_only.yaml`

Minimal validation batch.

Use it to confirm that:

- the batch system is installed;
- the main config loads correctly;
- the batch registry is available.

```bash
aforix batch check -b configs/batches/examples/check_only.yaml
aforix batch run -b configs/batches/examples/check_only.yaml
```

---

# Processing pipelines

## `normalize_validate.yaml`

Runs normalization and validation assuming grouped raw canonical datasets already exist.

Useful when:

- ingest outputs already exist;
- `database/raw_canonical` is already populated;
- you are testing normalization and validation only.

---

## `full_ingest_pipeline.yaml`

Complete end-to-end processing pipeline:

- config check
- ingest FlowTracker
- ingest Molinete
- ingest Nivus
- build groups
- normalize
- validate
- export tables
- analysis workflows

This is the most complete operational example.

---

## `consolidated_data_pipeline.yaml`

Fast operational pipeline for users that already have consolidated data.

It assumes:

- `database/raw_canonical` already exists;
- `database/normalized` already exists.

It runs:

- validation;
- table export;
- quality metrics;
- stage-discharge analysis;
- section profiles analysis.

---

# Export pipelines

## `sih_export_pipeline.yaml`

Exports consolidated Aforix measurements to SIH CSV format using:

```yaml
command: export.sih
```

Use this when the SIH export config defines all required selection/defaults.

---

## `sih_export_with_selection.yaml`

Exports selected measurements to SIH using an explicit selection CSV file.

The batch variable is:

```yaml
selection_file: data/external/sih/selection.csv
```

Use this when the user wants to export only specific actuaciones or aforos.

---

# Analysis pipelines

## `analysis_pipeline.yaml`

Runs analysis modules on existing normalized data:

- quality metrics;
- stage-discharge;
- section profiles.

---

# Correlation pipelines

## `correlation_gauges_vs_model.yaml`

Runs correlation between normalized gauging measurements and model outputs.

---

## `correlation_gauges_vs_stations.yaml`

Runs correlation between gauges and external stations using all available pairs:

```yaml
all_pairs: true
```

---

## `correlation_gauges_vs_stations_pairs.yaml`

Runs correlation between selected gauge/station pairs.

The pair format is:

```yaml
gauge_station_pairs: "[1 44] [8 117] [13 10]"
```

Each pair means:

```text
[gauge_point station_id]
```

---

## `correlation_model_vs_stations.yaml`

Runs correlation between model outputs and external stations.

---

# Recommended execution order

For a new setup:

1. `check_only.yaml`
2. `full_ingest_pipeline.yaml`
3. `consolidated_data_pipeline.yaml`
4. `analysis_pipeline.yaml`
5. correlation examples as needed
6. SIH export examples as needed

For fast repeated work after data is already consolidated:

1. `check_only.yaml`
2. `consolidated_data_pipeline.yaml`
3. `analysis_pipeline.yaml`
4. SIH/correlation-specific batches

---

# Typical commands

Validate a batch:

```bash
aforix batch check -b configs/batches/examples/check_only.yaml
```

Preview execution:

```bash
aforix batch plan -b configs/batches/examples/consolidated_data_pipeline.yaml
```

Dry-run:

```bash
aforix batch run -b configs/batches/examples/consolidated_data_pipeline.yaml --dry-run
```

Real execution:

```bash
aforix batch run -b configs/batches/examples/consolidated_data_pipeline.yaml
```
