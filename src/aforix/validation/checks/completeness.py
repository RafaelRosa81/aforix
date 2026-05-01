from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from aforix.validation.common import read_table, write_report


def run(
    *,
    input_dir: Path,
    output_dir: Path,
    validation_cfg: dict[str, Any],
) -> tuple[Path, pd.DataFrame]:
    completeness_cfg = validation_cfg.get("completeness", {}) or {}
    critical_cfg = completeness_cfg.get("critical_columns", {}) or {}

    rows: list[dict[str, object]] = []

    for table_name, columns in critical_cfg.items():
        df = read_table(input_dir, table_name)

        if df is None:
            rows.append(
                {
                    "table": table_name,
                    "column": None,
                    "n_rows": None,
                    "n_missing": None,
                    "missing_pct": None,
                    "status": "missing_table",
                }
            )
            continue

        n_rows = len(df)

        for column in columns:
            if column not in df.columns:
                rows.append(
                    {
                        "table": table_name,
                        "column": column,
                        "n_rows": n_rows,
                        "n_missing": None,
                        "missing_pct": None,
                        "status": "missing_column",
                    }
                )
                continue

            missing = df[column].isna() | (df[column].astype(str).str.strip() == "")
            n_missing = int(missing.sum())
            missing_pct = (n_missing / n_rows * 100) if n_rows else 0.0

            rows.append(
                {
                    "table": table_name,
                    "column": column,
                    "n_rows": n_rows,
                    "n_missing": n_missing,
                    "missing_pct": missing_pct,
                    "status": "ok" if n_missing == 0 else "has_missing",
                }
            )

    report = pd.DataFrame(
        rows,
        columns=[
            "table",
            "column",
            "n_rows",
            "n_missing",
            "missing_pct",
            "status",
        ],
    )

    path = write_report(report, output_dir, "completeness.csv")
    return path, report