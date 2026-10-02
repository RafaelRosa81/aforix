from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import yaml


EXPECTED_PARAMETERS = [
    "q_total_m3s",
    "q_total_ls",
    "area_total_m2",
    "width_total_m",
    "depth_mean_m",
    "velocity_mean_m_s",
    "temperature_c",
]

IDENTITY = [
    "instrument",
    "station_id",
    "station_name",
    "measurement_date",
    "measurement_time",
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


def canonical_text(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Acceptance check for the first user-facing Summary XLSX export."
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

    xlsx_files = sorted(run_dir.glob("summary_*_flat_allinst.xlsx"))
    if len(xlsx_files) != 1:
        raise SystemExit(
            f"Expected exactly one Summary flat all-instruments XLSX in {run_dir}; "
            f"found {len(xlsx_files)}"
        )
    xlsx_path = xlsx_files[0]
    metadata_path = xlsx_path.with_name(xlsx_path.stem + "_metadata.txt")
    if not metadata_path.exists():
        raise SystemExit(f"Missing metadata sidecar: {metadata_path}")

    exported = pd.read_excel(xlsx_path, sheet_name="export", dtype=str)
    source = pd.read_csv(normalized_root / "Summary.csv", dtype=str)

    expected_cols = [*IDENTITY, *EXPECTED_PARAMETERS]
    missing_export = [c for c in expected_cols if c not in exported.columns]
    missing_source = [c for c in expected_cols if c not in source.columns]

    checks: list[dict[str, object]] = []
    checks.append({
        "check": "columns",
        "status": "PASS" if not missing_export and not missing_source else "FAIL",
        "detail": f"missing_export={missing_export}; missing_source={missing_source}",
    })

    checks.append({
        "check": "row_count",
        "status": "PASS" if len(exported) == 250 and len(source) == 250 else "FAIL",
        "detail": f"exported={len(exported)} source={len(source)}",
    })

    comparison_ok = False
    comparison_detail = ""
    if not missing_export and not missing_source and len(exported) == len(source):
        exp = exported[expected_cols].copy()
        src = source[expected_cols].copy()
        for col in expected_cols:
            exp[col] = canonical_text(exp[col])
            src[col] = canonical_text(src[col])
        sort_keys = ["instrument", "station_id", "measurement_date", "measurement_time"]
        exp = exp.sort_values(sort_keys, kind="stable").reset_index(drop=True)
        src = src.sort_values(sort_keys, kind="stable").reset_index(drop=True)
        comparison_ok = exp.equals(src)
        if not comparison_ok:
            bad = (exp != src).any(axis=1)
            idx = int(bad[bad].index[0])
            comparison_detail = (
                f"first mismatch row={idx}; "
                f"export={exp.iloc[idx].to_dict()}; source={src.iloc[idx].to_dict()}"
            )
    else:
        comparison_detail = "comparison skipped because required columns/row counts differ"

    checks.append({
        "check": "source_fidelity",
        "status": "PASS" if comparison_ok else "FAIL",
        "detail": comparison_detail,
    })

    id_values = set(canonical_text(exported["station_id"])) if "station_id" in exported.columns else set()
    key_ids_ok = {"701190", "701150", "70101"}.issubset(id_values)
    checks.append({
        "check": "long_station_ids",
        "status": "PASS" if key_ids_ok else "FAIL",
        "detail": "required=701190,701150,70101",
    })

    metadata_text = metadata_path.read_text(encoding="utf-8")
    meta_ok = (
        "table: Summary" in metadata_text
        and "instrument: all" in metadata_text
        and "grouping: none" in metadata_text
        and "row_count: 250" in metadata_text
        and all(p in metadata_text for p in EXPECTED_PARAMETERS)
    )
    checks.append({
        "check": "metadata",
        "status": "PASS" if meta_ok else "FAIL",
        "detail": str(metadata_path),
    })

    # Workbook usability basics.
    xls = pd.ExcelFile(xlsx_path)
    workbook_ok = {"export", "metadata"}.issubset(set(xls.sheet_names))
    checks.append({
        "check": "workbook_structure",
        "status": "PASS" if workbook_ok else "FAIL",
        "detail": f"sheets={xls.sheet_names}",
    })

    report = pd.DataFrame(checks)
    runs_root = resolve_path(root, (cfg.get("paths", {}) or {}).get("runs_root", "runs"))
    checks_dir = runs_root / "_checks"
    checks_dir.mkdir(parents=True, exist_ok=True)
    report_path = checks_dir / "export_tables_summary_xlsx_acceptance.csv"
    report.to_csv(report_path, index=False, encoding="utf-8-sig")

    n_pass = int(report["status"].eq("PASS").sum())
    n_fail = int(report["status"].eq("FAIL").sum())

    print("Aforix export-tables Summary XLSX acceptance")
    print("============================================")
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
