# Metadata extraction policy PR-2

This PR starts the second step after configurable metadata normalization.

## Context

PR-1 added configurable metadata normalization in the normalize stage:

- `station_id` canonical formatting
- `station_code` generation
- `measurement_date` formatting
- `measurement_time` formatting

That solved false join mismatches in hydraulic validation, but it is still an intermediate design.

## Problem to solve in PR-2

The decision of where metadata comes from should not be hardcoded in instrument ingest code and should not primarily live in normalization YAMLs.

The ingest stage should be configurable for:

- `station_id`
- `station_name`
- `measurement_date`
- `measurement_time`
- optionally `station_code`

## Target architecture

```text
raw file parser
  -> raw parsed payload
  -> configurable metadata extraction policy
  -> raw_canonical CSV with consistent traceability fields
  -> build-groups
  -> normalize
```

## Separation of responsibilities

### Ingest

Ingest decides where metadata comes from.

Examples:

- FlowTracker: `.dis` summary field, filename, or parent folder.
- Molinete: Excel cell/header, filename, or parent folder.
- Nivus: XML attribute, filename, or parent folder.

### Normalize

Normalize should eventually only format/validate metadata and map hydraulic variables.

The `metadata:` fallback sections added in PR-1 should be kept temporarily for backward compatibility, but the long-term target is to simplify them once ingest emits consistent metadata.

## Proposed configuration shape

The configuration should live under each instrument ingest config, for example:

```yaml
ingest:
  nivus:
    metadata_policy:
      station_id:
        strategy: first_non_empty
        sources:
          - type: raw_field
            key: station_id
          - type: raw_field
            key: ref
          - type: xml_attribute
            path: ".//ref"
            attribute: "val"
          - type: filename_regex
            pattern: "P(?P<value>\\d{1,4})"
          - type: path_regex
            pattern: "P(?P<value>\\d{1,4})"
        transforms:
          - strip
          - uppercase
          - remove_prefix: "P"
          - digits_only

      station_name:
        strategy: first_non_empty
        sources:
          - type: raw_field
            key: station_name
          - type: raw_field
            key: name
          - type: xml_attribute
            path: ".//name"
            attribute: "val"

      measurement_datetime:
        strategy: first_non_empty_datetime
        sources:
          - type: raw_field
            key: measurement_datetime
          - type: raw_field
            key: timestamp_time
          - type: xml_attribute
            path: ".//timestamp"
            attribute: "time"
          - type: filename_regex
            pattern: "(?P<date>\\d{8})_(?P<time>\\d{6})"
        input_formats:
          - "%Y-%m-%d %H:%M:%S"
          - "%Y/%m/%d %H:%M:%S"
          - "%Y%m%d_%H%M%S"
        output_date_format: "%Y%m%d"
        output_time_format: "%H%M%S"
```

## Minimal PR-2 scope

To keep this PR small and safe:

1. Add a reusable metadata extraction module.
2. Support a limited first set of source types:
   - `raw_field`
   - `filename_regex`
   - `path_regex`
   - `constant`
3. Integrate it first with one instrument only, preferably Molinete or Nivus.
4. Leave existing ingest behavior as fallback.
5. Do not remove PR-1 normalization metadata fallback yet.

## Later extensions

After the basic engine is validated, add support for:

- `xml_attribute`
- Excel cell references
- lookup tables
- source priority rules
- required metadata validation
- detailed metadata extraction reports

## Success criteria

After PR-2:

- One instrument should get `station_id`, `station_name`, `measurement_date`, and `measurement_time` through configuration instead of hardcoded ingest logic.
- Raw canonical outputs should still be equivalent or better than before.
- Existing normalize and hydraulic validation should continue to pass.
