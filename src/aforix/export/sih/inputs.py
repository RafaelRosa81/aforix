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


def _load_summary_csv(root: Path, instrument: str, *, required: bool) -> pd.DataFrame | None:
    candidates = [
        root / instrument / "Summary.csv",
        root / instrument / "Summary" / "Summary.csv",
        root / "Summary.csv",
    ]

    for path in candidates:
        if path.exists():
            df = pd.read_csv(path, dtype=str).fillna("")
            if "instrument" in df.columns:
                return df[df["instrument"].astype(str).str.lower() == instrument.lower()].copy()
            return df

    if required:
        raise FileNotFoundError(
            f"Summary.csv not found for instrument '{instrument}'. Tried: {candidates}"
        )
    return None


def load_normalized_summary(normalized_root: str | Path, instrument: str) -> pd.DataFrame:
    df = _load_summary_csv(Path(normalized_root), instrument, required=True)
    assert df is not None
    return df


def load_raw_canonical_summary(raw_canonical_root: str | Path, instrument: str) -> pd.DataFrame | None:
    return _load_summary_csv(Path(raw_canonical_root), instrument, required=False)


def _normalized_date_series(s: pd.Series) -> pd.Series:
    return s.astype(str).str.replace("-", "", regex=False).str.strip()


def _normalized_time_series(s: pd.Series) -> pd.Series:
    return (
        s.astype(str)
        .str.replace(":", "", regex=False)
        .str.replace(".", "", regex=False)
        .str.strip()
        .str[:6]
    )


def resolve_measurement(summary_df: pd.DataFrame, selection_row: pd.Series) -> pd.Series:
    station_id = str(selection_row["station_id"])
    measurement_date = str(selection_row["measurement_date"])
    measurement_time = str(selection_row["measurement_time"])

    matches = summary_df[
        (summary_df["station_id"].astype(str) == station_id)
        & (_normalized_date_series(summary_df["measurement_date"]) == measurement_date)
        & (_normalized_time_series(summary_df["measurement_time"]) == measurement_time)
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


def resolve_optional_measurement(summary_df: pd.DataFrame | None, selection_row: pd.Series) -> pd.Series | None:
    if summary_df is None or summary_df.empty:
        return None
    try:
        return resolve_measurement(summary_df, selection_row)
    except MeasurementNotFoundError:
        return None
