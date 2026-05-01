from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from aforix.validation.common import DEFAULT_KEYS, read_table, write_report


def run(
    *,
    input_dir: Path,
    output_dir: Path,
    validation_cfg: dict[str, Any],
) -> tuple[Path, pd.DataFrame]:
    keys = validation_cfg.get("keys", DEFAULT_KEYS)
    rows: list[pd.DataFrame] = []

    for table_name in ("Summary", "Points"):
        df = read_table(input_dir, table_name)

        if df is None:
            continue

        available_keys = [col for col in keys if col in df.columns]

        if len(available_keys) != len(keys):
            missing = sorted(set(keys) - set(available_keys))
            rows.append(
                pd.DataFrame(
                    [
                        {
                            "table": table_name,
                            "status": "missing_key_columns",
                            "missing_key_columns": ",".join(missing),
                            "duplicate_count": None,
                        }
                    ]
                )
            )
            continue

        duplicated = df[df.duplicated(subset=available_keys, keep=False)].copy()

        if duplicated.empty:
            continue

        counts = (
            duplicated.groupby(available_keys, dropna=False)
            .size()
            .reset_index(name="duplicate_count")
        )

        counts.insert(0, "table", table_name)
        counts.insert(1, "status", "duplicate")
        rows.append(counts)

    if rows:
        report = pd.concat(rows, ignore_index=True)
    else:
        report = pd.DataFrame(
            columns=["table", "status", *keys, "duplicate_count"]
        )

    path = write_report(report, output_dir, "duplicates.csv")
    return path, report