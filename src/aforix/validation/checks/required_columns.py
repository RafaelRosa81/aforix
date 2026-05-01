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
    required_cfg = validation_cfg.get("required_columns", {}) or {}

    rows: list[dict[str, object]] = []

    for table_name, required_columns in required_cfg.items():
        df = read_table(input_dir, table_name)

        if df is None:
            rows.append(
                {
                    "table": table_name,
                    "column": None,
                    "status": "missing_table",
                    "message": f"Missing table: {input_dir / (table_name + '.csv')}",
                }
            )
            continue

        existing = set(df.columns)

        for column in required_columns:
            status = "ok" if column in existing else "missing_column"
            rows.append(
                {
                    "table": table_name,
                    "column": column,
                    "status": status,
                    "message": "" if status == "ok" else f"Missing column: {column}",
                }
            )

    report = pd.DataFrame(
        rows,
        columns=["table", "column", "status", "message"],
    )

    path = write_report(report, output_dir, "required_columns.csv")
    return path, report