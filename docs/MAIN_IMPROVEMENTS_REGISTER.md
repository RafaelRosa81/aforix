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
| MAIN-013 | SIH acceptance isolation | SIH real-data acceptance requires paths isolated from production/default database and output locations. | `configs/sih/sih_acceptance.yaml` was created and used successfully through SIH-01 to SIH-06, keeping normalized/raw/output paths under acceptance locations. | **ACCEPTED** | Retain the acceptance config as campaign scaffolding; do not merge it blindly into production defaults. |
| MAIN-014 | Export tables station-selection guidance | CLI help and export metadata still described legacy/ambiguous point-code behavior after station identity was made exact. | Found during EXP-TABLES continuation after MAIN-008. | **MERGE** | Merge wording cleanup so non-interactive table export documents exact `station_id` matching and does not imply P aliases or unsupported index-token behavior. |
| MAIN-015 | Interactive export station selection | Interactive multi-select checked bare numeric tokens as list indices before exact station IDs, so a numeric station ID could select the wrong station. | Regression reproduced the ambiguity: station ID `1` was interpreted as list index 1 and selected `7001`. Production fix now prioritizes exact station IDs and reserves `idx:N` / `[N]` for explicit index selection. | **MERGE** | Merge the interactive selection precedence fix and updated help wording after targeted/full-suite verification. |
| MAIN-016 | Export tables flat override | CLI help promised `--flat` would prevent pivoting, but the runner still pivoted whenever grouping was daily/monthly and reported grouped filename/metadata semantics. | Regression reproduced the defect: `grouping=daily, pivot=False` produced date-pivot columns instead of row-wise output. Production runner now treats explicit flat mode as authoritative and sets effective grouping to `none`. | **MERGE** | Merge the runner fix after focused/full-suite verification. |
| MAIN-017 | SIH semantic lookups | The original SIH config used semantic keys that were absent from the lookup CSVs. Project mappings have now been explicitly adopted: FT/ML `VADEO(57)/Velocimetro(11)`, Nivus `VADEO(57)/Acustico(10)`, M9 `BOTE(59)/ADCP(12)`. | Config consistency regression 2/2 PASS; full suite 99 passed; production config and lookup-table edits committed to the acceptance branch. | **MERGE** | Merge the adopted lookup rows/config mappings together with their consistency regression. Keep the mappings declarative; do not introduce code aliases. |
| MAIN-018 | SIH textual lookup matching | SIH textual lookup matching previously failed on representation-only differences such as `Vadeo` vs `VADEO`. | Focused regression 1/1 PASS; clean real-data rerun resolved `id_tipo_aforo=57` for FlowTracker and Molinete; later full suite 99 passed. | **MERGE** | Merge trim/casefold representation normalization only; keep semantic substitutions in configuration/data, not code. |
| MAIN-019 | SIH configured lookup strictness | Explicitly configured SIH semantic lookups previously could fail silently and emit blank IDs. | Focused regression 2/2 PASS; SIH-03 real-data error-handling check 5/5 PASS; later full suite 99 passed. | **MERGE** | Merge strict configured-lookup resolution: configured keys must resolve exactly once; absent keys may remain intentionally blank. |
| MAIN-020 | SIH operator identity | Real Molinete export writes `id_operador=I. Pérez`, while FlowTracker and Nivus are blank. The field name suggests an identifier, but the current config maps raw free text (`realizado`) directly for Molinete and there is no operator lookup in the reviewed SIH config. | SIH-04: Molinete actuación contains `I. Pérez`, FlowTracker blank. SIH-06 manual review: Nivus actuación also has blank `id_operador`. | **FOLLOW-UP — CLIENT QUERY** | Ask the client what SIH expects in `id_operador` (name/text, code, or foreign-key ID) and how operators should be mapped. Do not implement or infer IDs until the client provides the authoritative rule. Tracked in `docs/CLIENT_QUERIES.md`. |
| MAIN-021 | SIH scale fields | Molinete SIH config referenced nonexistent raw column `escala_media` for `lectura_escala` and `escala_media`; the adapter actually emits `escala_media_m`. The selected real measurement also has blank source values for `esc_ini_m`, `esc_fin_m`, and `escala_media_m`. | Regression failed first as intended; real-data diagnostic separated config defect from source-data blanks; config corrected in both SIH configs; focused regression 1/1 PASS; full suite 100 passed. | **MERGE** | Merge the declarative Molinete mapping correction (`escala_media_m`). Keep the blank scale fields for ACCM001 as accepted source-data absence, not an export defect. |
| MAIN-022 | SIH quality / `nivel_confiabilidad` | Nivus SIH config declares a quality source (`quality_metrics`), parameter `CG(%)`, and Bueno/Regular/Malo thresholds, but the SIH runner/mapping never reads quality results and always writes `nivel_confiabilidad` blank. The project will next build a broader data-quality evaluation system covering Nivus, FlowTracker, and Molinete, so SIH confidence integration should be designed against that unified quality model rather than implemented only for Nivus now. | SIH-06 real-data acceptance: Nivus core export 4 PASS / 0 FAIL / 1 INFO; `nivel_confiabilidad=''`. Repository review confirms no current SIH quality-output integration path. | **FOLLOW-UP — DEFERRED** | Defer implementation until the cross-instrument quality-evaluation system is defined for FlowTracker, Molinete, and Nivus. Then define the SIH `nivel_confiabilidad` contract and integrate the unified per-measurement quality result regression-first. |
| MAIN-023 | SIH documentation and sample-selection drift | SIH user docs/examples contained pre-acceptance semantics: legacy `P` station aliases, old semantic lookup labels, and the old Molinete `escala_media` source name. | Regression first: 3/3 failed. After documentation/template correction, a residual filename example caused 2/3 PASS and full suite 102/103; final cleanup then produced focused 3/3 PASS and full suite 103 passed. | **MERGE** | Merge the synchronized SIH docs/template updates with the regression guard so documentation remains aligned with authoritative station IDs, adopted semantic mappings, and `escala_media_m`. |
| MAIN-024 | Section profiles station selection | Advanced and interactive section-profile selectors converted numeric station IDs to `P<n>`, inventing a prefix and making authoritative numeric IDs such as `7001` fail exact filtering. | Regression failed 2/2 as intended: both CLI and interactive normalized `7001` to `P7001`. Production correction now delegates to representation-only `canonical_station_id()`. | **FOLLOW-UP — VERIFY** | Rerun focused regression and full suite, then execute real-data section-profile acceptance. |


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
- Full automated test suite: **103 passed**.

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


