from __future__ import annotations

from pathlib import Path

import pandas as pd


def write_csv(
    row: dict,
    columns: list[str],
    output_path: str | Path,
    *,
    delimiter: str = ",",
    encoding: str = "utf-8-sig",
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame([[row.get(c, "") for c in columns]], columns=columns)

    df.to_csv(output, index=False, sep=delimiter, encoding=encoding)

    return output
