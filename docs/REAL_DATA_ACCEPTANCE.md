# Real-data acceptance campaign

This campaign validates Aforix function-by-function with real source data while keeping generated acceptance outputs isolated from the normal working database.

## Isolation

- Real RAW inputs remain in `data/raw` and are treated as read-only.
- Acceptance runs: `runs_acceptance/`
- Acceptance database: `database_acceptance/`
- Acceptance exports: `outputs_acceptance/`
- Main acceptance config: `configs/examples/acceptance_real.yaml`

## Acceptance sequence

1. Baseline inventory of real RAW files.
2. `config-check`.
3. Ingest: FlowTracker, Molinete, Nivus.
4. `build-groups`.
5. `normalize run`.
6. Technical audit + `validate run`.
7. Exports.
8. External-source converters.
9. Analyses.
10. Batch orchestration.
11. Separate review of placeholders/legacy commands.

## Result states

- PASS: verified correct against real source data or an independently calculated expectation.
- WARN: function works, with a known limitation or data condition.
- FAIL: incorrect result; add a regression test before fixing.
- NOT IMPLEMENTED: command exists but the underlying function is still a placeholder.

## Baseline inventory

Run from repository root:

```powershell
python .\scripts\acceptance_inventory.py
```

This writes SHA-256-based physical inventory files under `runs_acceptance/_inventory` without modifying RAW inputs.


## Baseline real-data inventory — 2026-10-01

The first acceptance inventory was generated successfully from the user's real local RAW corpus.

| Instrument | Physical files | Unique SHA-256 | Exact duplicate files | Acceptance interpretation |
| --- | ---: | ---: | ---: | --- |
| FlowTracker | 30 | 29 | 1 | 29 unique source measurements plus one exact duplicate copy |
| Molinete | 13 | 13 | 0 | 13 unique source files |
| Nivus | 214 | 208 | 6 | 208 unique source measurements plus six exact duplicate copies |
| M9 | 0 | 0 | 0 | No real M9 acceptance data available |
| **TOTAL** | **257** | **250** | **7** | **250 unique RAW payloads** |

Known exact duplicate FlowTracker pair:

- `11900205.dis`
- `119020160205.dis`
- SHA-256: `32fd2e6983dfca0b29d80f6051b97d822a2df2ac8d5d10722030d8387032632f`

Nivus contains six exact duplicate pairs, each represented by an original XML and a `_1.xml` copy.

This 250-unique-payload baseline is consistent with the previously validated 250 hydraulic measurements and will be used as the expected corpus size unless a later identity-level audit proves that two non-identical files represent the same measurement.

## Campaign status

| ID | Function | Status | Evidence |
| --- | --- | --- | --- |
| BASE-01 | RAW physical inventory | PASS | 257 physical files, 250 unique SHA-256 payloads |
| CFG-01 | `aforix config-check` using `acceptance_real.yaml` | PASS | Configuration loaded successfully |
| ING-FT | FlowTracker ingest | PASS | 30 physical RAW files; 29 unique measurement outputs; isolated acceptance run confirmed |
| ING-ML | Molinete ingest | PASS | 13/13 real measurements passed independent RAW-to-ingest checks |
| ING-NV | Nivus ingest | PASS | 208/208 unique real measurements passed independent XML-to-ingest checks |


### Acceptance infrastructure issue discovered during ING-FT

`paths.runs_root: runs_acceptance` is currently ignored by `create_run()`, which hard-codes the root directory as `runs/`. The FlowTracker acceptance run therefore completed successfully but was written under the normal `runs/` tree.

A regression test was added first in `tests/test_runs_manager.py`. It defines the required behavior: `create_run()` must honor the configured `paths.runs_root` relative to the project root. The production fix will be applied only after the failing regression test is confirmed.


### runs_root fix

After the failing regression test confirmed the issue, `create_run()` was updated to resolve `paths.runs_root` from the active project configuration instead of hard-coding `runs/`. Relative roots are resolved from the project root; absolute roots are preserved. The acceptance campaign must re-run the regression test before proceeding.


### Regression verification — runs_root

Verified locally after the fix:

- `pytest -q tests/test_runs_manager.py`: **1 passed**
- full suite `pytest -q`: **77 passed**

The configured `paths.runs_root` behavior is now covered by regression testing and the full test suite remains green.


### ING-FT final acceptance verification

