# Aforix — Main integration and improvement register

This document records findings from the real-data acceptance campaign that are relevant when integrating the acceptance branch back into `main`.

It is intentionally separate from `REAL_DATA_ACCEPTANCE.md`: the acceptance document records test execution and evidence, while this register records **what should be merged, decided, retained, or investigated before/when updating `main`**.

## Status vocabulary

- **MERGE** — production fix already implemented and verified on `test/real-data-acceptance`; should be reviewed and merged into `main`.
- **DECIDE** — product/UX decision discovered during manual review; do not change silently.
- **FOLLOW-UP** — technically relevant issue or legacy behavior still requiring a focused audit/test.
- **ACCEPTED** — observed behavior is intentional or source-data-related; no production correction currently required.
- **PLACEHOLDER** — command/module exists but is not yet a complete production implementation.

## Register

| ID | Area | Finding | Acceptance evidence | Status for main | Proposed action |
|---|---|---|---|---|---|
| MAIN-001 | Run management | `create_run()` previously hardcoded `runs/` and ignored configured `paths.runs_root`. | Regression test failed first; fixed; full suite passed. Acceptance runs now remain under `runs_acceptance/`. | **MERGE** | Merge the production run-manager fix so all commands honor the configured runs root. |
| MAIN-002 | FlowTracker duplicate audit | Standalone pipeline audit treated distinct 20%/80% FlowTracker observations at the same vertical as duplicates because `percent_depth` was omitted from the duplicate key. | Regression reproduced the false positive; fix verified; duplicate audit now reports 461 OK + 208 not_checked and 0 duplicate findings. | **MERGE** | Merge the audit-key fix. Keep production validation and standalone audit semantics aligned. |
| MAIN-003 | Export tables configuration | `export tables` still read legacy config locations and could use `database/normalized` instead of the configured acceptance/current paths. | Modern + legacy path tests pass; full suite passed. | **MERGE** | Merge current-path support while preserving legacy config fallback. |
| MAIN-004 | User-facing XLSX time identity | Export loader inferred `measurement_time` numerically, so leading zeros were lost in Excel (for example `093425` became `93425`). | Manual review and automated fidelity check found the same defect; focused XLSX regression test passes after fix. | **MERGE** | Merge string-preservation for station/date/time identity fields in table exports. |
| MAIN-005 | Station identity / legacy P codes | Normalization still generated redundant `station_code=P<station_id>` even after `station_id` became authoritative and P-free. | Regression failed first; production YAML/normalizer fixed; regenerated Summary has no `station_code`, no station IDs beginning with P, normalize 10/10 PASS, validation 6/6 PASS, full suite 84 passed. | **MERGE** | Merge removal of default legacy `station_code` generation. Retain generic optional capability only when explicitly configured. |
| MAIN-006 | Export tables UX | Manual comparison found the **flat Summary export** clearer and more orderly than the historical/daily-pivot wide format. The pivot remains technically valid but becomes less readable as dates/parameters grow. | Flat XLSX accepted manually in EXP-TABLES-01/03; daily pivot passed 6/6 automated checks in EXP-TABLES-04 but was manually rejected as the default presentation. | **MERGE** | Make flat (`grouping=none`) the default/recommended general-purpose export in the new Aforix version. Keep daily/monthly pivot available only when explicitly requested. |
| MAIN-007 | Export tables metadata | Current workbook includes separate `export` and `metadata` sheets plus metadata sidecar. This was clearer than the historical wide output during the first manual review. | Workbook structure and metadata checks pass. | **DECIDE** | Keep the two-sheet structure unless later manual testing identifies a better user-facing layout. Review metadata wording for end-user clarity during later export tests. |
| MAIN-008 | Station identity downstream | Legacy downstream helpers semantically aliased `P<n>` to `7000+n`, and manual-stage conversion could invent a `P` prefix. This conflicted with the authoritative-station-ID rule. | Regression-first audit covered metadata, export tables, batch, manual stage, quality, section profiles, stage-discharge, correlation, and model-point namespace separation. Targeted downstream suite 6/6 PASS; metadata/boundary suite 29/29 PASS; full suite 90 passed. | **MERGE** | Merge the representation-only station canonicalization, manual-stage identity preservation, safe downstream sorting, and removal of legacy alias guidance. Keep `Pm<n>` model points explicitly separate. |
| MAIN-009 | FlowTracker exact duplicate source files | 30 physical FlowTracker files correspond to 29 unique measurements because one pair is binary-identical and has identical station/date/time. Current build/ingest outputs represent the unique measurement once. | Duplicate pair independently confirmed by hash and metadata. | **ACCEPTED / FOLLOW-UP** | Scientifically acceptable under current duplicate rule. Consider whether provenance should retain both physical source paths even when payload is collapsed. |
| MAIN-010 | Nivus source QC | Nine Nivus points have no valid gate observations in the raw source. | Raw-to-normalized field checks show no ingestion loss; issue is source-data QC. | **ACCEPTED** | Keep as QC information; do not “repair” in normalization. |
| MAIN-011 | Negative flow observations | Pipeline audit reports 236 informational range flags associated with negative flow values; no warning/error range findings. | Hydraulic/unit checks remain clean; production validation range rules pass. | **ACCEPTED** | Preserve signed flow. Keep negative-flow reporting informational unless domain rules change. |
| MAIN-012 | Placeholder commands | `export excel`, M9 ingest, filter-groups, and statistics analysis are not complete production implementations in the audited codebase. | Structural review during acceptance campaign. | **PLACEHOLDER** | Keep clearly documented as incomplete; test/implement separately rather than treating CLI presence as acceptance. |
| MAIN-013 | SIH acceptance isolation | Default SIH config still points to standard database/output paths rather than acceptance-specific paths. | Identified during pipeline mapping; SIH acceptance not yet executed. | **FOLLOW-UP** | Create/use an isolated SIH acceptance config before real-data SIH tests. |
| MAIN-014 | Export tables station-selection guidance | CLI help and export metadata still described legacy/ambiguous point-code behavior after station identity was made exact. | Found during EXP-TABLES continuation after MAIN-008. | **MERGE** | Merge wording cleanup so non-interactive table export documents exact `station_id` matching and does not imply P aliases or unsupported index-token behavior. |
| MAIN-015 | Interactive export station selection | Interactive multi-select checked bare numeric tokens as list indices before exact station IDs, so a numeric station ID could select the wrong station. | Regression reproduced the ambiguity: station ID `1` was interpreted as list index 1 and selected `7001`. Production fix now prioritizes exact station IDs and reserves `idx:N` / `[N]` for explicit index selection. | **MERGE** | Merge the interactive selection precedence fix and updated help wording after targeted/full-suite verification. |
| MAIN-016 | Export tables flat override | CLI help promised `--flat` would prevent pivoting, but the runner still pivoted whenever grouping was daily/monthly and reported grouped filename/metadata semantics. | Regression reproduced the defect: `grouping=daily, pivot=False` produced date-pivot columns instead of row-wise output. Production runner now treats explicit flat mode as authoritative and sets effective grouping to `none`. | **MERGE** | Merge the runner fix after focused/full-suite verification. |
| MAIN-017 | SIH semantic lookups | SIH batch export can succeed structurally even if configured `tipo_aforo_lookup` or `instrumentos_rangos_lookup` does not resolve; current lookup helpers allow an empty result for these fields. | SIH-01 passed 6/6 structural/identity/numeric checks; config review found lookup-key vocabulary that may not match the current lookup CSV values. | **FOLLOW-UP** | Run SIH-02 semantic completeness diagnostic. Do not invent replacement IDs; distinguish matching-normalization defects from missing/incorrect domain mapping that requires a data/config decision. |
| MAIN-018 | SIH textual lookup matching | Configured `tipo_aforo_lookup: Vadeo` is semantically present in `tipos_aforos.csv` as `VADEO`, but production matching is exact/case-sensitive and silently returns blank because the resolver marks this lookup optional. | SIH-02: normalized diagnostic finds the key, while exported `id_tipo_aforo` is blank for both FlowTracker and Molinete. | **FOLLOW-UP** | Regression-first: textual lookup keys should match after representation-only trim/case normalization. Do not broaden this into semantic aliasing. |
| MAIN-019 | SIH configured lookup strictness | When `tipo_aforo_lookup` or `instrumentos_rangos_lookup` is explicitly configured but has no matching lookup row, current resolvers return blank because they call the generic lookup helper with `required=False`. The export can therefore report success with missing configured semantic IDs. | SIH-02 real-data export produced successful files while `id_instrumentos_rangos` was blank for both selected measurements. | **FOLLOW-UP** | Regression-first: an explicitly configured semantic lookup key must resolve exactly once or raise an error; leaving the config key absent may still represent an intentionally blank optional field. |