### MAIN-017 scope expansion — Nivus and M9

Review of the current SIH configuration shows that the semantic lookup mismatch is broader than FlowTracker/Molinete:

- FlowTracker: `instrumentos_rangos_lookup: Velocimetro puntual` — absent from current `instrumentos_rangos.csv`;
- Molinete: `instrumentos_rangos_lookup: Velocimetro puntual` — absent;
- Nivus: `instrumentos_rangos_lookup: Doppler acustico` — absent (current lookup has only `Acustico` as a potentially related label, but no semantic equivalence is assumed);
- M9: `instrumentos_rangos_lookup: ADCP movil` — absent.

There is also a separate SIH `tipo_aforo` lookup gap for:
- Nivus: `tipo_aforo_lookup: Acustico` — absent from current `tipos_aforos.csv`;
- M9: `tipo_aforo_lookup: ADCP` — absent.

M9 is currently disabled in SIH config, so these M9 mismatches do not affect current exports until M9 is enabled. Nivus is enabled and therefore would currently fail strict semantic lookup resolution under MAIN-019 until its SIH mappings are defined.


### MAIN-017 domain mapping decision

The SIH semantic mapping has now been explicitly chosen for the project:

- FlowTracker: `tipo_aforo=VADEO (57)`, `instrumentos_rangos=Velocimetro (11)`;
- Molinete: `tipo_aforo=VADEO (57)`, `instrumentos_rangos=Velocimetro (11)`;
- Nivus: `tipo_aforo=VADEO (57)`, `instrumentos_rangos=Acustico (10)`;
- M9: `tipo_aforo=BOTE (59)`, `instrumentos_rangos=ADCP (12)`.

