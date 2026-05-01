from __future__ import annotations

from pathlib import Path

import pandas as pd

from aforix.config.loader import load_config
from aforix.validation.common import (
    get_validation_config,
    is_check_enabled,
    resolve_project_path,
    summarize_report,
)
from aforix.validation.checks import (
    completeness,
    duplicates,
    hydraulic_consistency,
    ranges,
    required_columns,
)


CHECKS = {
    "required_columns": required_columns.run,
    "duplicates": duplicates.run,
    "completeness": completeness.run,
    "ranges": ranges.run,
    "hydraulic_consistency": hydraulic_consistency.run,
}


def run_validation(config_path: str | Path) -> Path:
    config_path = Path(config_path).resolve()
    cfg = load_config(config_path)

    validation_cfg = get_validation_config(cfg)

    if not validation_cfg.get("enabled", True):
        raise RuntimeError("Validation is disabled in config: validation.enabled=false")

    input_dir = resolve_project_path(
        validation_cfg.get("input_dir", "database/normalized"),
        config_path=config_path,
    )
    output_dir = resolve_project_path(
        validation_cfg.get("output_dir", "database/validation"),
        config_path=config_path,
    )

    if not input_dir.exists():
        raise FileNotFoundError(f"Validation input directory does not exist: {input_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    summaries: list[dict[str, object]] = []

    for check_name, check_func in CHECKS.items():
        if not is_check_enabled(validation_cfg, check_name):
            continue

        report_path, report = check_func(
            input_dir=input_dir,
            output_dir=output_dir,
            validation_cfg=validation_cfg,
        )

        n_rows = len(report)
        status = _infer_status(report)
        message = _infer_message(check_name, report, status)

        summaries.append(
            summarize_report(
                check_name=check_name,
                report_path=report_path,
                n_rows=n_rows,
                status=status,
                message=message,
            )
        )

    summary_df = pd.DataFrame(
        summaries,
        columns=["check", "status", "n_rows", "report_path", "message"],
    )
    summary_df.to_csv(output_dir / "validation_summary.csv", index=False)

    return output_dir


def _infer_status(report: pd.DataFrame) -> str:
    if report.empty:
        return "ok"

    if "status" not in report.columns:
        return "ok"

    statuses = set(report["status"].dropna().astype(str))

    bad_statuses = {
        "missing_table",
        "missing_column",
        "missing_columns",
        "missing_key_columns",
        "duplicate",
        "has_missing",
        "out_of_range",
        "missing_pair",
        "inconsistent",
    }

    return "issues_found" if statuses & bad_statuses else "ok"


def _infer_message(check_name: str, report: pd.DataFrame, status: str) -> str:
    if status == "ok":
        return "No issues found."

    return f"{check_name} generated report rows requiring review."