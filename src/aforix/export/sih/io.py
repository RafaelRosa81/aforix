from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd


DEFAULT_CSV_ENCODINGS = (
    "utf-8-sig",
    "utf-8",
    "cp1252",
    "latin1",
)


class CsvReadError(ValueError):
    pass


def read_csv_robust(
    path: str | Path,
    *,
    dtype=str,
    fillna_value: str | None = "",
    encodings: Iterable[str] = DEFAULT_CSV_ENCODINGS,
    **kwargs,
) -> pd.DataFrame:
    """Read a CSV file trying common encodings used by Excel/Windows.

    This is intentionally used by the SIH export module because configuration CSVs
    may be edited by users in Excel or LibreOffice and saved as UTF-8, UTF-8-BOM,
    Windows-1252, or Latin-1.
    """

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"CSV file not found: {p}")

    errors: list[str] = []

    for encoding in encodings:
        try:
            df = pd.read_csv(p, dtype=dtype, encoding=encoding, **kwargs)
            if fillna_value is not None:
                df = df.fillna(fillna_value)
            return df
        except UnicodeDecodeError as exc:
            errors.append(f"{encoding}: {exc}")

    raise CsvReadError(
        "Could not read CSV with supported encodings. "
        f"File: {p}. Tried: {', '.join(encodings)}. Errors: {errors}"
    )
