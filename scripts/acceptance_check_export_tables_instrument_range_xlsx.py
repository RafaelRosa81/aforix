from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import yaml


IDENTITY = [
    "instrument",
    "station_id",
    "station_name",
    "measurement_date",
    "measurement_time",
]
PARAMETERS = [
    "q_total_m3s",
    "q_total_ls",
    "area_total_m2",
    "velocity_mean_m_s",
]


def project_root_from_config(config_path: Path) -> Path:
    resolved = config_path.resolve()
    for candidate in [resolved.parent, *resolved.parents]:
        if (candidate / ".git").exists() or (candidate / "pyproject.toml").exists():
            return candidate
    return Path.cwd().resolve()


def resolve_path(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def clean_text(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def numeric_equal(a: pd.Series, b: pd.Series) -> pd.Series:
    an = pd.to_numeric(a, errors="coerce")
    bn = pd.to_numeric(b, errors="coerce")
    missing_mismatch = an.isna() ^ bn.isna()
    both = an.notna() & bn.notna()
    value_mismatch = pd.Series(False, index=a.index)
    value_mismatch.loc[both] = (an.loc[both] - bn.loc[both]).abs() > 1e-12
    return ~(missing_mismatch | value_mismatch)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Acceptance check for instrument/date-range Summary XLSX export."
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

    xlsx_files = sorted(run_dir.glob("summary_20260119-20260122_flat_ft.xlsx"))
    if len(xlsx_files) != 1:
        raise SystemExit(
            f"Expected exactly one FlowTracker range XLSX in {run_dir}; "
            f"found {len(xlsx_files)}"
        )

    xlsx_path = xlsx_files[0]
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

    expected = source[
        (source["instrument"].astype(str).str.lower() == "flowtracker")
        & (source["measurement_date"].astype(str) >= "20260119")
        & (source["measurement_date"].astype(str) <= "20260122")
    ].copy()

    expected_cols = [*IDENTITY, *PARAMETERS]
    missing_export = [c for c in expected_cols if c not in exported.columns]
    missing_source = [c for c in expected_cols if c not in expected.columns]

    checks: list[dict[str, object]] = []

    checks.append({
        "check": "columns",
        "status": "PASS" if not missing_export and not missing_source else "FAIL",
        "detail": f"missing_export={missing_export}; missing_source={missing_source}",
    })

    row_count_ok = len(expected) > 0 and len(exported) == len(expected)
    checks.append({
        "check": "row_count",
        "status": "PASS" if row_count_ok else "FAIL",
        "detail": f"source_filtered={len(expected)} exported={len(exported)}",
    })

    filter_ok = (
        not exported.empty
        and exported["instrument"].fillna("").astype(str).str.lower().eq("flowtracker").all()
        and exported["measurement_date"].fillna("").astype(str).between("20260119", "20260122").all()
    )
    checks.append({
        "check": "instrument_and_date_filter",
        "status": "PASS" if filter_ok else "FAIL",
        "detail": (
            f"instruments={sorted(set(exported['instrument'].dropna().astype(str)))}; "
            f"dates={sorted(set(exported['measurement_date'].dropna().astype(str)))}"
        ),
    })

    comparison_ok = False
    comparison_detail = ""
    if not missing_export and not missing_source and len(exported) == len(expected):
        exp = exported[expected_cols].copy()
        src = expected[expected_cols].copy()

        for col in IDENTITY:
            exp[col] = clean_text(exp[col])
            src[col] = clean_text(src[col])

        sort_keys = ["instrument", "station_id", "measurement_date", "measurement_time"]
        exp = exp.sort_values(sort_keys, kind="stable").reset_index(drop=True)
        src = src.sort_values(sort_keys, kind="stable").reset_index(drop=True)

        identity_ok = exp[IDENTITY].equals(src[IDENTITY])

        numeric_ok = True
        numeric_detail = []
        for col in PARAMETERS:
            equal = numeric_equal(exp[col], src[col])
            if not equal.all():
                numeric_ok = False
                idx = int(equal[~equal].index[0])
                numeric_detail.append(
                    f"{col}: export={exp.loc[idx, col]!r} source={src.loc[idx, col]!r}"
                )

        comparison_ok = identity_ok and numeric_ok
        if not comparison_ok:
            comparison_detail = (
                f"identity_ok={identity_ok}; numeric_detail={numeric_detail}"
            )
    else:
        comparison_detail = "comparison skipped because required columns/row counts differ"

    checks.append({
        "check": "source_fidelity",
        "status": "PASS" if comparison_ok else "FAIL",
        "detail": comparison_detail,
    })

    no_legacy_station_code = "station_code" not in exported.columns
    no_p_station_ids = not exported["station_id"].fillna("").astype(str).str.startswith("P").any()
    checks.append({
        "check": "station_identity_schema",
        "status": "PASS" if no_legacy_station_code and no_p_station_ids else "FAIL",
        "detail": (
            f"station_code_present={not no_legacy_station_code}; "
            f"p_prefixed_ids={int(exported['station_id'].fillna('').astype(str).str.startswith('P').sum())}"
        ),
    })

    metadata = metadata_path.read_text(encoding="utf-8")
    metadata_ok = all(
        token in metadata
        for token in [
            "table: Summary",
            "instrument: flowtracker",
            "early_date_requested: 20260119",
            "late_date_requested: 20260122",
            "grouping: none",
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
    report_path = checks_dir / "export_tables_instrument_range_xlsx_acceptance.csv"
    report.to_csv(report_path, index=False, encoding="utf-8-sig")

    n_pass = int(report["status"].eq("PASS").sum())
    n_fail = int(report["status"].eq("FAIL").sum())

    print("Aforix export-tables instrument/date-range XLSX acceptance")
    print("========================================================")
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