## Current verified acceptance state after station-code removal

- Real unique measurements: **250** (`29 FlowTracker + 13 Molinete + 208 Nivus`).
- Cross-instrument normalized Summary rows: **250**.
- Cross-instrument normalized Points rows: **3977**.
- Normalize acceptance: **10/10 PASS**.
- Raw column audit: **669/669 OK**.
- Normalized column audit: **669/669 OK**.
- Duplicate audit: **0 duplicate findings**.
- Hydraulic consistency audit: **750/750 OK**.
- Unit consistency audit: **461/461 OK**.
- Validation acceptance: **6/6 PASS**.
- Full automated test suite: **84 passed**.

## Integration rule

Do not merge this branch to `main` merely because an individual acceptance item passes. Before final integration:

1. review all entries marked **MERGE** and confirm the diff is intentional;
2. explicitly resolve entries marked **DECIDE**;
3. either close or deliberately defer **FOLLOW-UP** items;
4. run the full test suite and the selected real-data smoke checks one final time;
5. merge through a reviewed PR so the acceptance history remains traceable.


## MAIN-008 downstream station-identity audit — occurrence inventory

The first source audit found legacy semantic station canonicalization in multiple downstream boundaries, not only in normalization:

- `src/aforix/metadata.py::canonical_station_id` maps `P<n>` to `7000+n`;
- `export/tables/runner.py` uses it for point filtering and point discovery;
- `batch/default_registry.py` uses it for point parsing;
- quality analysis uses it for filename-derived station IDs and filters;
- section-profiles uses it when standardizing station IDs;
- stage-discharge uses it for normalized/manual-stage matching and CLI selection;
- correlation uses it in CLI/interactive selection, gauge loading, and gauge/model workflows;
- `external/manual_stage/convert.py` has a separate legacy rule that converts numeric IDs to `P<n>`.