These are deliberate project/domain choices supplied during acceptance, not inferred aliases. A regression test now requires every configured lookup key in the main SIH config to resolve exactly once and requires acceptance SIH semantic mappings to stay synchronized with the main SIH config.

The production config edits themselves are currently local/uncommitted and are not overwritten by this test commit.


### MAIN-017 regression synchronization

The expected first regression result was observed: **1 PASS / 1 FAIL**. Main SIH lookup keys resolve against the user's locally updated lookup CSV, while the acceptance SIH config still differed from the main config (`Vadeo` vs `VADEO` was the first reported mismatch).

`configs/sih/sih_acceptance.yaml` has now been synchronized to the adopted mappings: FlowTracker/Molinete `VADEO / Velocimetro`, Nivus `VADEO / Acustico`, M9 `BOTE / ADCP`. The user's locally modified production config files were not touched remotely.


### MAIN-017 configuration regression verification

The adopted SIH semantic mappings now pass the focused consistency regression with the user's local production-config edits plus the synchronized acceptance config: **2/2 PASS**.

The full test suite also passes: **99 passed**.

The production config edits (`configs/sih/sih.yaml` and `configs/sih/instrumentos_rangos.csv`) are still local/uncommitted at this checkpoint and must be committed/pushed before MAIN-017 can be considered fully captured in the branch history. Real-data SIH export verification is still pending.


### SIH-04 uploaded-output review

Five generated CSVs were reviewed after adopting the SIH semantic mappings. Both selected measurements are recorded as `success`; station/date/time identity is preserved as `7071 / 20260120 / 141519` (FlowTracker) and `7071 / 20260120 / 142300` (Molinete). The adopted mappings are present in both aforo files: `id_tipo_aforo=57` and `id_instrumentos_rangos=11`. Instrument IDs remain `501` (FlowTracker) and `19` (Molinete).

The hydraulic summary values are internally coherent at the exported precision: Molinete satisfies `caudal = seccion * velocidad_media` to floating-point precision; FlowTracker differs by about 0.07%, consistent with rounded exported mean velocity. Empty autogenerated `id`, `id_actuacion`, and `id_perfil` fields remain consistent with current configuration.

Two follow-ups were registered rather than silently accepted: operator identity semantics (MAIN-020) and blank Molinete scale fields despite a found raw-canonical row (MAIN-021). The Molinete free-text observation still says `Punto P71`; this is treated as preserved source text, not as station identity, because the actual station field and filenames correctly use authoritative ID `7071`.


### MAIN-021 diagnosis — Molinete scale mapping

Repository review identified a concrete configuration/source-column mismatch before changing production configuration. The Molinete adapter emits raw-canonical `escala_media_m`, while both SIH configs currently map `lectura_escala` and `escala_media` from `escala_media` (without `_m`). Therefore those two outputs are guaranteed blank even when the source contains a scale mean.

`escala_inicio -> esc_ini_m` and `escala_fin -> esc_fin_m` already point to real adapter columns. Their blank values in SIH-04 may therefore be genuine source-data blanks; a real-data diagnostic was added to inspect the selected raw-canonical row before deciding.

A focused regression test was added first and is expected to fail until the two `escala_media` source mappings are corrected.

### MAIN-020 diagnosis — operator mapping contract

The current repository contains no SIH operator lookup table or operator-ID mapping. Molinete maps raw field `realizado` directly into output column `id_operador`; the reviewed row therefore exports the source text `I. Pérez`. This cannot be classified as correct or incorrect from repository evidence alone. Keep MAIN-020 open until the SIH contract or authoritative operator-ID catalogue is available; do not invent an ID.


### MAIN-021 regression result and real-data diagnosis

