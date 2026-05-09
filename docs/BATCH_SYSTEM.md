# Batch System Architecture

## Overview

Aforix batch infrastructure provides declarative orchestration for:

- ingest
- build-groups
- normalize
- validation
- export
- analysis

The batch system does not implement processing logic. It only validates, plans, executes registered commands, writes manifests, and generates reports.

---

# Architectural Principles

## 1. No duplicated logic

Batch must reuse existing modules and command entrypoints.

The batch layer must never implement:

- ingest logic
- normalize logic
- validation logic
- export logic
- analysis logic

---

## 2. Registry-driven execution

All steps resolve through the batch command registry.

```yaml
steps:
  - id: normalize
    command: normalize.run
```

Resolution flow:

```text
batch.yaml -> planner -> registry -> existing Aforix module
```

---

## 3. Separation of layers

```text
Launchers
    ↓
Interactive UX
    ↓
CLI Typer
    ↓
Batch Runner
    ↓
Planner
    ↓
Registry
    ↓
Core Modules
```

---

# Batch YAML Structure

```yaml
version: 1

batch:
  id: example
  name: Example batch
  description: Example execution recipe

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
    params:
      config: ${main_config}
```

---

# Available Commands

Typical batch commands include:

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

List currently registered commands with:

```bash
aforix batch list-commands
```

---

# CLI Usage

Validate a batch file:

```bash
aforix batch check -b configs/batches/examples/check_only.yaml
```

Preview the execution plan:

```bash
aforix batch plan -b configs/batches/examples/full_ingest_pipeline.yaml
```

Dry-run a batch:

```bash
aforix batch run -b configs/batches/examples/full_ingest_pipeline.yaml --dry-run
```

Run a batch:

```bash
aforix batch run -b configs/batches/examples/full_ingest_pipeline.yaml
```

---

# Example Batches

Examples are located in:

```text
configs/batches/examples/
```

Recommended progression:

1. `check_only.yaml`
2. `normalize_validate.yaml`
3. `analysis_pipeline.yaml`
4. `consolidated_data_pipeline.yaml`
5. `correlation_gauges_vs_model.yaml`
6. `correlation_gauges_vs_stations.yaml`
7. `correlation_model_vs_stations.yaml`
8. `full_ingest_pipeline.yaml`

---

# Manifest and Reports

Each batch run generates:

```text
runs/batch/YYYYMMDD_HHMMSS/
├── manifest.json
└── reports/
    ├── batch_report.md
    ├── batch_report.json
    └── batch_report.csv
```

The manifest records:

- batch id
- run id
- status
- start/end time
- duration
- step status
- outputs
- warnings
- errors
- metrics

---

# Metrics

The batch runner collects lightweight per-step metrics.

If `psutil` is available, CPU and RAM are recorded. If not, the batch still runs and reports `metrics_available: false`.

Current metrics include:

- duration
- CPU start/end percent
- RAM start/end/peak MB
- command-reported metrics, when available

Future metrics may include:

- input/output files
- input/output size
- rows processed
- throughput
- internal/external source volumes

---

# Interactive Layer and Launchers

Interactive workflows and launchers are UX helpers only.

They must:

- open a shell
- activate the Aforix environment
- call CLI commands
- keep the shell open for debugging

They must not contain processing logic.

---

# Current Limitations

The first batch version is intentionally sequential.

Not included yet:

- DAG execution
- scheduler
- SLURM integration
- retries
- incremental cache
- dashboard
- TUI

These can be added later without changing the core principle: batch orchestrates registered commands and does not own domain logic.
