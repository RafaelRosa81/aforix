from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
import yaml


EXPECTED_CHECKS = {
    "required_columns",
    "duplicates",
    "completeness",
    "ranges",
    "hydraulic_consistency",
}


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
        description="Real-data acceptance check for aforix validate run."
    )
    parser.add_argument("--config", default="configs/examples/acceptance_real.yaml")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    project_root = project_root_from_config(config_path)

    with config_path.open("r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    validation_cfg = cfg["validation"]
    output_dir = resolve_path(project_root, validation_cfg["output_dir"])

    summary_path = output_dir / "validation_summary.csv"
    required_path = output_dir / "required_columns.csv"
    duplicates_path = output_dir / "duplicates.csv"
    completeness_path = output_dir / "completeness.csv"
    ranges_path = output_dir / "ranges.csv"
    hydraulic_path = output_dir / "hydraulic_consistency_summary_points.csv"

    required_files = [
        summary_path,
        required_path,
        duplicates_path,
        completeness_path,
        ranges_path,
        hydraulic_path,
    ]
    missing_files = [str(p) for p in required_files if not p.exists()]
    if missing_files:
        raise SystemExit("Missing validation outputs: " + ", ".join(missing_files))

    summary = pd.read_csv(summary_path, dtype=str)
    required = pd.read_csv(required_path, dtype=str)
    duplicates = pd.read_csv(duplicates_path, dtype=str)
    completeness = pd.read_csv(completeness_path, dtype=str)
    ranges = pd.read_csv(ranges_path, dtype=str)
    hydraulic = pd.read_csv(hydraulic_path, dtype=str)

    findings: list[dict[str, object]] = []

    actual_checks = set(summary["check"].dropna().astype(str))
    summary_checks_ok = (
        actual_checks == EXPECTED_CHECKS
        and summary["status"].fillna("").astype(str).eq("ok").all()
    )
    findings.append({
        "check": "validation_summary",
        "status": "PASS" if summary_checks_ok else "FAIL",
        "detail": f"checks={sorted(actual_checks)} statuses={summary['status'].tolist()}",
    })

    required_ok = (
        not required.empty
        and required["status"].fillna("").astype(str).eq("ok").all()
    )
    findings.append({
        "check": "required_columns",
        "status": "PASS" if required_ok else "FAIL",
        "detail": f"rows={len(required)} non_ok={int((required['status'] != 'ok').sum())}",
    })

    duplicates_ok = duplicates.empty
    findings.append({
        "check": "duplicates",
        "status": "PASS" if duplicates_ok else "FAIL",
        "detail": f"rows={len(duplicates)}",
    })

    completeness_ok = (
        not completeness.empty
        and completeness["status"].fillna("").astype(str).eq("ok").all()
        and pd.to_numeric(completeness["n_missing"], errors="coerce").fillna(0).eq(0).all()
    )
    findings.append({
        "check": "completeness",
        "status": "PASS" if completeness_ok else "FAIL",
        "detail": f"rows={len(completeness)} non_ok={int((completeness['status'] != 'ok').sum())}",
    })

    ranges_ok = ranges.empty
    findings.append({
        "check": "ranges",
        "status": "PASS" if ranges_ok else "FAIL",
        "detail": f"rows={len(ranges)}",
    })

    hydraulic_status = hydraulic["status"].fillna("").astype(str)
    hydraulic_ok = len(hydraulic) == 250 and hydraulic_status.eq("ok").all()
    findings.append({
        "check": "hydraulic_consistency",
        "status": "PASS" if hydraulic_ok else "FAIL",
        "detail": (
            f"rows={len(hydraulic)} "
            f"ok={int(hydraulic_status.eq('ok').sum())} "
            f"non_ok={int((~hydraulic_status.eq('ok')).sum())}"
        ),
    })

    report = pd.DataFrame(findings)
    runs_root = resolve_path(project_root, cfg["paths"].get("runs_root", "runs"))
    checks_dir = runs_root / "_checks"
    checks_dir.mkdir(parents=True, exist_ok=True)
    report_path = checks_dir / "validate_acceptance.csv"
    report.to_csv(report_path, index=False, encoding="utf-8-sig")

    n_pass = int(report["status"].eq("PASS").sum())
    n_fail = int(report["status"].eq("FAIL").sum())

    print("Aforix validate real-data acceptance")
    print("====================================")
    print(f"Checks: {len(report)}")
    print(f"PASS: {n_pass}")
    print(f"FAIL: {n_fail}")
    print(f"Validation summary rows: {len(summary)}")
    print(f"Required-column rows  : {len(required)}")
    print(f"Duplicate rows        : {len(duplicates)}")
    print(f"Completeness rows     : {len(completeness)}")
    print(f"Range rows            : {len(ranges)}")
    print(f"Hydraulic rows        : {len(hydraulic)}")
    print(f"Report: {report_path}")

    if n_fail:
        print("")
        print("Failed checks:")
        print(report.loc[report["status"] == "FAIL"].to_string(index=False))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