The focused regression failed exactly as intended: `sih.yaml` still maps Molinete `escala_media` to raw column `escala_media` instead of the adapter column `escala_media_m`.

Real-data diagnostic for station `7071`, date `20260120`, time `142300` showed:
- `id_operador -> realizado`: column exists, value `I. Pérez`;
- `lectura_escala -> escala_media`: configured source column does not exist;
- `escala_inicio -> esc_ini_m`: column exists, but source value is blank;
- `escala_fin -> esc_fin_m`: column exists, but source value is blank;
- `escala_media -> escala_media`: configured source column does not exist;
- actual adapter column `escala_media_m`: column exists, but source value is blank;
- `observaciones`: present;
- `radio_hidraulico_m`: present (`0.22646286086565168`).

Conclusion: there is a genuine configuration defect for the mean-scale mappings (`lectura_escala` and `escala_media` should reference `escala_media_m`), but the selected real Molinete measurement itself contains no scale values in `esc_ini_m`, `esc_fin_m`, or `escala_media_m`. Therefore correcting the mapping is necessary for future/other measurements but will not populate scale fields for this specific acceptance row.

MAIN-021 remains **FOLLOW-UP** until the configuration correction is implemented and the regression/full suite are rerun.

### Acceptance pause checkpoint — SIH

Work paused after the MAIN-021 diagnostic. Last fully green suite before the intentionally failing regression: **99 passed**. Current focused regression state: **1 expected FAIL** in `tests/test_sih_molinete_scale_mapping.py`, pending production/config correction.

Open SIH items at pause:
- MAIN-020: confirm SIH semantics for `id_operador`; current Molinete export carries source text `I. Pérez`, and the repository has no operator-ID lookup or authoritative mapping;
- MAIN-021: change Molinete `lectura_escala` and `escala_media` source mappings from nonexistent `escala_media` to adapter column `escala_media_m`, then rerun focused/full tests and SIH export;
- after MAIN-020/021, continue real-data SIH acceptance with Nivus (`id_tipo_aforo=57`, `id_instrumentos_rangos=10`).


### MAIN-021 production/config correction

Resumed acceptance and applied the confirmed Molinete SIH scale mapping correction in both production and acceptance configs:
- `lectura_escala: escala_media` -> `lectura_escala: escala_media_m`;
- `escala_media: escala_media` -> `escala_media: escala_media_m`.

`escala_inicio -> esc_ini_m` and `escala_fin -> esc_fin_m` were already correct and remain unchanged. For ACCM001, all three underlying scale values are known to be blank, so a regenerated export should still show blank scale fields for that specific measurement even though the mapping defect is fixed.

Verification pending: focused regression, full suite, then clean SIH real-data regeneration.


### MAIN-021 verification complete

Post-correction verification is green:
- `tests/test_sih_molinete_scale_mapping.py`: **1 passed**;
- full suite: **100 passed**.

MAIN-021 is now **MERGE**. The remaining real-data smoke rerun should confirm that FlowTracker/Molinete SIH files still generate successfully after the config-only correction; ACCM001 scale fields are expected to remain blank because the raw-canonical values themselves are blank.


### MAIN-021 real-data smoke verification complete

Clean post-fix SIH rerun for FlowTracker + Molinete generated the expected **5 files**. Semantic checker: **6/6 PASS**. Exact-ID checker: **4/4 PASS**. This confirms the Molinete scale mapping correction did not regress the accepted SIH identities/mappings. MAIN-021 is fully verified for integration.


### SIH-06 Nivus real-data acceptance

Selected deterministic real measurement: station `7001`, date `20241219`, time `214313`.

Observed normalized values:
- `q_total_m3s=0.0755909999999999`;
- `width_total_m=4.0`;
- `depth_mean_m=0.1794`;
- `area_total_m2=0.7175`;
- `velocity_mean_m_s=0.1054`.

Raw-canonical context includes `instrument=nivus`, blank `notes`, and `rh [m]=0.1725`.

