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


### EXP-TABLES-06 final acceptance

The real menu-driven flat XLSX export passed both automated and manual review.

Automated acceptance:
- rows exported: **2**
- checks: **6**
- PASS: **6**
- FAIL: **0**

Manual acceptance:
- the interactive workflow was judged clear;
- the generated XLSX was judged correct;
- the accepted flat layout remained intact.

EXP-TABLES-06 is **PASS (automated + manual)**.


### Export tables flat override — regression stage

Before closing the export-tables module, source inspection found a contract mismatch: CLI help says `--flat` prevents pivoting even when `--grouping daily/monthly` is supplied, but the runner currently still builds a pivot whenever grouping is daily/monthly. Filename and metadata also continue to describe a grouped pivot.

Target rule:
- explicit flat mode (`pivot=False`) must produce row-wise flat output;
- effective grouping must be `none`;
- filename and metadata must describe a flat export.

A regression test was added before production changes.


### Export tables flat override — production correction

The regression test failed as intended: `grouping=daily` with `pivot=False` still generated pivoted date columns instead of a row-wise flat export.

Production runner behavior is now corrected so explicit flat mode is authoritative. When `pivot=False`:
- effective grouping is `none`;
- the output is built with the flat path;
- filename shape is `flat`;
- metadata reports flat semantics consistently.

Verification is pending the focused regression and full pytest suite.


### Export tables module — final acceptance

MAIN-016 verification completed successfully:

- `tests/test_export_tables_flat_override.py`: **1 passed**;
- full suite: **94 passed**.

The `export tables` module is now accepted for the current campaign. Verified capabilities include:
- flat XLSX/CSV exports;
- exact station/date/instrument filters;
- preservation of authoritative station/date/time identity;
- interactive export workflow;
- daily and monthly pivot as explicit analytical options;
- flat as the default/recommended layout;
- explicit `--flat` override semantics.

EXP-TABLES is **PASS (module complete for current scope)**.


### SIH-01 — isolated batch export setup

After closing `export tables`, the next module is SIH export.

Acceptance isolation is now explicit:
- normalized input: `database_acceptance/normalized`;
- raw canonical input: `database_acceptance/raw_canonical`;
- quality input: `database_acceptance/analysis/quality_metrics`;
- output: `outputs_acceptance/sih`;
- SIH config: `configs/sih/sih_acceptance.yaml`;
- selection: `configs/sih/selection_acceptance.csv`.

The first batch case intentionally selects two independent measurements for authoritative station `7071` on the same date:
- FlowTracker `20260120 141519`;
- Molinete `20260120 142300`.

The checker validates isolation, metadata success/identity, expected SIH files, exact SIH schemas, station/date/time identity, and normalized hydraulic-value fidelity. This first run is allowed to expose configuration/lookup defects; they will be diagnosed regression-first rather than hidden.


### SIH-01 automated acceptance

The isolated batch SIH export completed successfully for the two selected real measurements.

Execution:
- generated files: **5** (2 actuaciones, 2 aforos, 1 metadata);
- selection rows: **2**;
- checker: **6/6 PASS**;
- output remained isolated under `outputs_acceptance/sih`;
- both same-day station `7071` measurements remained distinct;
- station/date/time identity and normalized hydraulic values matched the accepted normalized Summary data.

SIH-01 is **PASS for structural/identity/numeric export behavior**. Manual inspection of user-facing SIH CSV fields remains useful, and semantic lookup completeness is tested separately in SIH-02.


### SIH-02 — semantic lookup completeness diagnostic

SIH-01 proved that files can be generated correctly at the structural, identity, and normalized-value levels. The next check deliberately audits semantic IDs that SIH configuration says should be resolved:

- `id_instrumento`;
- `id_tipo_actuacion`;
- `id_tipo_aforo`;
- `id_instrumentos_rangos`.

The diagnostic also checks whether each configured `tipo_aforo_lookup` and `instrumentos_rangos_lookup` key has exactly one match in the current lookup CSVs, using only representation-normalized comparison (trim/case). It does **not** invent or substitute domain IDs when a configured concept is absent from the lookup table.


### SIH-02 diagnostic result

Result: **2 PASS / 4 FAIL**.

The failures are not one single defect:

