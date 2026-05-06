from __future__ import annotations

from pathlib import Path

import pandas as pd


REQUIRED_SELECTION_COLUMNS = {
    "station_id",
    "measurement_date",
    "measurement_time",
    "instrument",
    "export_id",
}


class SelectionFileError(ValueError):
    pass


class MeasurementNotFoundError(ValueError):
    pass


class DuplicateMeasurementError(ValueError):
    pass


def load_selection_file(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Selection file not found: {p}")

    df = pd.read_csv(p, dtype=str).fillna("")

    missing = REQUIRED_SELECTION_COLUMNS - set(df.columns)
    if missing:
        raise SelectionFileError(
            f"Selection file missing required columns: {sorted(missing)}"
        )

    return df


def load_normalized_summary(normalized_root: str | Path, instrument: str) -> pd.DataFrame:
    root = Path(normalized_root)

    summary_path = root / instrument / "Summary.csv"
    if not summary_path.exists():
        alt = root / instrument / "Summary" / "Summary.csv"
        if alt.exists():
            summary_path = alt

    if not summary_path.exists():
        raise FileNotFoundError(
            f"Normalized Summary.csv not found for instrument '{instrument}': {summary_path}"
        )

    return pd.read_csv(summary_path, dtype=str)


def resolve_measurement(summary_df: pd.DataFrame, selection_row: pd.Series) -> pd.Series:
    station_id = str(selection_row["station_id"])
    measurement_date = str(selection_row["measurement_date"])
    measurement_time = str(selection_row["measurement_time"])

    matches = summary_df[
        (summary_df["station_id"].astype(str) == station_id)
        & (summary_df["measurement_date"].astype(str).str.replace("-", "") == measurement_date)
        & (
            summary_df["measurement_time"]
            .astype(str)
            .str.replace(":", "")
            .str.replace(".", "", regex=False)
            .str[:6]
            == measurement_time
        )
    ]

    if matches.empty:
        raise MeasurementNotFoundError(
            f"No measurement found for station={station_id}, date={measurement_date}, time={measurement_time}"
        )

    if len(matches) > 1:
        raise DuplicateMeasurementError(
            f"Multiple measurements found for station={station_id}, date={measurement_date}, time={measurement_time}"
        )

    return matches.iloc[0]
