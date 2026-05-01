from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from aforix.validation.common import (
    DEFAULT_TRACEABILITY_COLUMNS,
    read_table,
    safe_numeric,
    write_report,
)


def run(
    *,
    input_dir: Path,
    output_dir: Path,
    validation_cfg: dict[str, Any],
) -> tuple[Path, pd.DataFrame]:
    ranges_cfg = validation_cfg.get("ranges", {}) or {}
    trace_cols = validation_cfg.get(
        "traceability_columns",
        DEFAULT_TRACEABILITY_COLUMNS,
    )

    reports: list[pd.DataFrame] = []

    for table_name, table_ranges in ranges_cfg.items():
        df = read_table(input_dir, table_name)

        if df is None:
            reports.append(
                pd.DataFrame(
                    [
                        {
                            "table": table_name,
                            "column": None,
                            "value": None,
                            "rule": None,
                            "status": "missing_table",
                        }
                    ]
                )
            )
            continue

        base_cols = [col for col in trace_cols if col in df.columns]

        for column, rules in table_ranges.items():
            if column not in df.columns:
                reports.append(
                    pd.DataFrame(
                        [
                            {
                                "table": table_name,
                                "column": column,
                                "value": None,
                                "rule": None,
                                "status": "missing_column",
                            }
                        ]
                    )
                )
                continue

            values = safe_numeric(df[column])
            mask = pd.Series(False, index=df.index)
            rule_labels: list[str] = []

            if "min" in rules:
                mask = mask | (values < float(rules["min"]))
                rule_labels.append(f"min={rules['min']}")

            if "max" in rules:
                mask = mask | (values > float(rules["max"]))
                rule_labels.append(f"max={rules['max']}")

            bad = df.loc[mask, base_cols].copy()
            if bad.empty:
                continue

            bad.insert(0, "table", table_name)
            bad["column"] = column
            bad["value"] = values.loc[mask].values
            bad["rule"] = ";".join(rule_labels)
            bad["status"] = "out_of_range"
            reports.append(bad)

    if reports:
        report = pd.concat(reports, ignore_index=True)
    else:
        report = pd.DataFrame(
            columns=[
                "table",
                *trace_cols,
                "column",
                "value",
                "rule",
                "status",
            ]
        )

    path = write_report(report, output_dir, "ranges.csv")
    return path, report