The model-point namespace `Pm<n>` is intentionally separate and already has explicit protection against confusing measured `P<n>` IDs with model points.

A new downstream regression suite (`tests/test_station_identity_downstream.py`) defines the target rule before production changes: station normalization may clean representation (whitespace/case/float-like string artifacts) but must not create semantic aliases or renumber `P<n>` into the 7000 namespace. Manual-stage conversion must not invent a `P` prefix. Production downstream code remains unchanged until the expected failures are observed.

### MAIN-008 implementation note

After the expected regression failures, the acceptance branch now contains the production correction for downstream station identity. The shared canonical helper no longer creates `P<n> -> 7000+n` aliases, manual-stage conversion no longer creates `P<n>`, and correlation sorting accepts distinct nonnumeric station namespaces. MAIN-008 remains pending verification before its status is promoted to **MERGE**.


### MAIN-008 verification complete

Downstream station identity correction is now fully verified on the acceptance branch:

- downstream identity regression suite: **6/6 PASS**;
- metadata + canonical-boundary suite: **29/29 PASS**;
- full test suite: **90 passed**.

MAIN-008 is promoted to **MERGE**.


## Work checkpoint — 2026-10-02

Acceptance campaign paused after closing **EXP-TABLES-01** and before executing **EXP-TABLES-02**.

Next active item on resume:
- **EXP-TABLES-02 — exact station/date filtered CSV**
- station `7071`
- date `20260120`
- expected two independent same-day measurements (FlowTracker + Molinete)

No merge to `main` should be performed before the acceptance campaign resumes and the remaining export/downstream modules are reviewed.


### MAIN-006 implementation note

The flat-layout product decision has now been implemented on the acceptance branch: both non-interactive and interactive table export default to `grouping=none`. Daily/monthly pivot modes remain explicit options. Verification is pending before final integration.


### MAIN-006 verification complete

The flat-layout default is now verified on the acceptance branch:

- focused default regression: **1/1 PASS**;
- full test suite: **91 passed**.

Both CLI and interactive table export now default to `grouping=none`. Daily/monthly pivot modes remain available only when explicitly requested. MAIN-006 is fully verified for integration.


### MAIN-015 implementation note

The intended regression failure was observed: entering bare `1` selected station `7001` because the code treated it as list index 1. Interactive station selection now gives exact station IDs priority. Explicit index syntax (`idx:N` or `[N]`) remains supported. Verification is pending.


### MAIN-015 verification complete

The interactive station-selection correction is fully verified:

- focused interactive-selection tests: **2/2 PASS**;
- full test suite: **93 passed**.

Exact authoritative station IDs now take precedence in station-selection prompts. Explicit index selection remains available through `idx:N` or `[N]`. MAIN-015 is verified for integration.


### MAIN-016 implementation note

The intended regression failure was observed: `grouping=daily` with `pivot=False` still produced pivot columns such as `20260120 | q_total_ls`.

The runner now treats explicit flat mode as authoritative:
- output remains row-wise flat;
- effective grouping becomes `none`;
- filename uses the `flat` shape;
- metadata reports `grouping: none`, `pivot: False`, and `column_order: flat`.