Export generated exactly 3 files (actuación, aforo, metadata). Automated acceptance result: **4 PASS / 0 FAIL / 1 INFO**. Identity, metadata status, hydraulic numeric fidelity, and adopted semantic IDs all pass: `id_tipo_actuacion=4`, `id_instrumento=502`, `id_tipo_aforo=57`, `id_instrumentos_rangos=10`, `id_estacion=7001`.

The INFO is `nivel_confiabilidad=''`. This is now tracked separately as MAIN-022 rather than treated as a Nivus core-export failure. Core Nivus SIH export is accepted pending manual file review; quality-to-SIH integration remains a follow-up.


### SIH-06 manual review complete

Manual review of the uploaded Nivus SIH files confirms the automated result:
- actuación: `id_estacion=7001`, `id_tipo_actuacion=4`, `id_instrumento=502`, `fecha=19/12/2024 21:43:13`;
- aforo: `id_estacion=7001`, `id_instrumento=502`, `id_instrumentos_rangos=10`, `id_tipo_aforo=57`;
- hydraulic values match the accepted normalized row: `ancho=4.0`, `caudal=0.0755909999999999`, `profundidad=0.1794`, `seccion=0.7175`, `velocidad_media=0.1054`;
- `radio_hidraulico=0.1725` is populated from raw canonical;
- `observaciones` is blank consistently with blank raw `notes`;
- `id_operador` and `lectura_escala` are blank under the current Nivus config;
- `nivel_confiabilidad` is blank and remains tracked under MAIN-022;
- metadata reports `status=success`, authoritative station/date/time identity, and `raw_canonical_found=True`.

SIH-06 is **PASS (automated + manual) for core Nivus export**. Remaining issues are explicitly separated into MAIN-020 (operator identity contract) and MAIN-022 (quality-to-`nivel_confiabilidad` integration).


### SIH pause checkpoint after SIH-06

Work is paused with the core SIH real-data acceptance in a stable state.

Verified state at pause:
- FlowTracker + Molinete post-fix smoke: 5 files generated, semantic checker **6/6 PASS**, exact-ID checker **4/4 PASS**;
- Nivus SIH-06: **PASS automated + manual** for core export (`4 PASS / 0 FAIL / 1 INFO` automated);
- Nivus accepted IDs: `id_tipo_actuacion=4`, `id_instrumento=502`, `id_tipo_aforo=57`, `id_instrumentos_rangos=10`;
- Molinete scale mapping MAIN-021 is fully verified and marked **MERGE**;
- last fully verified Python suite: **100 passed**.

Open items to resume:
- MAIN-020 (**FOLLOW-UP**): determine the authoritative SIH contract and lookup/mapping for `id_operador`; do not invent operator IDs;
- MAIN-022 (**FOLLOW-UP**): define `nivel_confiabilidad` semantics and integrate per-measurement Nivus CG quality results regression-first;
- MAIN-023 (**FOLLOW-UP**): update stale SIH documentation/examples and `selection_template.csv` to the authoritative station-ID doctrine and adopted mappings;
- MAIN-007 (**DECIDE**): retain/review the chosen export-tables workbook metadata presentation before final integration;
- MAIN-009 (**ACCEPTED / FOLLOW-UP**): decide whether exact-duplicate FlowTracker provenance should retain both physical source paths;
- MAIN-012 (**PLACEHOLDER**): M9 ingest/export, `export excel`, filter-groups, and statistics remain incomplete. M9 SIH mapping `BOTE(59)/ADCP(12)` is configuration-only and has no real-data end-to-end acceptance yet.

Integration rule remains unchanged: do not merge the acceptance branch wholesale. Review MERGE items, resolve/defer DECIDE/FOLLOW-UP items explicitly, run a final full suite + selected real-data smoke tests, then merge through a reviewed PR.


### MAIN-023 regression stage

