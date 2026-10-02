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
PARAMETERS = ["q_total_m3s", "q_total_ls"]


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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Acceptance check for exact-station/date filtered Summary CSV export."
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

    csv_files = sorted(run_dir.glob("summary_20260120-20260120_flat_allinst.csv"))
    if len(csv_files) != 1:
        raise SystemExit(
            f"Expected exactly one filtered Summary CSV in {run_dir}; found {len(csv_files)}"
        )

    output_path = csv_files[0]
    metadata_path = output_path.with_name(output_path.stem + "_metadata.txt")
    if not metadata_path.exists():
        raise SystemExit(f"Missing metadata sidecar: {metadata_path}")

    exported = pd.read_csv(output_path, dtype=str)
    source = pd.read_csv(
        normalized_root / "Summary.csv",
        dtype={
            "station_id": "string",
            "measurement_date": "string",
            "measurement_time": "string",
        },
    )

    expected = source[
        (source["station_id"].astype(str) == "7071")
        & (source["measurement_date"].astype(str) == "20260120")
    ].copy()

    expected_cols = [*IDENTITY, *PARAMETERS]
    exported = exported[expected_cols].copy()
    expected = expected[expected_cols].copy()

    for col in IDENTITY:
        exported[col] = clean_text(exported[col])
        expected[col] = clean_text(expected[col])

    sort_keys = ["instrument", "station_id", "measurement_date", "measurement_time"]
    exported = exported.sort_values(sort_keys, kind="stable").reset_index(drop=True)
    expected = expected.sort_values(sort_keys, kind="stable").reset_index(drop=True)

    checks: list[dict[str, object]] = []

    checks.append({
        "check": "expected_rows",
        "status": "PASS" if len(expected) == 2 and len(exported) == 2 else "FAIL",
        "detail": f"source_filtered={len(expected)} exported={len(exported)}",
    })

    expected_instruments = set(expected["instrument"])
    checks.append({
        "check": "multi_instrument_same_day",
        "status": "PASS"
        if expected_instruments == {"flowtracker", "molinete"}
        and set(exported["instrument"]) == expected_instruments
        else "FAIL",
        "detail": f"source={sorted(expected_instruments)} export={sorted(set(exported['instrument']))}",
    })

    identity_ok = exported[IDENTITY].equals(expected[IDENTITY])
    checks.append({
        "check": "identity_fidelity",
        "status": "PASS" if identity_ok else "FAIL",
        "detail": (
            f"export={exported[IDENTITY].to_dict('records')} "
            f"source={expected[IDENTITY].to_dict('records')}"
        ),
    })

    numeric_ok = True
    numeric_detail: list[str] = []
    for col in PARAMETERS:
        exp_num = pd.to_numeric(exported[col], errors="coerce")
        src_num = pd.to_numeric(expected[col], errors="coerce")
        bad = (exp_num.isna() ^ src_num.isna()) | (
            exp_num.notna()
            & src_num.notna()
            & ((exp_num - src_num).abs() > 1e-12)
        )
        if bad.any():
            numeric_ok = False
            idx = int(bad[bad].index[0])
            numeric_detail.append(
                f"{col}: export={exported.loc[idx, col]!r} source={expected.loc[idx, col]!r}"
            )
    checks.append({
        "check": "numeric_fidelity",
        "status": "PASS" if numeric_ok else "FAIL",
        "detail": "; ".join(numeric_detail),
    })

    metadata = metadata_path.read_text(encoding="utf-8")
    metadata_ok = all(
        token in metadata
        for token in [
            "table: Summary",
            "instrument: all",
            "points: 7071",
            "early_date_requested: 20260120",
            "late_date_requested: 20260120",
            "grouping: none",
            "row_count: 2",
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
    report_path = checks_dir / "export_tables_filtered_csv_acceptance.csv"
    report.to_csv(report_path, index=False, encoding="utf-8-sig")

    n_pass = int(report["status"].eq("PASS").sum())
    n_fail = int(report["status"].eq("FAIL").sum())

    print("Aforix export-tables filtered CSV acceptance")
    print("============================================")
    print(f"Export directory: {run_dir}")
    print(f"CSV: {output_path}")
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
