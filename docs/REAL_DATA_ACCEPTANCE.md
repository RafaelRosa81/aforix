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