1. **Textual representation mismatch — code defect candidate**
   - configured: `tipo_aforo_lookup: Vadeo`;
   - lookup contains `VADEO`;
   - the acceptance diagnostic deliberately normalizes case/outer whitespace and finds exactly one semantic match;
   - production lookup uses exact string comparison, so both exported `id_tipo_aforo` values are blank.
   - A focused regression test is added before production changes.

2. **Missing semantic mapping — configuration/domain-data issue**
   - configured: `instrumentos_rangos_lookup: Velocimetro puntual`;
   - current lookup values are `Barra 20 mm`, cable/barra combinations, `Todos los casos`, and `Acustico`;
   - there is no `Velocimetro puntual` entry to resolve.
   - No substitute ID will be guessed.

Fields already confirmed populated in the two real exports:
- `id_tipo_actuacion = 4`;
- FlowTracker `id_instrumento = 501`;
- Molinete `id_instrumento = 19`.

Manual visual review remains pending.


### SIH-02a — textual lookup production correction

The regression failed as intended: `resolve_tipo_aforo_lookup_id()` returned blank for configured `Vadeo` when the lookup row was `VADEO`.

Production matching is now representation-normalized using trim + case-insensitive comparison only. No domain aliases are introduced.

Expected consequence:
- `Vadeo` -> existing SIH lookup ID `57` (`VADEO`);
- `Velocimetro puntual` remains unresolved because it is absent from the current `instrumentos_rangos.csv`.

Focused and full-suite verification are pending.


### SIH-02a verification + interrupted real-data rerun

Code verification after the textual lookup fix:
- focused regression: **1 passed**;
- full suite: **95 passed**.

The attempted real-data regeneration then failed only at the final metadata write with:

`PermissionError: outputs_acceptance/sih/sih_export_metadata.csv`

The output directory had just been opened for manual review. On Windows, an open CSV can prevent deletion/overwrite; the cleanup command used `-ErrorAction SilentlyContinue`, so a locked file could have prevented a truly clean directory reset without being visible in the console.

Therefore the subsequent semantic checker result is **not accepted as a clean rerun**. Molinete already shows `id_tipo_aforo=57`, but FlowTracker still shows blank and may be stale. Re-run only after closing all SIH CSVs/Excel windows and confirming the output directory is actually removed before export.

The unresolved `Velocimetro puntual` / `id_instrumentos_rangos` issue remains independent and expected.


### SIH-02a clean real-data verification

The clean rerun completed successfully and generated the expected 5 files. The semantic checker still reports **2 PASS / 4 FAIL**, but the failure content is now exactly the expected unresolved range mapping:

- FlowTracker: `id_tipo_aforo=57`, `id_instrumentos_rangos=""`;
- Molinete: `id_tipo_aforo=57`, `id_instrumentos_rangos=""`.

This confirms MAIN-018 end to end. The remaining SIH-02 issue is solely the configured `Velocimetro puntual` concept not existing in the current `instrumentos_rangos.csv`.


### SIH-02b — configured lookup strictness regression

The remaining range-mapping problem exposes a second behavior issue independent of the missing domain row: SIH currently reports a measurement export as successful even when a semantic lookup was explicitly configured but did not resolve.

Target contract:
- if `tipo_aforo_lookup` or `instrumentos_rangos_lookup` is configured, it must resolve exactly once;
- if it does not resolve, the measurement export must fail explicitly rather than silently writing a blank configured semantic ID;
- this does not choose or invent a replacement lookup value.

A regression test has been added before production changes.


### SIH-02b — configured lookup strictness production correction

The regression produced the intended **2 failures**: neither unresolved configured lookup raised an error.

Production behavior is now corrected:
- absent lookup configuration may remain blank;
- an explicitly configured lookup key must resolve exactly once;
- unresolved configured semantics raise instead of silently writing blank IDs.

No lookup values or SIH IDs were invented. In the current real-data acceptance config, `Velocimetro puntual` is still unresolved and should therefore make the selected measurement rows report export errors until the correct SIH mapping is supplied.


### SIH-02b verification complete

Verification after the strict configured-lookup correction:
- `tests/test_sih_configured_lookup_required.py`: **2 passed**;
- full suite: **97 passed**;
- repeated full-suite run: **97 passed**.

The next real-data run is expected to fail both selected measurements explicitly on the unresolved configured `instrumentos_rangos_lookup: Velocimetro puntual`, while still writing SIH export metadata that records those failures.


