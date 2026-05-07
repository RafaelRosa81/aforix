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

## Proposed configuration concept

```yaml
ingest:
  flowtracker:
    metadata_policy:
      station_id:
        strategy: first_non_empty
        sources:
          - {type: raw_field, key: station_id}
          - {type: raw_field, key: file_name}
          - {type: path_regex, pattern: "P(?P<value>\\d{1,4})"}
        transforms:
          - strip
          - uppercase
          - remove_prefix: "P"
        output_format: string

      station_code:
        strategy: build_from_field
        source: station_id
        prefix: "P"

      measurement_date:
        strategy: datetime_parse
        source: {type: raw_field, key: start_date_time}
        input_formats:
          - "%Y/%m/%d %H:%M:%S"
          - "%Y-%m-%d %H:%M:%S"
          - "%m/%d/%Y %H:%M:%S"
        output_format: "%Y%m%d"

      measurement_time:
        strategy: datetime_parse
        source: {type: raw_field, key: start_date_time}
        input_formats:
          - "%Y/%m/%d %H:%M:%S"
          - "%Y-%m-%d %H:%M:%S"
          - "%m/%d/%Y %H:%M:%S"
        output_format: "%H%M%S"
```

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
