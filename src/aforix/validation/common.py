from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_TRACEABILITY_COLUMNS = [
    "station_id",
    "station_name",
    "measurement_date",
    "measurement_time",
    "instrument",
    "source_file",
    "source_run_dir",
    "run_id",
]

DEFAULT_KEYS = [
    "instrument",
    "station_id",
    "measurement_date",
    "measurement_time",
]


def project_root_from_config(config_path: Path) -> Path:
    resolved = config_path.resolve()
    if len(resolved.parents) >= 3:
        return resolved.parents[2]
    return Path.cwd()


def resolve_project_path(path_value: str | Path, *, config_path: Path) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return (project_root_from_config(config_path) / path).resolve()


def get_validation_config(cfg: dict[str, Any]) -> dict[str, Any]:
    return cfg.get("validation", {}) or {}


def is_check_enabled(validation_cfg: dict[str, Any], check_name: str) -> bool:
    checks = validation_cfg.get("checks", {}) or {}
    return bool(checks.get(check_name, True))


def safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def read_table(input_dir: Path, table_name: str) -> pd.DataFrame | None:
    path = input_dir / f"{table_name}.csv"
    if not path.exists():
        return None
    return pd.read_csv(path, dtype=str)


def write_report(df: pd.DataFrame, output_dir: Path, filename: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / filename
    df.to_csv(out_path, index=False)
    return out_path


def empty_report(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def summarize_report(
    *,
    check_name: str,
    report_path: Path,
    n_rows: int,
    status: str,
    message: str,
) -> dict[str, object]:
    return {
        "check": check_name,
        "status": status,
        "n_rows": n_rows,
        "report_path": str(report_path),
        "message": message,
    }