After the `runs_root` fix, the real-data FlowTracker acceptance run was created under the isolated acceptance tree:

- run root: `runs_acceptance/ingest_flowtracker/20261001_215942`
- Summary outputs: **29**
- Points outputs: **29**

This matches the expected 29 unique FlowTracker measurements from 30 physical RAW files with one exact duplicate pair. ING-FT is accepted for the current real-data corpus.


### ING-ML structural verification

Real-data Molinete ingest produced:

- run: `runs_acceptance/ingest_molinete/20261001_220110`
- Summary outputs: **13**
- Points outputs: **13**

This matches the baseline of 13 unique Molinete RAW Excel files. Numerical/source fidelity remains to be checked before final PASS.


### ING-ML final acceptance verification

Independent real-data Molinete acceptance check completed successfully:

- run: `runs_acceptance/ingest_molinete/20261001_220110`
- Summary files: **13**
- Points files: **13**
- measurements checked: **13**
- PASS: **13**
- FAIL: **0**

The independent checker opened the RAW Excel files directly and compared station identity plus total discharge, area, mean velocity, Points sums, and point counts against Aforix ingest outputs. ING-ML is accepted for the current real-data corpus.


### ING-NV structural verification

Real-data Nivus ingest produced:

- run: `runs_acceptance/ingest_nivus/20261001_220512`
- Summary outputs: **208**
- Points outputs: **208**
- Sections outputs: **208**
- Gates outputs: **208**

This matches the baseline of 214 physical XML files with six exact duplicate copies, leaving 208 unique payloads/measurement outputs. XML-to-CSV field fidelity remains to be checked before final PASS.


### ING-NV final acceptance verification

Independent real-data Nivus acceptance check completed successfully:

- run: `runs_acceptance/ingest_nivus/20261001_220512`
- measurements checked: **208**
- PASS: **208**
- FAIL: **0**
- Summary rows: **208**
- Points rows: **3147**
- Sections rows: **3563**
- Gates rows: **100704**
- metadata mismatches: **0**
- row-count mismatches: **0**
- field mismatches: **0**

The independent checker parsed the real XML files directly and compared metadata, row counts, and source fields against all four Aforix ingest groups. ING-NV is accepted for the current real-data corpus.


### GRP-01 checker correction

The first build-groups acceptance check reported two failures only for concatenated `Summary` groups (FlowTracker and Nivus), while all six file-based group checks and the 916-row manifest passed. Inspection showed the production build orders concatenated Summary rows by the configured deduplication identity key, whereas the acceptance checker had concatenated expected rows in filename order and compared row-by-row.

The checker was corrected to align concatenated rows by measurement identity (`instrument`, `station_id`, `measurement_date`, `measurement_time`, `source_file`) before comparing values. No production build-groups code was changed. GRP-01 remains pending until the corrected checker is rerun.


### GRP-01 final acceptance verification

Corrected build-groups acceptance check completed successfully:

- group checks: **8**
- PASS: **8**
- FAIL: **0**
- manifest expected rows: **916**
- manifest rows: **916**
- manifest selected: **916**
- manifest status: **PASS**

This verifies that the latest isolated ingest runs were consolidated into `database_acceptance/raw_canonical` without row loss or content drift, and that all selected source CSVs are represented in the manifest.


### GRP-01 final acceptance verification

The corrected build-groups acceptance checker passed completely:

- group checks: **8**
- PASS: **8**
- FAIL: **0**
- manifest expected rows: **916**
- manifest rows: **916**
- manifest selected: **916**
- manifest status: **PASS**

GRP-01 is accepted for the current real-data corpus.


### NORM-01 first acceptance run

Normalization completed in the isolated acceptance tree with **669 normalized outputs**, plus cross-instrument concatenations of Summary and Points. The global concatenations contain **250 Summary rows** and **3977 Points rows**.

The first acceptance checker produced 4 PASS / 6 FAIL, but all six failures were checker assumptions about pre-normalization representation rather than observed data loss: Molinete dates/times legitimately change from `YYYY-MM-DD` / `HH:MM:SS` to configured canonical `YYYYMMDD` / `HHMMSS`, and raw point/section/gate indices use instrument-specific source column names that normalize to canonical index columns. The checker was updated to compare canonical logical identity and source aliases. Production normalization code was not changed.

The general audit simultaneously reported all 669 raw and normalized column checks OK, all 750 hydraulic checks OK, and all 461 unit-consistency checks OK. Duplicate/range audit findings are retained for separate diagnosis before validation is closed.


