# Batch System Architecture

## Overview

Aforix batch infrastructure provides declarative orchestration for:

- ingest
- build-groups
- normalize
- validation
- export
- analysis

The batch system does not implement processing logic.

Its responsibilities are:

- validation
- planning
- execution orchestration
- manifests
- reporting
- performance metrics
- interactive workflows

---

# Architectural Principles

## 1. No duplicated logic

Batch must reuse existing:

- CLI commands
- modules
- registries
- analysis pipelines

The batch layer must never implement:

- normalize logic
- export logic
- analysis logic
- ingest logic

---

## 2. Registry-driven execution

All steps must resolve through a command registry.

Example:

```yaml
command: normalize.run
```

Resolution flow:

```text
step -> registry -> callable
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

# Batch YAML

## main.yaml

Describes project configuration:

- paths
- instruments
- normalize
- validation
- export
- defaults

## batch.yaml

Describes operational execution:

- steps
- order
- execution behavior
- overrides
- reports

---

# Planned Commands

```bash
aforix batch check
aforix batch plan
aforix batch run
aforix batch interactive
aforix batch list-commands
```

---

# Planned Features

## V1

- sequential execution
- batch schema validation
- registry
- planner
- manifests
- dry-run
- launchers
- interactive workflows
- metrics
- reports

## Later phases

- DAG execution
- scheduler
- SLURM integration
- incremental cache
- retries
- dashboard
- TUI

---

# Manifest

Each batch run will generate:

```text
runs/batch/YYYYMMDD_HHMMSS/
├── manifest.json
├── batch_resolved.yaml
├── logs/
└── reports/
```

---

# Performance Metrics

Metrics planned per step:

- duration
- input/output files
- input/output size
- rows processed
- CPU usage
- RAM usage
- disk usage
- throughput

Sources will distinguish:

- internal sources
- external sources

Examples:

- flowtracker
- molinete
- nivus
- m9
- dinagua
- model outputs

---

# Interactive Layer

Interactive mode will:

- ask questions
- build parameters
- optionally generate temporary batches
- reuse the same registry and runner

Examples:

```bash
aforix normalize interactive
aforix validate interactive
aforix export interactive
```

---

# Launchers

Launchers are UX helpers.

They must:

- open shell
- activate conda
- activate aforix environment
- open interactive workflows
- keep shell open

Launchers must never contain processing logic.
