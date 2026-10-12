"""Select normalized verticals for a single SIH discharge measurement.

This module deliberately does not calculate IVE. The calculation engine is
developed separately and can consume the selected rows once available.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from aforix.export.sih.io import read_csv_robust
from aforix.export.sih.inputs import (
    _normalized_date_series,
    _normalized_time_series,
)


REQUIRED_POINT_COLUMNS = {
    "station_id",
    "measurement_date",
    "measurement_time",
    "distance_m",
    "depth_m",
    "velocity_mean_m_s",
    "width_m",
}


def load_ive_points(
    normalized_root: str | Path,
    instrument: str,
    measurement: pd.Series,
) -> pd.DataFrame:
    """Return the ordered points for exactly one normalized measurement.

    Raise on missing/ambiguous data rather than mixing two measurements.
    """
    root = Path(normalized_root)
    candidates = [
        root / instrument / "Points.csv",
        root / instrument / "Points" / "Points.csv",
        root / "Points.csv",
    ]
    path = next((candidate for candidate in candidates if candidate.is_file()), None)
    if path is None:
        raise FileNotFoundError(f"Points.csv not found for {instrument}; tried: {candidates}")

    df = read_csv_robust(path, dtype=str, fillna_value="")
    missing = REQUIRED_POINT_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Points.csv missing IVE columns: {sorted(missing)}")

    if "instrument" in df.columns:
        df = df[df["instrument"].astype(str).str.strip().str.casefold() == instrument.strip().casefold()]

    date = str(measurement["measurement_date"]).replace("-", "").strip()
    time = str(measurement["measurement_time"]).replace(":", "").replace(".", "").strip()[:6]
    df = df[
        (df["station_id"].astype(str).str.strip() == str(measurement["station_id"]).strip())
        & (_normalized_date_series(df["measurement_date"]) == date)
        & (_normalized_time_series(df["measurement_time"]) == time)
    ].copy()
    if df.empty:
        raise ValueError(
            f"No IVE points for instrument={instrument}, "
            f"station={measurement['station_id']}, date={date}, time={time}"
        )

    # Reject partial numeric data; silently dropping verticals changes the IVE.
    for column in ("distance_m", "depth_m", "velocity_mean_m_s", "width_m"):
        df[column] = pd.to_numeric(df[column], errors="raise")
        if df[column].isna().any():
            raise ValueError(f"Missing numeric value in Points.csv column: {column}")

    widths = df["width_m"].unique()
    if len(widths) != 1 or widths[0] <= 0:
        raise ValueError("IVE requires one positive total width_m for the measurement")

    df = df.sort_values("distance_m", kind="stable").reset_index(drop=True)
    if df["distance_m"].duplicated().any():
        raise ValueError("Duplicate vertical distance_m in selected measurement")
    if (df["distance_m"] < 0).any() or (df["distance_m"] > widths[0]).any():
        raise ValueError("Vertical distance_m outside measurement width_m")
    if (df["depth_m"] < 0).any():
        raise ValueError("Negative depth_m in selected measurement")
    return df