### SIH-03 — real-data unresolved-lookup failure behavior

This case verifies MAIN-019 end to end with the current unresolved domain configuration.

Expected behavior for both selected `7071` measurements:
- no `actuacion` or `aforo` CSV should be emitted;
- `sih_export_metadata.csv` should contain two rows with `status=error`;
- each error should identify the unresolved configured `instrumentos_rangos_lookup` and key `Velocimetro puntual`;
- no partial measurement output files should remain.

This is an expected-failure acceptance test of error handling, not a resolution of the missing SIH range mapping.


### SIH-03 final acceptance

The real-data unresolved-lookup behavior passed exactly as designed:

- output directory clean before run: confirmed;
- files generated: **1** (`sih_export_metadata.csv`);
- checker: **5/5 PASS**;
- both selected measurements were rejected explicitly because `Velocimetro puntual` does not resolve in the current `instrumentos_rangos.csv`;
- no partial measurement CSVs were left behind.

SIH-03 is **PASS**. The remaining open item is not an error-handling defect: it is the unresolved domain/configuration mapping for `id_instrumentos_rangos` (MAIN-017).


### SIH semantic lookup scope review

The unresolved SIH mapping is not limited to FlowTracker/Molinete.

Current configuration vs lookup CSVs:
- FlowTracker/Molinete range key `Velocimetro puntual`: not present;
- Nivus range key `Doppler acustico`: not present;
- M9 range key `ADCP movil`: not present;
- Nivus tipo-aforo key `Acustico`: not present in `tipos_aforos.csv`;
- M9 tipo-aforo key `ADCP`: not present in `tipos_aforos.csv`.

M9 remains disabled, so it is not currently exercised. Nivus is enabled and requires semantic SIH mapping resolution before its SIH export can pass strict acceptance.


### SIH mapping decision — regression stage

Adopted semantic mappings:
- FlowTracker -> `VADEO / Velocimetro`;
- Molinete -> `VADEO / Velocimetro`;
- Nivus -> `VADEO / Acustico`;
- M9 -> `BOTE / ADCP`.

Lookup IDs currently adopted:
- `VADEO=57`;
- `BOTE=59`;
- `Acustico=10`;
- `Velocimetro=11`;
- `ADCP=12`.

A configuration regression test was added without modifying the user's local config files. It checks both lookup resolvability and synchronization between production and acceptance SIH mappings.


### SIH mapping consistency — expected failure confirmed

Initial regression result: **1 passed / 1 failed**. Lookup resolvability passed with the user's local production-config edits; acceptance/main mapping synchronization failed as expected.

The acceptance SIH config is now synchronized to the adopted mappings. Re-run the focused consistency test before committing the user's local `sih.yaml` and `instrumentos_rangos.csv` edits.


### SIH mapping consistency verification

Focused config consistency test: **2 passed**.
Full suite: **99 passed**.

This verifies lookup-key resolvability and synchronization between the main and acceptance SIH mappings using the user's current local production-config edits. Real-data export verification with the adopted IDs remains pending.


### SIH-04 — adopted FlowTracker/Molinete mappings

Acceptance target for the current two-measurement selection:
- FlowTracker ACCF001: `id_tipo_actuacion=4`, `id_instrumento=501`, `id_tipo_aforo=57`, `id_instrumentos_rangos=11`;
- Molinete ACCM001: `id_tipo_actuacion=4`, `id_instrumento=19`, `id_tipo_aforo=57`, `id_instrumentos_rangos=11`.

`scripts/acceptance_check_sih_expected_ids.py` verifies those exact IDs plus successful metadata status. Manual inspection remains required for the complete CSV contents and usability.


### SIH-04 uploaded output review

Reviewed generated files:
- `ID_ACCF001_actuacion_7071_20260120_141519.csv`;
- `ID_ACCF001_aforo_7071_20260120_141519.csv`;
- `ID_ACCM001_actuacion_7071_20260120_142300.csv`;
- `ID_ACCM001_aforo_7071_20260120_142300.csv`;
- `sih_export_metadata.csv`.

Observed results: both metadata rows are `success`; authoritative station ID `7071`, dates/times, and filenames agree; FlowTracker exports instrument `501`, type `57`, range `11`; Molinete exports instrument `19`, type `57`, range `11`. The CSVs are UTF-8 BOM comma-delimited files with one data row each. Hydraulic summary values are internally coherent at exported precision.

