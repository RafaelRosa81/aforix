# Metadata policy PR-1 plan

This branch is intended to introduce a small, safe first step toward configurable metadata handling in Aforix.

## Scope

PR-1 should focus on canonical formatting of shared metadata fields before broader ingest refactors:

- `station_id`
- optional `station_code`
- `measurement_date`
- `measurement_time`

## Design principle

Metadata normalization must be configurable by instrument. The code should avoid hardcoded assumptions such as:

- station identifiers always using prefix `P`
- dates always being `%Y%m%d`
- times always already being six digits
- metadata always coming from the same raw field for every instrument

## Final PR-1 design direction

The normalization YAML for each instrument/table should explicitly separate:

```yaml
metadata:
  station_id:
    sources:
      - station_id
      - file_name

  station_name:
    sources:
      - station_name
      - site_name

  measurement_date:
    sources:
      - measurement_date
      - start_date_time

  measurement_time:
    sources:
      - measurement_time
      - start_date_time
```

from:

```yaml
metadata_policy:
  station_id:
    remove_prefixes: ["P"]
    digits_only: true

  station_code:
    enabled: true
    prefix: "P"

  measurement_date:
    output_format: "%Y%m%d"

  measurement_time:
    output_format: "%H%M%S"
```

This distinction is important:

- `metadata` defines where traceability fields come from.
- `metadata_policy` defines how those fields are normalized/formatted.
- `columns` remains focused on hydraulic and measurement variables.

## Backward compatibility target

PR-1 should remain compatible with existing normalization YAMLs that still define:

```yaml
columns:
  station_id:
    source: station_id
```

The new `metadata:` section is additive and progressively adoptable.

## Initial implementation target

Before changing all ingest modules, create reusable helpers or a small metadata policy module that can normalize:

- `P11` -> `11` when configured to remove prefix
- `11` -> `P11` when configured to build a station code
- `01/19/2026` -> `20260119`
- `2026-01-19` -> `20260119`
- `20260119` -> `20260119`
- `9:15:00` -> `091500`
- `91500` -> `091500`
- `091500` -> `091500`

## Validation target

After this PR, hydraulic validation should no longer produce false `left_only` / `right_only` rows caused by metadata format mismatches such as:

- `93425` vs `093425`
- `91500` vs `091500`
- `01/19/2026` vs `20260119`
- `P11` vs `11`

## Out of scope for PR-1

- full build-groups dedup redesign
- append/upsert normalized database policy
- rewriting all instrument parsers
- changing raw extraction behavior