### NORM-01 final acceptance verification

The corrected normalization acceptance checker completed with **10 PASS / 0 FAIL**. Cross-instrument concatenations contain **250 Summary rows** and **3977 Points rows**, matching the expected corpus.

The acceptance audit also shows:
- raw column checks: **669/669 OK**
- normalized column checks: **669/669 OK**
- hydraulic consistency: **750/750 OK**
- unit consistency: **461/461 OK**
- range flags: **236**, all informational negative-flow observations; **no warning/error range findings**

NORM-01 is accepted for the current real-data corpus.

A separate audit-script issue remains open: four FlowTracker Points files are reported as duplicate-bearing because the standalone audit currently keys Points only by `point_index`; FlowTracker can legitimately contain the same vertical at multiple `percent_depth` values. The production validation duplicate check already handles this correctly. A regression test was added before changing the audit implementation.


### Audit duplicate regression test harness

The first regression-test run failed during test collection because `scripts/` is not a Python package and therefore `from scripts.audit_pipeline_outputs import ...` is not importable in the installed test environment. The test harness was corrected to load the standalone audit script explicitly by file path. Production code remains unchanged; the regression assertion still needs to fail before the audit implementation is modified.


### Audit duplicate regression test harness — second correction

The explicit file-path import still failed during collection because the dynamically created module was not registered in `sys.modules` before execution; `dataclasses` relies on that registration while decorating `TableRef`. The test harness now registers the module before `exec_module`. Production audit code remains unchanged; the next run should reach the intended duplicate assertion.


### Audit duplicate false-positive fix

The regression test now reaches the intended assertion and fails because the standalone audit labels two FlowTracker rows with the same `point_index` but different `percent_depth` as duplicates. The audit duplicate key was corrected to mirror production validation semantics: FlowTracker Points use measurement identity + `point_index` + `percent_depth`. A guard test was also added to confirm that rows with the same `point_index` and same `percent_depth` are still reported as true duplicates.


### Post-fix audit verification

The FlowTracker audit duplicate-key fix was verified locally:

- targeted audit tests: **2 passed**
- full test suite: **79 passed**
- raw column audit: **669/669 OK**
- normalized column audit: **669/669 OK**
- duplicate audit: **461 OK**, **208 not_checked** (Nivus Gates; no reliable unique key defined), **0 duplicate findings**
- hydraulic consistency: **750/750 OK**
- unit consistency: **461/461 OK**
- range audit: **1179 OK**, **236 informational flags** (negative flow observations), with no warning/error findings

The standalone audit and production duplicate validation semantics are now aligned for FlowTracker multi-depth verticals.


### VAL-01 final acceptance verification

Production validation completed successfully against the isolated normalized acceptance database:

- acceptance checks: **6**
- PASS: **6**
- FAIL: **0**
- validation summary rows: **5**
- required-column rows: **25**
- duplicate rows: **0**
- completeness rows: **10**
- range rows: **0**
- hydraulic rows: **250**

The five production validation checks (`required_columns`, `duplicates`, `completeness`, `ranges`, and `hydraulic_consistency`) all resolve to `ok`. VAL-01 is accepted for the current real-data corpus.


### EXP-TABLES configuration isolation — regression test

Before running real exports, inspection found that the tables-export configuration helper still reads legacy keys (`project.database_root`, `project.runs_root`, and top-level `export_tables`) while the current main config uses `paths.database_root`, `paths.runs_root`, and `export.tables`. A regression test was added first to require the acceptance config to resolve its normalized input to `database_acceptance/normalized` and output to `outputs_acceptance/tables`. Production export code has not yet been changed.


### User-facing output acceptance protocol

From the export stage onward, acceptance uses two complementary layers:

1. **Automated verification** — file existence, row/column counts, filters, calculations, source traceability, metadata, naming, and isolation under acceptance output roots.
2. **Manual user review** — open the produced CSV/XLSX files as an end user would and verify readability, headings, ordering, units, station/date identity, representative numeric values against normalized source data, empty-cell behavior, and whether the result is practically usable without interpretation of internal implementation details.

Manual review findings are recorded separately from automated failures so presentation/usability issues are not hidden by technically correct data.


### EXP-TABLES config fallback correction