Manual-review follow-ups: Molinete `id_operador` contains display text (`I. Pérez`) while FlowTracker is blank, so the SIH operator-ID contract must be confirmed (MAIN-020). Molinete scale-related fields are blank despite `raw_canonical_found=True`; source-vs-mapping verification is required (MAIN-021). Molinete observation text `Punto P71` is retained as free text while authoritative station identity remains `7071`.


### SIH-05 — Molinete raw-field diagnostic

Pre-fix repository diagnosis: the Molinete adapter writes `escala_media_m`, but both SIH configs currently reference nonexistent raw column `escala_media` for `lectura_escala` and `escala_media`. A regression test and a real-data diagnostic script were added before production changes.

The diagnostic also reports actual values of `esc_ini_m` and `esc_fin_m` for ACCM001 so their blank SIH outputs can be classified as source-data blanks versus an export defect.


### SIH-05 diagnostic result

Focused regression result: **1 FAIL**, expected. The failure confirms that both SIH configs still reference `escala_media` instead of the Molinete adapter column `escala_media_m`.

Real-data diagnostic for ACCM001 (`7071 / 20260120 / 142300`):
- `realizado` exists and contains `I. Pérez`;
- `esc_ini_m` exists but is blank;
- `esc_fin_m` exists but is blank;
- `escala_media_m` exists but is blank;
- `escala_media` does not exist;
- observations and hydraulic radius are present.

Classification: **configuration defect confirmed, source scale values blank for this selected measurement**. A future config fix is still required, but it should not be expected to change the visible scale fields for ACCM001 because the underlying values are empty.

### Pause checkpoint

Acceptance paused here. Resume with the MAIN-021 config correction first, then rerun the focused regression, full suite, and SIH real-data export. Keep MAIN-020 open until an authoritative SIH operator-ID contract/mapping is available. Nivus SIH acceptance follows afterward.


### SIH-05 production correction

The Molinete SIH configuration defect is corrected in both `sih.yaml` and `sih_acceptance.yaml`: `lectura_escala` and `escala_media` now source from the adapter column `escala_media_m`.

Expected acceptance behavior for ACCM001 remains blank scale output because `esc_ini_m`, `esc_fin_m`, and `escala_media_m` are all blank in that selected raw-canonical row. Verification is pending.


### SIH-05 verification

After correcting the Molinete mean-scale source mapping in both SIH configs:
- focused regression: **1 passed**;
- full test suite: **100 passed**.

The code/config correction is accepted. A clean FT/ML SIH real-data smoke rerun is the next step. ACCM001 scale outputs are still expected to be blank because the selected raw-canonical row has blank `esc_ini_m`, `esc_fin_m`, and `escala_media_m` values.


### SIH-05 final acceptance

Clean FT/ML rerun after the Molinete scale mapping correction:
- generated files: **5**;
- semantic lookup checker: **6/6 PASS**;
- exact-ID checker: **4/4 PASS**.

SIH-05 is **PASS**. FlowTracker/Molinete remain accepted with `id_tipo_aforo=57` and `id_instrumentos_rangos=11`.


### SIH-06 — Nivus real-data acceptance setup

A deterministic preparation script now selects the first sorted Nivus measurement that has complete normalized hydraulic summary values, positive discharge, and a matching raw-canonical Summary row. It writes an isolated one-row selection file under `runs_acceptance/_checks/` so no corpus-specific station/date is hardcoded in repository configuration.

The Nivus checker expects the adopted SIH IDs: `id_tipo_actuacion=4`, `id_instrumento=502`, `id_tipo_aforo=57`, `id_instrumentos_rangos=10`, preserves authoritative station identity, and verifies exported hydraulic values against normalized Summary. `nivel_confiabilidad` is reported as INFO rather than asserted because the current SIH quality configuration is documented but not yet wired into output generation.


### SIH-06 automated result

Deterministic Nivus case selected: `7001 / 20241219 / 214313` (`ACCN001`).

Export generated 3 files and the checker reported **4 PASS / 0 FAIL / 1 INFO**. Passed checks:
- expected files;
- metadata success + authoritative station/date/time identity;
- semantic IDs `4 / 502 / 57 / 10`;
- hydraulic numeric fidelity against normalized Summary.

