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
    p = Path(value)
    return p.resolve() if p.is_absolute() else (root / p).resolve()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Acceptance check for interactive flat XLSX table export."
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
        dirs = sorted(p for p in export_root.iterdir() if p.is_dir())
        if not dirs:
            raise SystemExit(f"No export directories found in {export_root}")
        run_dir = dirs[-1]

    matches = sorted(run_dir.glob("summary_20260120-20260120_flat_allinst.xlsx"))
    if len(matches) != 1:
        raise SystemExit(
            f"Expected exactly one interactive flat XLSX in {run_dir}; found {len(matches)}"
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

    expected = source[
        (source["station_id"].astype(str) == "7071")
        & (source["measurement_date"].astype(str) == "20260120")
    ].copy()

    expected_cols = [*IDENTITY, *PARAMETERS]
    checks: list[dict[str, object]] = []

    columns_ok = list(exported.columns) == expected_cols
    checks.append({
        "check": "columns",
        "status": "PASS" if columns_ok else "FAIL",
        "detail": f"expected={expected_cols}; exported={list(exported.columns)}",
    })

    row_count_ok = len(exported) == len(expected) == 2
    checks.append({
        "check": "row_count",
        "status": "PASS" if row_count_ok else "FAIL",
        "detail": f"expected={len(expected)} exported={len(exported)}",
    })

    identity_ok = False
    numeric_ok = False
    if columns_ok and len(exported) == len(expected):
        sort_keys = ["instrument", "station_id", "measurement_date", "measurement_time"]
        exp = exported.copy()
        src = expected[expected_cols].copy()

        for col in IDENTITY:
            exp[col] = exp[col].fillna("").astype(str).str.strip()
            src[col] = src[col].fillna("").astype(str).str.strip()

        exp = exp.sort_values(sort_keys, kind="stable").reset_index(drop=True)
        src = src.sort_values(sort_keys, kind="stable").reset_index(drop=True)

        identity_ok = exp[IDENTITY].equals(src[IDENTITY])

        numeric_ok = True
        for col in PARAMETERS:
            a = pd.to_numeric(exp[col], errors="coerce")
            b = pd.to_numeric(src[col], errors="coerce")
            mismatch = (a.isna() ^ b.isna()) | (
                a.notna() & b.notna() & ((a - b).abs() > 1e-12)
            )
            if mismatch.any():
                numeric_ok = False

    checks.append({
        "check": "identity_fidelity",
        "status": "PASS" if identity_ok else "FAIL",
        "detail": "Expected exact station/date/time/instrument identity fidelity.",
    })
    checks.append({
        "check": "numeric_fidelity",
        "status": "PASS" if numeric_ok else "FAIL",
        "detail": "Expected exact q_total_m3s/q_total_ls fidelity.",
    })

    instruments = set(exported["instrument"].dropna().astype(str)) if "instrument" in exported else set()
    times = set(exported["measurement_time"].dropna().astype(str)) if "measurement_time" in exported else set()
    same_day_pair_ok = instruments == {"flowtracker", "molinete"} and times == {"141519", "142300"}
    checks.append({
        "check": "same_day_distinct_measurements",
        "status": "PASS" if same_day_pair_ok else "FAIL",
        "detail": f"instruments={sorted(instruments)}; times={sorted(times)}",
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
            "pivot: False",
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
    report_path = checks_dir / "export_tables_interactive_xlsx_acceptance.csv"
    report.to_csv(report_path, index=False, encoding="utf-8-sig")

    n_pass = int(report["status"].eq("PASS").sum())
    n_fail = int(report["status"].eq("FAIL").sum())

    print("Aforix export-tables interactive XLSX acceptance")
    print("===============================================")
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