The current acceptance-path test passed, confirming that the modern config structure now resolves `database_acceptance/normalized` correctly. The remaining failure was limited to the legacy/standalone-config compatibility test: when a config file is outside a repository tree, `_infer_repo_root()` fell back to the process working directory, making relative paths depend on where the command was launched. The fallback was corrected to the config file's own directory, while repository-contained configs still resolve from the repository root.


### EXP-TABLES configuration verification

The export-tables path-resolution fixes were verified locally:

- targeted export config tests: **2 passed**
- full test suite: **81 passed**

The modern acceptance config resolves to `database_acceptance/normalized` for input and `outputs_acceptance/tables` for output, while standalone legacy configs remain supported.


### EXP-TABLES-01 — first user-facing workbook

The first manual+automated export case is a flat all-instrument `Summary` workbook with only user-relevant hydraulic columns. The automated checker verifies 250 rows, exact fidelity against normalized Summary data, preservation of long station IDs (including 701190/701150/70101), sidecar metadata, and workbook sheets. Manual review focuses on readability, field order, station/date/time presentation, units/column naming, representative values, and whether the workbook is practical to use without internal Aforix knowledge.


### EXP-TABLES-01 first manual review — time formatting defect

The first real user-facing Summary workbook contained the expected 250 rows and was manually judged acceptable in the other reviewed aspects, but the user identified a presentation/data-fidelity defect in `measurement_time`: leading zeros were lost (for example `091500` appeared as `91500`). The automated source-fidelity check independently caught the same defect (for example source `093425` vs exported `93425`).

Inspection of the workbook confirmed that `station_id`, `measurement_date`, and `measurement_time` had been written as numeric cells. Root cause: the export loader used default pandas type inference when reopening normalized CSVs, so six-digit time identity strings could be coerced to integers before XLSX writing.

The export loader now keeps `station_id`, `measurement_date`, and `measurement_time` as strings while continuing to infer hydraulic measurement columns numerically. A focused regression test verifies the XLSX cell value and type for a leading-zero time. EXP-TABLES-01 remains pending until the workbook is regenerated, the automated checker passes, and the corrected time is manually confirmed.


### EXP-TABLES-01 checker numeric-equivalence correction

After the leading-zero time fix, the regenerated workbook preserved `085851` correctly. The remaining automated failure was not a workbook defect: the checker compared numeric hydraulic values as strings, so Excel's equivalent serialization of `109.0` as `109` (and `12.0` as `12`) was treated as a mismatch. The checker now compares identity fields exactly as text and hydraulic fields numerically with tight tolerance. Production export code was not changed for this second issue.


### Legacy `station_code` discovered during manual review

Manual review of a normalized Summary file showed that authoritative `station_id` values are now correct and P-free (for example `7001`, `70101`, `701150`), but a legacy `station_code` column is still being generated as `P` + `station_id` (for example `P7001`, `P701150`). The column carries no independent station identity and is not used by the current SIH station mapping, which reads `station_id` directly.

The older export example also demonstrates the historical behavior: its exported `station_id` values were P-prefixed (for example `P7003`, `P7008`, `P7013`). The current flat export correctly uses P-free `station_id` values.

The target behavior for the current pipeline is now explicitly tested: current normalization configs must not generate the legacy `station_code`, and the normalizer must not force that column when it is not requested. Production code/config has not yet been changed; the regression tests should fail first.


### Legacy `station_code` production fix

The regression tests failed as expected: the current normalization YAMLs still enabled `station_code: P...`, and the normalizer forced an empty `station_code` column even when no policy requested it.

The production pipeline was corrected as follows:

- removed P-prefixed `station_code` generation from the current FlowTracker, Molinete, and Nivus normalization specs;
- removed `station_code` from the normalizer's mandatory traceability columns;
- aligned the standalone pipeline auditor with the P-free normalized schema;
- retained the generic metadata capability to create a `station_code` only when a project-specific policy explicitly requests it.

Existing normalized acceptance files still contain the old column until normalization is rerun; the next acceptance step must regenerate normalized outputs and re-run the normalization/validation checks.


### Manual verification after station_code removal

The regenerated acceptance `Summary.csv` was manually inspected in PowerShell. Confirmed:

- `station_code` is absent from the normalized Summary schema;
- `station_id` is the first station-identity column;
- querying for `station_id` values beginning with `P` returned no rows.

The follow-up spot check for specific long IDs still needs to be executed; the user's later PowerShell commands were wrapped in `{ ... }`, which creates a script block instead of running the pipeline.