`nivel_confiabilidad` is blank and reported as INFO. Repository review confirms that current SIH code does not consume quality-metric output even though Nivus SIH config declares `CG(%)` thresholds. This is registered as MAIN-022 and does not invalidate the core Nivus SIH export acceptance.

Manual review of the generated Nivus actuación/aforo/metadata CSVs remains pending before SIH-06 is closed as automated + manual PASS.


### SIH-06 final acceptance — manual review

Uploaded Nivus actuación, aforo, and metadata CSVs were reviewed directly.

Manual checks confirm:
- authoritative station/date/time identity is consistent across filenames, rows, and metadata;
- semantic IDs are correct (`4 / 502 / 57 / 10`);
- hydraulic values match normalized data;
- raw hydraulic radius is correctly exported as `0.1725`;
- blank observations are consistent with blank raw `notes`;
- blank `id_operador`/`lectura_escala` reflect current Nivus configuration;
- blank `nivel_confiabilidad` remains the known MAIN-022 follow-up.

SIH-06 is **PASS (automated + manual) for the current core Nivus scope**.


### Pause checkpoint after SIH-06

Acceptance is paused after closing SIH-06 as **PASS (automated + manual) for core Nivus export**.

Current verified baseline:
- full test suite: **100 passed**;
- FlowTracker/Molinete SIH post-MAIN-021 smoke: **6/6 semantic PASS**, **4/4 exact-ID PASS**;
- Nivus SIH-06: **4 PASS / 0 FAIL / 1 INFO**, followed by successful manual review;
- authoritative station identity and adopted SIH mappings are preserved across the three tested instruments.

Deferred items are tracked in the main-improvements register: MAIN-020 (`id_operador` contract), MAIN-022 (CG -> `nivel_confiabilidad` integration), MAIN-023 (SIH docs/sample drift), plus previously registered product/follow-up/placeholder items. M9 remains outside real-data SIH acceptance because its ingest/export path is not yet production-complete.

Resume from MAIN-020/022/023 before declaring the SIH module fully production-complete or preparing the final merge review.


### MAIN-023 regression setup

Added `tests/test_sih_docs_template_contract.py` to pin accepted station-ID and SIH mapping documentation/template semantics before making corrections. Expected current result: failures caused by legacy `P` station examples/template rows and stale pre-acceptance SIH mapping examples.


### MAIN-023 expected failure + correction

The focused documentation/template contract suite failed **3/3** before changes, as expected. Corrections were then applied to the SIH selection template and user documentation so examples follow authoritative station IDs, adopted SIH mappings, and the corrected Molinete `escala_media_m` source. Targeted/full-suite verification remains pending.


### MAIN-023 partial verification

Post-correction run: focused suite **2 passed / 1 failed**; full suite **102 passed / 1 failed**. The only remaining defect was two stale aforo filename examples (`_P8_`, `_P11_`) in `SIH_EXPORT.md`. They are now corrected; final targeted/full-suite verification is pending.


### MAIN-023 final verification

Documentation/template contract is now fully green:
- focused suite: **3 passed**;
- full suite: **103 passed**.

MAIN-023 is closed as verified. SIH documentation and selection examples now follow authoritative station IDs, adopted SIH semantic mappings, and the corrected Molinete `escala_media_m` source.


### Deferred SIH items after MAIN-023

- **MAIN-020** is deferred pending a client decision on the SIH `id_operador` contract and authoritative operator mapping. No ID conversion will be implemented before that consultation.
- **MAIN-022** is deferred until a unified data-quality evaluation system is designed for FlowTracker, Molinete, and Nivus. SIH `nivel_confiabilidad` integration will be implemented afterward against that common quality model.


## Section profiles real-data acceptance

### SP-00 — preflight / station identity regression

The next audited module is `aforix analyze section-profiles`.

Repository preflight found that both the advanced CLI and interactive selection normalize every numeric station token to `P<n>`. That conflicts with the accepted authoritative station-ID rule, where `7001`, `7071`, and `P71` are distinct identities and no prefix may be invented.

A regression test was added first in `tests/analysis/test_section_profiles_station_identity.py`. Production code is intentionally unchanged at this stage; the focused test is expected to fail for numeric IDs such as `7001` and `7071`.

