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
| MAIN-006 | Export tables UX | Manual comparison found the current **flat Summary export** clearer and more orderly than the historical wide daily-pivot example. The historical example becomes extremely wide for long date ranges; the flat export keeps one measurement per row and a compact set of columns. | User manual review: current flat workbook judged clearer; corrected time display accepted. | **DECIDE** | Consider making flat export the documented/recommended general-purpose mode. Retain daily/monthly pivot as an explicit analytical export. If desired, evaluate whether CLI default `--grouping` should change from `monthly` to `none`; do not change this automatically without product decision. |
| MAIN-007 | Export tables metadata | Current workbook includes separate `export` and `metadata` sheets plus metadata sidecar. This was clearer than the historical wide output during the first manual review. | Workbook structure and metadata checks pass. | **DECIDE** | Keep the two-sheet structure unless later manual testing identifies a better user-facing layout. Review metadata wording for end-user clarity during later export tests. |
| MAIN-008 | Station identity downstream | `src/aforix/metadata.py::canonical_station_id()` still contains a legacy semantic mapping `P<n> -> 7000+n`, and some downstream/export/analysis helpers call canonical station logic. This is inconsistent with the current rule that raw station number is authoritative and must not be semantically renumbered. | Not triggered in the accepted normalization path because current station policy does not enable canonical remapping. | **FOLLOW-UP** | Before merge completion, audit every downstream caller of `canonical_station_id` and any manual-stage/analysis station normalization. Add regression tests before changing behavior. |
| MAIN-009 | FlowTracker exact duplicate source files | 30 physical FlowTracker files correspond to 29 unique measurements because one pair is binary-identical and has identical station/date/time. Current build/ingest outputs represent the unique measurement once. | Duplicate pair independently confirmed by hash and metadata. | **ACCEPTED / FOLLOW-UP** | Scientifically acceptable under current duplicate rule. Consider whether provenance should retain both physical source paths even when payload is collapsed. |
| MAIN-010 | Nivus source QC | Nine Nivus points have no valid gate observations in the raw source. | Raw-to-normalized field checks show no ingestion loss; issue is source-data QC. | **ACCEPTED** | Keep as QC information; do not “repair” in normalization. |
| MAIN-011 | Negative flow observations | Pipeline audit reports 236 informational range flags associated with negative flow values; no warning/error range findings. | Hydraulic/unit checks remain clean; production validation range rules pass. | **ACCEPTED** | Preserve signed flow. Keep negative-flow reporting informational unless domain rules change. |
| MAIN-012 | Placeholder commands | `export excel`, M9 ingest, filter-groups, and statistics analysis are not complete production implementations in the audited codebase. | Structural review during acceptance campaign. | **PLACEHOLDER** | Keep clearly documented as incomplete; test/implement separately rather than treating CLI presence as acceptance. |
| MAIN-013 | SIH acceptance isolation | Default SIH config still points to standard database/output paths rather than acceptance-specific paths. | Identified during pipeline mapping; SIH acceptance not yet executed. | **FOLLOW-UP** | Create/use an isolated SIH acceptance config before real-data SIH tests. |

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
