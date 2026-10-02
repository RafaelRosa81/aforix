from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import yaml


PARAMETERS = ["q_total_ls", "area_total_m2"]
EARLY = "20260119"
LATE = "20260122"
INSTRUMENT = "flowtracker"


def project_root_from_config(config_path: Path) -> Path:
    resolved = config_path.resolve()
    for candidate in [resolved.parent, *resolved.parents]:
        if (candidate / ".git").exists() or (candidate / "pyproject.toml").exists():
            return candidate
    return Path.cwd().resolve()


def resolve_path(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Acceptance check for daily-pivot FlowTracker Summary XLSX export."
    )
    parser.add_argument("--config", default="configs/examples/acceptance_real.yaml")
    parser.add_argument("--export-dir", default=None)
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    root = project_root_from_config(config_path)

    with config_path.open("r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    export_cfg = ((cfg.get("export", {}) or {}).get("tables", {}) or {})
    normalized_root = resolve_path(root, export_cfg["input_dir"])
    export_root = resolve_path(root, export_cfg["output_dir"])

    if args.export_dir:
        run_dir = Path(args.export_dir).resolve()
    else:
        candidates = sorted(p for p in export_root.iterdir() if p.is_dir())
        if not candidates:
            raise SystemExit(f"No export directories found in {export_root}")
        run_dir = candidates[-1]

    matches = sorted(run_dir.glob("summary_20260119-20260122_daily_avg_ft.xlsx"))
    if len(matches) != 1:
        raise SystemExit(
            f"Expected exactly one daily FlowTracker pivot XLSX in {run_dir}; "
            f"found {len(matches)}"
        )

    xlsx_path = matches[0]
    metadata_path = xlsx_path.with_name(xlsx_path.stem + "_metadata.txt")
    if not metadata_path.exists():
        raise SystemExit(f"Missing metadata sidecar: {metadata_path}")

    exported = pd.read_excel(xlsx_path, sheet_name="export", dtype=str)
    source = pd.read_csv(
        normalized_root / "Summary.csv",
        dtype={
            "station_id": "string",
            "measurement_date": "string",
            "measurement_time": "string",
        },
    )

    work = source[
        (source["instrument"].astype(str).str.lower() == INSTRUMENT)
        & (source["measurement_date"].astype(str) >= EARLY)
        & (source["measurement_date"].astype(str) <= LATE)
    ].copy()

    for col in PARAMETERS:
        work[col] = pd.to_numeric(work[col], errors="coerce")

    periods = pd.date_range(EARLY, LATE, freq="D").strftime("%Y%m%d").tolist()

    grouped = (
        work.groupby(["instrument", "station_id", "measurement_date"], dropna=False)[PARAMETERS]
        .mean()
        .reset_index()
    )

    expected = grouped.pivot(
        index=["instrument", "station_id"],
        columns="measurement_date",
        values=PARAMETERS,
    )
    expected = expected.swaplevel(0, 1, axis=1)

    desired_columns = pd.MultiIndex.from_product(
        [periods, PARAMETERS],
        names=["measurement_date", None],
    )
    expected = expected.reindex(columns=desired_columns).reset_index()

    flat_cols = []
    for col in expected.columns:
        if isinstance(col, tuple):
            parts = [str(x) for x in col if x not in (None, "", "nan")]
            flat_cols.append(" | ".join(parts) if parts else "")
        else:
            flat_cols.append(str(col))
    expected.columns = flat_cols

    checks: list[dict[str, object]] = []

    expected_columns = ["instrument", "station_id"] + [
        f"{period} | {parameter}"
        for period in periods
        for parameter in PARAMETERS
    ]
    columns_ok = list(exported.columns) == expected_columns
    checks.append({
        "check": "column_order_and_period_coverage",
        "status": "PASS" if columns_ok else "FAIL",
        "detail": (
            f"expected={expected_columns}; "
            f"exported={list(exported.columns)}"
        ),
    })

    row_count_ok = len(exported) == len(expected) and len(expected) > 0
    checks.append({
        "check": "row_count",
        "status": "PASS" if row_count_ok else "FAIL",
        "detail": f"expected={len(expected)} exported={len(exported)}",
    })

    station_rows_ok = set(
        zip(
            exported["instrument"].fillna("").astype(str),
            exported["station_id"].fillna("").astype(str),
        )
    ) == set(
        zip(
            expected["instrument"].fillna("").astype(str),
            expected["station_id"].fillna("").astype(str),
        )
    )
    checks.append({
        "check": "station_rows",
        "status": "PASS" if station_rows_ok else "FAIL",
        "detail": (
            f"expected_rows={sorted(set(zip(expected['instrument'].astype(str), expected['station_id'].astype(str))))}; "
            f"export_rows={sorted(set(zip(exported['instrument'].astype(str), exported['station_id'].astype(str))))}"
        ),
    })

    fidelity_ok = False
    fidelity_detail = ""
    if columns_ok and len(exported) == len(expected):
        sort_keys = ["instrument", "station_id"]
        exp = exported.sort_values(sort_keys, kind="stable").reset_index(drop=True)
        src = expected.sort_values(sort_keys, kind="stable").reset_index(drop=True)

        ids_ok = (
            exp["instrument"].fillna("").astype(str).equals(
                src["instrument"].fillna("").astype(str)
            )
            and exp["station_id"].fillna("").astype(str).equals(
                src["station_id"].fillna("").astype(str)
            )
        )

        numeric_ok = True
        failures: list[str] = []
        for col in expected_columns[2:]:
            a = pd.to_numeric(exp[col], errors="coerce")
            b = pd.to_numeric(src[col], errors="coerce")
            mismatch = (a.isna() ^ b.isna()) | (
                a.notna() & b.notna() & ((a - b).abs() > 1e-12)
            )
            if mismatch.any():
                numeric_ok = False
                idx = int(mismatch[mismatch].index[0])
                failures.append(
                    f"{col}: export={exp.loc[idx, col]!r} source={src.loc[idx, col]!r}"
                )

        fidelity_ok = ids_ok and numeric_ok
        if not fidelity_ok:
            fidelity_detail = f"ids_ok={ids_ok}; failures={failures}"
    else:
        fidelity_detail = "comparison skipped because columns/row counts differ"

    checks.append({
        "check": "daily_mean_fidelity",
        "status": "PASS" if fidelity_ok else "FAIL",
        "detail": fidelity_detail,
    })

    missing_period_columns_ok = all(
        f"{period} | {param}" in exported.columns
        for period in periods
        for param in PARAMETERS
    )
    checks.append({
        "check": "explicit_missing_period_columns",
        "status": "PASS" if missing_period_columns_ok else "FAIL",
        "detail": f"periods={periods}",
    })

    metadata = metadata_path.read_text(encoding="utf-8")
    metadata_ok = all(
        token in metadata
        for token in [
            "table: Summary",
            "instrument: flowtracker",
            "early_date_requested: 20260119",
            "late_date_requested: 20260122",
            "grouping: daily",
            "pivot: True",
            "aggregation: mean",
            "column_order: period_major",
        ]
    )
    checks.append({
        "check": "metadata",
        "status": "PASS" if metadata_ok else "FAIL",
        "detail": str(metadata_path),
    })

    report = pd.DataFrame(checks)
    runs_root = resolve_path(root, (cfg.get("paths", {}) or {}).get("runs_root", "runs"))
    checks_dir = runs_root / "_checks"
    checks_dir.mkdir(parents=True, exist_ok=True)
    report_path = checks_dir / "export_tables_daily_pivot_xlsx_acceptance.csv"
    report.to_csv(report_path, index=False, encoding="utf-8-sig")

    n_pass = int(report["status"].eq("PASS").sum())
    n_fail = int(report["status"].eq("FAIL").sum())

    print("Aforix export-tables daily pivot XLSX acceptance")
    print("================================================")
    print(f"Export directory: {run_dir}")
    print(f"Workbook: {xlsx_path}")
    print(f"Rows: {len(exported)}")
    print(f"Checks: {len(report)}")
    print(f"PASS: {n_pass}")
    print(f"FAIL: {n_fail}")
    print(f"Report: {report_path}")

    if n_fail:
        print("")
        print("Failed checks:")
        print(report.loc[report["status"] == "FAIL"].to_string(index=False))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