After resolving this boundary, real-data acceptance will verify:
- all three supported instruments (Nivus, FlowTracker, Molinete);
- exact station/date filtering;
- workbook README/Index/measurement sheets;
- row counts and source identity;
- X/Y values against normalized Points;
- chart creation and end-user readability;
- interactive and advanced CLI selection.


### SECTION-PROFILES-01 — station identity regression

Pre-fix focused regression: **2 failed / 0 passed**, both showing the same defect: CLI and interactive point normalization changed authoritative station `7001` into invented alias `P7001`.

Production correction applied: both selection paths now use representation-only `canonical_station_id()`. Verification pending before real-data section-profile execution.


### SECTION-PROFILES-01 — Nivus scoped real-data workbook

After MAIN-024 verification (2/2 focused PASS; full suite 105 passed), section-profiles acceptance begins with the already-verified real Nivus measurement `7001 / 20241219 / 214313`.

Scope: instrument `NV`, station `7001`, date `20241219`, default axes `distance_m` vs `depth_m`, scatter chart. Automated checker validates workbook structure, authoritative station identity, absence of legacy P aliases, measurement data row counts, and one chart per measurement sheet. Manual review of the XLSX remains required after automated PASS.


### SECTION-PROFILES-01 automated result

Nivus `7001 / 20241219` generated `section_profile_depth_m_by_distance_m_nivus_7001_20241219_20241219.xlsx`.

Checker result: **5/5 PASS**:
- README/Index/measurement-sheet structure;
- authoritative identity (`7001`, `nivus`, `2024-12-19`);
- no legacy `P` alias;
- 10 index rows = 10 worksheet data rows;
- exactly one chart on the measurement sheet.

Next real-data coverage: FlowTracker and Molinete at station `7071`, date `20260120`, followed by manual workbook review.


### SECTION-PROFILES-02 — FlowTracker

Real run: station `7071`, date `20260120`, instrument FlowTracker. Checker: **5/5 PASS**. Workbook identity is authoritative, no legacy P alias is present, measurement sheet contains 24 data rows matching the Index count, and exactly one native chart is present.

### SECTION-PROFILES-03 — Molinete

Real run: station `7071`, date `20260120`, instrument Molinete. Checker: **5/5 PASS**. Workbook identity is authoritative, no legacy P alias is present, measurement sheet contains 25 data rows matching the Index count, and exactly one native chart is present.

All three supported instruments have now passed the first automated section-profile layer. A second checker layer now verifies `distance_m`/`depth_m` fidelity against normalized Points, followed by manual review of the three XLSX outputs.


### SECTION-PROFILES strengthened checker — final automated results

The second acceptance layer verified workbook data directly against normalized Points:
- Nivus `7001 / 20241219`: **6/6 PASS**, 10 rows, X/Y source fidelity confirmed;
- FlowTracker `7071 / 20260120`: **6/6 PASS**, 24 rows, X/Y source fidelity confirmed;
- Molinete `7071 / 20260120`: **6/6 PASS**, 25 rows, X/Y source fidelity confirmed.

All three workbooks preserve authoritative station IDs, contain the expected workbook structure, have matching Index/data row counts, reproduce `distance_m` and `depth_m` from normalized Points exactly, and contain one native chart per measurement sheet.

Automated section-profiles acceptance is complete. Manual review of workbook readability, chart labeling/scales, and end-user usability remains pending.


### SECTION-PROFILES manual workbook review

The three generated workbooks were reviewed directly.

- **Nivus `7001 / 20241219`**: manual PASS for current scope. Distance/depth values are populated, identity/metadata are readable, and the profile chart corresponds to the data.
- **FlowTracker `7071 / 20260120`**: manual PASS for current scope. Distance/depth values are populated and the chart is coherent with the worksheet data.
- **Molinete `7071 / 20260120`**: manual **FAIL pending correction**. All 25 worksheet `distance_m` values are blank while `depth_m` is populated. The chart is labeled as distance-based but Excel falls back to ordinal X positions, so it is not a valid distance profile.

Diagnosis: Molinete raw adapter emits progression as `progr_m`; normalization currently omits `progr_m` from `Points.distance_m` sources. This is tracked as MAIN-025. A regression was added first; production mapping remains unchanged until the failure is observed.