### Post-station-code full verification

After regenerating normalized data without the legacy `station_code` column:

- manual spot-check preserved IDs `70101`, `701150`, `701190`, and `7071` across FlowTracker/Molinete/Nivus;
- no `station_id` beginning with `P` was found;
- normalize acceptance: **10/10 PASS**;
- cross-instrument Summary: **250 rows**;
- cross-instrument Points: **3977 rows**;
- raw column audit: **669/669 OK**;
- normalized column audit: **669/669 OK**;
- duplicate audit: **0 duplicate findings**;
- hydraulic consistency: **750/750 OK**;
- unit consistency: **461/461 OK**;
- production validation acceptance: **6/6 PASS**;
- station-code regression tests: **2 passed**;
- complete test suite: **84 passed**.

A separate `docs/MAIN_IMPROVEMENTS_REGISTER.md` now tracks acceptance findings that must be merged, decided, or followed up before updating `main`.


### Downstream station identity — regression stage

Source inspection confirmed that legacy station aliasing survives in downstream modules even though the accepted normalized database is now P-free. A regression suite was added before production changes. It covers core canonical station handling, export-table filtering, batch point parsing, manual-stage conversion, quality, section-profiles, stage-discharge, and protection of the distinct `Pm<n>` model-point namespace.

Expected current result: failures showing `P71 -> 7071` aliasing and manual-stage generation of `P<n>`.

### Downstream station identity — production correction

The regression suite failed in five expected places, confirming that semantic aliasing was active in the shared metadata helper, export filters, batch parsing, manual-stage conversion, and analysis input boundaries.

Production corrections were then applied:

- `canonical_station_id()` is now representation-only and no longer maps `P<n>` to `7000+n`;
- manual-stage conversion preserves the supplied station identity instead of inventing a `P` prefix;
- correlation station sorting accepts distinct nonnumeric namespaces;
- the interactive correlation prompt no longer advertises legacy P aliases;
- older tests encoding the deprecated semantic mapping were updated to the authoritative-identity rule.

Verification is pending the targeted and full pytest runs.


### Downstream identity verification — stale test expectation corrected

The targeted downstream suite passed **6/6** after the production fix. The broader metadata/boundary run exposed three remaining failures, all in one parameterized export-boundary test whose expected values still encoded the old `P<n> -> 7000+n` mapping. Production behavior was already correct (`P1 -> P1`, `P71 -> P71`, `P101 -> P101`). The stale test expectations were corrected, and the correlation CLI help was also updated to stop advertising legacy P aliases.


### Downstream station identity — final verification

Verification after the production correction is complete:

- `tests/test_station_identity_downstream.py`: **6 passed**;
- `tests/test_metadata.py tests/test_canonical_point_boundaries.py`: **29 passed**;
- full suite: **90 passed**.

The authoritative-ID rule is now enforced across the audited downstream boundaries: no semantic `P<n> -> 7000+n` aliasing, no manual-stage P-prefix invention, and `Pm<n>` remains a distinct model-point namespace.


### EXP-TABLES-01 final acceptance

The final flat all-instrument Summary workbook was regenerated after station-identity cleanup.

Automated acceptance:
- rows exported: **250**
- checks: **6**
- PASS: **6**
- FAIL: **0**

Manual acceptance:
- workbook layout judged clear and usable;
- no legacy `station_code` column;
- six-digit times preserved;
- long station IDs remain intact.

EXP-TABLES-01 is **PASS (automated + manual)**.


### EXP-TABLES-02 — exact station/date filtered CSV

Next case verifies non-interactive filters and CSV output using a domain-significant same-day example:

- table: `Summary`
- station_id: `7071`
- date: `20260120`
- instrument: `all`
- expected measurements: **2** (FlowTracker + Molinete, distinct times)

This case checks exact station matching, date filtering, retention of multiple same-day measurements, CSV identity formatting, numeric fidelity, and metadata.


## Pause / resume checkpoint — 2026-10-02

Acceptance work paused here by user request.

### Closed before pause
- ING-FT: PASS
- ING-ML: PASS
- ING-NV: PASS
- GRP-01 build-groups: PASS
- NORM-01: PASS
- VAL-01: PASS
- EXP-TABLES-01 flat all-instrument Summary XLSX: **PASS automated + PASS manual**
- downstream station identity audit: closed; authoritative station IDs preserved; full suite **90 passed**
- legacy `station_code` removed from current normalized outputs

