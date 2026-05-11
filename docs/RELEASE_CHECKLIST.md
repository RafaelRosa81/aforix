# Aforix production release checklist

This checklist defines the minimum go/no-go checks before using Aforix in production.

Scope for this release:

- FlowTracker, Molinete and Nivus are in scope.
- M9 is out of scope for this production release and will be addressed in a later stabilization cycle.
- Checks that require local, non-versioned hydrological data are manual checks and should not be treated as mandatory CI jobs.

## 1. Clean installation

Objective: verify that Aforix can be installed from a clean environment.

Go criteria:

- Editable installation completes without dependency errors.
- Runtime and development dependencies install from `pyproject.toml`.

Windows CMD:

```bat
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Expected result:

- Installation finishes successfully.
- No `ModuleNotFoundError` or dependency resolution errors.

No-go if:

- Installation fails.
- `.[dev]` is not recognized.
- Required runtime dependencies are missing.

## 2. Critical runtime imports

Objective: verify that core analysis and batch dependencies are available after installation.

Windows CMD:

```bat
python -c "import sklearn, scipy, matplotlib, psutil; print('OK')"
```

Expected result:

```text
OK
```

No-go if:

- Any import fails.

## 3. CLI smoke test

Objective: verify that the CLI and main subcommands load successfully.

Windows CMD:

```bat
aforix --help
aforix ingest --help
aforix export --help
aforix analyze --help
aforix normalize --help
aforix validate --help
aforix batch --help
aforix external --help
```

Expected result:

- Typer help is displayed for each command.
- No import errors.
- No unexpected traceback.

No-go if:

- The root CLI does not start.
- Any production subcommand fails to load.

## 4. Configuration check

Objective: verify that the example project configuration is structurally valid.

Windows CMD:

```bat
aforix config-check -c configs/examples/main.yaml
```

Expected result:

- Configuration loads successfully.
- No validation errors.

No-go if:

- The YAML cannot be read.
- Required sections are missing.
- Config validation fails.

## 5. Test suite

Objective: verify the current regression baseline.

Windows CMD:

```bat
pytest -q
```

Expected result:

- All tests pass.

No-go if:

- Tests fail.
- Tests cannot be collected.
- `aforix` cannot be imported from tests.

## 6. Compile check

Objective: verify that Python files in source and scripts compile.

Windows CMD:

```bat
python -m compileall src scripts
```

Expected result:

- No syntax errors.

No-go if:

- Any source or script file fails to compile.

## 7. Batch smoke test

Objective: verify that batch orchestration can validate, plan and dry-run a minimal batch.

Windows CMD:

```bat
aforix batch check -b configs/batches/examples/check_only.yaml
aforix batch plan -b configs/batches/examples/check_only.yaml
aforix batch run -b configs/batches/examples/check_only.yaml --dry-run
```

Expected result:

- Batch validation succeeds.
- Execution plan is printed.
- Dry-run completes without executing domain processing.

No-go if:

- Batch YAML cannot be loaded.
- A registered command is missing.
- Dry-run fails.

## 8. Local production pipeline smoke test

Objective: verify the real local data pipeline. This check depends on local, non-versioned data and is not suitable for CI.

Windows CMD:

```bat
aforix config-check -c configs/examples/main.yaml
aforix ingest flowtracker -c configs/examples/main.yaml
aforix ingest molinete -c configs/examples/main.yaml
aforix ingest nivus -c configs/examples/main.yaml
aforix build-groups -c configs/examples/main.yaml
aforix normalize run -c configs/examples/main.yaml
python scripts\audit_pipeline_outputs.py
aforix validate run -c configs/examples/main.yaml
```

Expected result:

- Each stage completes successfully.
- Normalized outputs are generated in `database/normalized`.
- Audit and validation reports do not show blocking inconsistencies.

No-go if:

- Any production instrument in scope fails unexpectedly.
- Normalized outputs are missing or inconsistent.
- Validation reports blocking errors that affect results.

## 9. SIH export smoke test

Objective: verify that SIH export commands and configuration load correctly.

Windows CMD:

```bat
aforix export sih --help
aforix config-check -c configs/examples/main.yaml
```

Manual check with local normalized data:

```bat
aforix export sih -c configs/examples/main.yaml --sih-config configs/sih/sih.yaml
```

Expected result:

- SIH help loads.
- SIH config can be used when normalized data exists.
- Exported files follow the expected SIH structure.

No-go if:

- SIH command fails to load.
- Required SIH config files or templates are missing.
- Exported files are structurally invalid.

## 10. Git ignore and versioned assets

Objective: verify that generated data are ignored without hiding versioned configs or templates.

Windows CMD:

```bat
git check-ignore -v configs\sih\selection_template.csv
git check-ignore -v configs\examples\main.yaml
git check-ignore -v outputs\demo.csv
git check-ignore -v runs\demo.csv
git check-ignore -v database\demo.csv
```

Expected result:

- Files under `configs/` should not be ignored.
- Generated output paths such as `outputs/`, `runs/` and `database/` should be ignored.

No-go if:

- Required templates or example configs are hidden by `.gitignore`.
- Generated data directories are not ignored.

## 11. Documentation release check

Objective: verify that documentation matches the current production scope.

Manual review:

```bat
type README.md
type docs\02_pipeline.md
type docs\03_cli.md
type docs\BATCH_GUIDE.md
type docs\CONFIGURATION_GUIDE.md
```

Expected result:

- Installation instructions are current.
- CLI commands match implemented commands.
- Batch usage is documented.
- M9 is not presented as production-ready in this release.

No-go if:

- Documentation instructs users to run commands that no longer exist.
- Documentation presents experimental functionality as production-ready.
- Required release checks are not documented.

## Final go/no-go summary

Go if:

- Clean installation succeeds.
- Critical imports pass.
- CLI smoke tests pass.
- `config-check` passes.
- Tests pass.
- Compile check passes.
- Batch smoke test passes.
- Local production pipeline succeeds with real data.
- SIH export is verified when SIH delivery is in scope.
- Versioned configs/templates are not hidden by `.gitignore`.

No-go if:

- A clean install cannot run `aforix --help`.
- Any required runtime dependency is missing.
- Tests cannot be collected or executed.
- Batch orchestration cannot validate/plan/dry-run.
- Normalization or validation produces blocking data-quality errors.
- Documentation contradicts the actual supported production scope.