Verification is pending.


### MAIN-016 verification complete

The explicit flat-override correction is fully verified:

- focused regression: **1/1 PASS**;
- full test suite: **94 passed**.

`pivot=False` now forces true flat output, effective grouping `none`, flat filename semantics, and flat metadata. MAIN-016 is verified for integration.


### SIH-02 diagnosis

The semantic diagnostic produced **2 PASS / 4 FAIL** and separates two different causes:

- `id_tipo_actuacion` and `id_instrumento` are populated in both selected exports (FlowTracker instrument ID `501`, Molinete instrument ID `19`);
- `tipo_aforo_lookup: Vadeo` has a representation-level match in the lookup table (`VADEO`), but production lookup matching is exact/case-sensitive, so exported `id_tipo_aforo` is blank. This is MAIN-018 and is suitable for a code fix;
- `instrumentos_rangos_lookup: Velocimetro puntual` has **no semantic row at all** in the current `instrumentos_rangos.csv`. Exported `id_instrumentos_rangos` is therefore blank. No replacement ID is inferred; this remains a configuration/domain-data decision under MAIN-017.


### MAIN-018 implementation note

The focused regression failed as expected: configured `Vadeo` returned an empty ID against lookup value `VADEO`.

Production textual lookup matching now applies representation-only normalization:
- trim surrounding whitespace;
- case-insensitive comparison via `casefold()`;
- no semantic aliases or substitutions are introduced.

This affects the generic SIH textual lookup helper used by `tipo_aforo` and `instrumentos_rangos`. Therefore `Vadeo` can resolve to the existing `VADEO` row, while `Velocimetro puntual` will still remain unresolved because no corresponding semantic row exists in the current ranges lookup.

Verification is pending.


### MAIN-018 verification

The textual lookup normalization fix is verified at code level:

- focused regression: **1/1 PASS**;
- full test suite: **95 passed**.

A subsequent real-data SIH rerun was interrupted at final metadata write by Windows `PermissionError` on `outputs_acceptance/sih/sih_export_metadata.csv`. Because the prior manual review had opened the SIH output directory/files, this rerun cannot be treated as a clean end-to-end verification: the output directory may contain a mixture of newly rewritten and previously open/stale files.

Observed partial files show Molinete `id_tipo_aforo=57`, consistent with the fix, while FlowTracker still appeared blank; that asymmetry must be rechecked only after closing open files and performing a confirmed clean output-directory removal.


### MAIN-018 real-data verification complete

A clean SIH regeneration after the file-lock issue confirmed the production fix end to end:

- FlowTracker exported `id_tipo_aforo=57`;
- Molinete exported `id_tipo_aforo=57`;
- both resolve configured `Vadeo` against lookup row `VADEO`;
- the only remaining semantic blank in these two aforos is `id_instrumentos_rangos`.

MAIN-018 is fully verified for integration.


### MAIN-019 implementation note

The strictness regression failed as intended: both explicitly configured but unresolved semantic lookups returned blank instead of raising.

Production resolver behavior is now:
- a direct configured ID still wins;
- if no direct ID and no lookup key is configured, the field may remain intentionally blank;
- if a lookup key is explicitly configured, it must resolve exactly once or raise a `ValueError`.

This makes unresolved SIH semantics visible in the per-measurement export metadata instead of silently producing a successful export with a blank configured ID. Verification is pending.


### MAIN-019 verification complete

The configured-lookup strictness correction is fully verified at code level:

- focused regression: **2/2 PASS**;
- full test suite: **97 passed** (repeated twice with the same result).

Explicitly configured SIH semantic lookup keys now must resolve exactly once; otherwise the measurement export raises and is recorded as an error instead of silently emitting a blank configured ID. MAIN-019 is verified for integration.


### MAIN-019 real-data verification complete

SIH-03 verified the strict configured-lookup behavior end to end with real acceptance data:

- output directory was confirmed clean before execution;
- generated files: **1** (`sih_export_metadata.csv` only);
- expected unresolved lookup checker: **5/5 PASS**;
- both selected measurements were recorded as explicit export errors;
- no partial `actuacion` or `aforo` CSVs were emitted.

This confirms that unresolved configured SIH semantics no longer pass silently. MAIN-019 is fully verified for integration.

### Current migration checkpoint

All production-code findings intended for later integration into `main` are tracked in this register. Acceptance-only configs/checkers/docs remain campaign scaffolding and should not be merged blindly with production changes.

Latest verified full test suite: **97 passed**.