### Current verified state
- unique real measurements: **250**
- normalized Summary rows: **250**
- normalized Points rows: **3977**
- duplicate findings: **0**
- hydraulic audit: **750/750 OK**
- unit audit: **461/461 OK**
- validation acceptance: **6/6 PASS**
- full pytest suite: **90 passed**

### Exact next step when work resumes
Continue with **EXP-TABLES-02 — exact station/date filtered CSV**.

Planned test case:
- table: `Summary`
- station_id: `7071`
- date: `20260120`
- instrument: `all`
- format: CSV
- expected rows: **2**
  - FlowTracker at `141519`
  - Molinete at `142300`

Commands to resume:

```powershell
git pull

python -m aforix.export.tables.cli `
  -c configs/examples/acceptance_real.yaml `
  --table Summary `
  --instrument all `
  --points 7071 `
  --early-date 20260120 `
  --late-date 20260120 `
  --grouping none `
  --format csv `
  --parameters q_total_m3s q_total_ls

python .\scripts\acceptance_check_export_tables_filtered_csv.py
```

Manual review after the checker:
- exactly 2 rows;
- both with `station_id=7071`;
- distinct times preserved;
- no aggregation/collapse of the two same-day measurements;
- `q_total_m3s` and `q_total_ls` remain coherent.


### EXP-TABLES-02 automated verification

The exact-station/date filtered Summary CSV export completed successfully for station `7071` on `20260120`.

Automated acceptance:
- rows exported: **2**
- checks: **5**
- PASS: **5**
- FAIL: **0**
- expected same-day measurements retained independently: FlowTracker + Molinete
- exact station/date filtering, identity fidelity, numeric fidelity, and metadata all passed

Manual user review is still pending before EXP-TABLES-02 is closed.


### EXP-TABLES-02 final acceptance

Manual review confirmed the filtered CSV is correct and usable. The two expected same-day measurements for station `7071` were preserved independently.

EXP-TABLES-02 is **PASS (automated + manual)**.


### EXP-TABLES-03 — instrument + inclusive date-range XLSX

Next case verifies simultaneous instrument/date filtering on Summary and XLSX output:

- instrument: `flowtracker`
- date range: `20260119` through `20260122` inclusive
- grouping: `none`
- format: XLSX
- parameters: q, area, mean velocity

The checker derives the expected row count directly from normalized Summary data and verifies exact row identity/numeric fidelity, filter boundaries, absence of legacy `station_code`, P-free authoritative IDs, and metadata.


### EXP-TABLES-03 final acceptance

The FlowTracker Summary XLSX export for the inclusive date range `20260119` through `20260122` completed successfully.

Automated acceptance:
- rows exported: **8**
- checks: **6**
- PASS: **6**
- FAIL: **0**

Manual acceptance:
- workbook reviewed by the user and judged correct;
- instrument/date filtering is clear;
- authoritative station IDs and time formatting remain intact;
- selected hydraulic fields are presented correctly.

EXP-TABLES-03 is **PASS (automated + manual)**.


### EXP-TABLES-04 — daily pivot XLSX

Next case tests the grouped/pivot branch of `export tables` using the same FlowTracker date window as EXP-TABLES-03:

- instrument: `flowtracker`
- date range: `20260119` through `20260122`
- grouping: `daily`
- aggregation: `mean`
- format: XLSX
- parameters: `q_total_ls`, `area_total_m2`

The checker independently builds the expected daily pivot from normalized Summary data and verifies period-major columns, complete date coverage (including dates with blank cells), station rows, numeric mean fidelity, and metadata.


### EXP-TABLES-04 automated pass + manual UX decision

The daily pivot workbook passed all structural/numeric checks:

- rows: **8**
- checks: **6**
- PASS: **6**
- FAIL: **0**

Manual review reached a product/UX conclusion: although the pivot is technically correct, the user prefers the newer **flat** layout because it is easier to read and use. The pivot layout resembles the older wide workbook format and becomes less readable as dates/parameters grow.

Decision for the new Aforix version:
- **flat** should be the default/recommended general-purpose table export;
- **daily/monthly pivot** should remain available only when explicitly requested for analytical use.

A regression test is added before changing the CLI default.


### Flat export default — production correction

The regression test failed as expected because the non-interactive CLI still defaulted to `grouping=monthly`.

Production behavior is now changed so the new general-purpose default is the accepted flat layout:

- non-interactive CLI `--grouping` default: `none`;
- interactive export prompt default: `none`;
- `daily` and `monthly` pivot exports remain available when explicitly selected.

Verification is pending the focused regression test and full pytest suite.


### Flat export default — final verification

The production default change was verified successfully:

- `tests/test_export_tables_defaults.py`: **1 passed**;
- full suite: **91 passed**.

The new Aforix table-export default is therefore the flat layout (`grouping=none`) for both CLI and interactive modes. Pivot remains an explicit analytical option.


### EXP-TABLES-05 — monthly pivot technical verification

Because pivot is retained as an explicit analytical option, monthly grouping is tested separately even though flat is now the default presentation.

Test case:
- table: `Summary`
- instrument: `flowtracker`
- date range: `20251101` through `20260131`
- grouping: `monthly`
- aggregation: `mean`
- format: XLSX
- parameters: `q_total_ls`, `area_total_m2`

This is a technical acceptance case; no preference reversal is implied. The checker independently reconstructs monthly means and verifies period-major columns, station rows, numeric fidelity, explicit month coverage, and metadata.


### EXP-TABLES-05 final acceptance

The explicit monthly pivot FlowTracker Summary export completed successfully.

Automated acceptance:
- rows exported: **16**
- checks: **6**
- PASS: **6**
- FAIL: **0**

This confirms that monthly pivot remains technically correct as an explicit analytical option. The product decision is unchanged: flat remains the default/recommended general-purpose layout.


### Interactive export selection — regression stage

Before executing a real interactive export, source inspection found an ambiguity in `_choose_many()`: bare numeric input is interpreted as a list index before exact station-code matching. With numeric authoritative station IDs, selection should be unambiguous.

Target rule:
- when selecting stations (`allow_codes=True`), an exact station ID such as `7071` must select station `7071`;
- list-index selection must be explicit via `idx:N` or `[N]`;
- legacy P-code guidance should be removed.

A regression test was added before production changes.


### Interactive station selection regression harness correction

The first regression test unexpectedly passed because the chosen station ID (`7071`) was far outside the available list-index range, so the existing code naturally fell through to exact station-code matching. That did not exercise the ambiguous branch.

The regression case was corrected to use station ID `1` in a list where index `1` points to a different station. This now tests the actual ambiguity: for station selection, bare `1` must mean exact `station_id=1`, while explicit `idx:1` remains the index-selection syntax. Production code is still unchanged pending the intended failure.


### Interactive station selection regression harness — second correction

The second test still passed because station ID `1` was accidentally placed at list index `1`, so both interpretations selected the same value. The harness is corrected again so station `1` is at index `0` while index `1` is station `7001`.

Expected behavior:
- bare `1` -> exact station ID `1`;
- explicit `idx:1` -> station `7001`.

Production code remains unchanged until the corrected test demonstrates the ambiguity.


### Interactive station selection — production correction

The corrected regression test reached the intended failure:

- bare input `1` was incorrectly interpreted as list index 1;
- station `7001` was selected instead of authoritative station ID `1`;
- explicit `idx:1` behaved as intended.

Production interactive selection was corrected so that when selecting stations, exact station IDs are matched before any bare numeric index interpretation. Index selection now remains explicit via `idx:N` or `[N]`. Legacy P-code wording in the validation message was also removed.

Verification is pending the targeted test and full suite.


### Interactive station selection — targeted verification

The focused regression suite passed after the production correction:

- `tests/test_export_tables_interactive_selection.py`: **2 passed**.

Full-suite verification is still pending before MAIN-015 is closed.


### Interactive station selection — final verification

Verification after the production correction is complete:

- focused regression suite: **2 passed**;
- full test suite: **93 passed**.

MAIN-015 is closed as verified.


### EXP-TABLES-06 — real interactive flat XLSX export

This case exercises the actual menu-driven export path after MAIN-006 and MAIN-015:

- table: `Summary`
- instrument: `all`
- station: exact authoritative ID `7071`
- parameters: `q_total_m3s q_total_ls`
- date range: `20260120` to `20260120`
- grouping: accept default `none`
- aggregation: accept default `mean` (irrelevant for flat output)
- format: accept default `xlsx`

Expected output is the same two independent same-day measurements previously accepted in EXP-TABLES-02, now reached through the interactive workflow. Automated and manual review are both required.