A focused regression suite was added before editing SIH documentation/template content. It pins three already-adopted contracts:
- `configs/sih/selection_template.csv` must not use legacy `P<digits>` station aliases;
- `docs/SIH_CONFIGURATION.md` must describe the current semantic mappings (`VADEO/BOTE`, `Velocimetro/Acustico/ADCP`) and Molinete `escala_media_m` source;
- `docs/SIH_EXPORT.md` examples must use authoritative station IDs without legacy `P` aliases.

Production documentation/template files are intentionally unchanged at this stage; the focused suite is expected to fail and demonstrate the drift before correction.


### MAIN-023 expected regression confirmed

Focused suite result before documentation/template correction: **3 failed**. The failures independently confirmed all three forms of drift: legacy `P<digits>` rows in `selection_template.csv`, stale semantic/scale examples in `SIH_CONFIGURATION.md`, and legacy `P` station examples in `SIH_EXPORT.md`.

### MAIN-023 implementation

Documentation/template content has now been synchronized with the accepted contracts:
- `selection_template.csv` now contains only verified authoritative-ID examples (`7001` Nivus, `7071` Molinete, `7071` FlowTracker);
- `SIH_CONFIGURATION.md` now documents `VADEO/BOTE`, `Velocimetro/Acustico/ADCP`, and Molinete `escala_media_m`;
- `SIH_EXPORT.md` examples now use authoritative numeric station IDs and explicitly state that no `P<n> -> 7000+n` aliasing is performed;
- the quality section retains the known MAIN-022 limitation instead of implying that `nivel_confiabilidad` is already populated.

Verification pending: rerun `tests/test_sih_docs_template_contract.py` and then the full suite.


### MAIN-023 partial verification and residual fix

First post-correction verification produced **2 PASS / 1 FAIL** in the focused suite and **102 passed / 1 failed** in the full suite. The remaining failure was narrowly scoped to two residual output-filename examples in `SIH_EXPORT.md`: the actuación filenames had been updated, but the paired aforo filenames still contained `_P8_` and `_P11_`.

Those two residual examples are now corrected to the same authoritative station/date/time identities used by their paired actuación examples (`7001 / 20241219 / 214313` and `7071 / 20260120 / 142300`). A repository-side guard confirmed no `_P<digits>_` filename fragment remains in `SIH_EXPORT.md` after the edit.

Verification pending: rerun the focused MAIN-023 suite and then the full suite.


### MAIN-023 final verification complete

Final verification after removing the last residual legacy filename examples:
- `tests/test_sih_docs_template_contract.py`: **3 passed**;
- full test suite: **103 passed**.

MAIN-023 is fully verified and promoted to **MERGE**.


### MAIN-020 client-decision checkpoint

MAIN-020 is intentionally deferred pending an external client decision. The project must ask the client what value SIH expects in `id_operador` and what authoritative operator mapping/catalogue should be used. Until that answer exists, the current evidence (`I. Pérez` for Molinete; blank for FlowTracker/Nivus) must not be converted into invented IDs. The question is tracked in `docs/CLIENT_QUERIES.md`.

### MAIN-022 scope decision

MAIN-022 is intentionally deferred. Rather than wiring the current Nivus-only CG result directly into SIH, the project will first design a broader data-quality evaluation system that covers **FlowTracker, Molinete, and Nivus**. Once that unified quality model exists, `nivel_confiabilidad` should be mapped from the per-measurement quality result under an explicit SIH contract and regression-first implementation.


### MAIN-024 regression stage

Before running section-profiles on real data, repository review found a station-selection boundary that still invents legacy `P` prefixes in both CLI and interactive helpers. A focused regression now requires `7001 -> 7001`, `7071 -> 7071`, and `P71 -> P71`. Production behavior remains unchanged until the expected failure is observed.


### MAIN-024 implementation

The expected regression failure was observed: both section-profile selection paths converted `7001` to `P7001`. The CLI and interactive helpers now delegate to shared `canonical_station_id()`, which performs representation cleanup only and preserves distinct identities such as `7001`, `7071`, and `P71`. CLI help was also updated to show authoritative numeric station-ID examples. Focused/full-suite verification is pending.
