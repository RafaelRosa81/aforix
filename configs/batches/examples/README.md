# Batch Examples

This directory contains example batch pipelines for validating and testing the Aforix batch infrastructure.

## Files

### `check_only.yaml`
Minimal validation batch.

Recommended first test:

```bash
python -m aforix batch check -b configs/batches/examples/check_only.yaml
```

---

### `normalize_validate.yaml`
Runs normalization and validation using already existing grouped datasets.

Useful when:
- ingest outputs already exist;
- testing normalize/validate iteration.

---

### `full_ingest_pipeline.yaml`
Complete end-to-end pipeline:

- config check
- ingest FlowTracker
- ingest Molinete
- ingest Nivus
- build groups
- normalize
- validate
- export tables

Recommended for operational testing after validating the smaller pipelines first.

---

## Recommended execution order

1. `check_only.yaml`
2. `normalize_validate.yaml`
3. `full_ingest_pipeline.yaml`

---

## Typical commands

Validate batch:

```bash
aforix batch check -b configs/batches/examples/check_only.yaml
```

Preview execution:

```bash
aforix batch plan -b configs/batches/examples/full_ingest_pipeline.yaml
```

Dry-run:

```bash
aforix batch run -b configs/batches/examples/full_ingest_pipeline.yaml --dry-run
```

Real execution:

```bash
aforix batch run -b configs/batches/examples/full_ingest_pipeline.yaml
```
