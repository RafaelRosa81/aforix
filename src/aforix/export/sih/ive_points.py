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
    instrument_root = root / instrument
    points_dir = instrument_root / "Points"
    points_files = sorted(points_dir.glob("*.csv")) if points_dir.is_dir() else []
    candidates = [
        instrument_root / "Points.csv",
        points_dir / "Points.csv",
        root / "Points.csv",
    ]

    if points_files:
        frames = [read_csv_robust(path, dtype=str, fillna_value="") for path in points_files]
        df = pd.concat(frames, ignore_index=True, sort=False)
    else:
        path = next((candidate for candidate in candidates if candidate.is_file()), None)
        if path is None:
            raise FileNotFoundError(
                f"Points data not found for {instrument}; tried files {candidates} "
                f"and directory {points_dir}"
            )
        df = read_csv_robust(path, dtype=str, fillna_value="")

    missing = REQUIRED_POINT_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Points data missing IVE columns: {sorted(missing)}")

    if df.empty:
        raise FileNotFoundError(f"Points.csv not found for {instrument}; tried: {candidates}")

    if "instrument" in df.columns:
        df = df[df["instrument"].astype(str).str.strip().str.casefold() == instrument.strip().casefold()]

    date = str(measurement["measurement_date"]).replace("-", "").strip()
    time = str(measurement["measurement_time"]).replace(":", "").replace(".", "").strip()[:6]
    df = df[
        (df["station_id"].astype(str).str.strip() == str(measurement["station_id"]).strip())
        & (_normalized_date_series(df["measurement_date"]) == date)
        & (_normalized_time_series(df["measurement_time"]) == time)
    ].copy()

    requested_source = measurement.get("source_file")
    if requested_source is not None and not pd.isna(requested_source) and str(requested_source).strip():
        if "source_file" in df.columns:
            source_values = df["source_file"].astype(str).str.strip()
            requested = str(requested_source).strip()
            exact = source_values == requested
            if exact.any():
                df = df[exact].copy()
            else:
                # Normalized summaries can carry an absolute path while Points
                # metadata contains only the original MAT basename.
                requested_name = Path(requested.replace("\\", "/")).name.casefold()
                same_name = source_values.map(
                    lambda value: Path(value.replace("\\", "/")).name.casefold()
                    == requested_name
                )
                if same_name.any():
                    df = df[same_name].copy()

    if df.empty:
        raise ValueError(
            f"No IVE points for instrument={instrument}, "
            f"station={measurement['station_id']}, date={date}, time={time}"
        )

    # File based normalization may leave equivalent rows from separate source
    # exports (for example, older and newer filenames for the same MAT). Keep
    # one copy of each M9 sample, but reject copies that disagree physically.
    if (
        instrument.strip().casefold() == "m9"
        and {"source_file", "sample_number"}.issubset(df.columns)
    ):
        identity = ["source_file", "sample_number"]
        value_columns = ["distance_m", "depth_m", "velocity_mean_m_s", "width_m"]
        duplicated = df.duplicated(identity, keep=False)
        if duplicated.any():
            conflicts = (
                df.loc[duplicated]
                .groupby(identity, dropna=False)[value_columns]
                .nunique(dropna=False)
                .gt(1)
                .any(axis=1)
            )
            if conflicts.any():
                raise ValueError(
                    "Conflicting duplicate M9 Points rows for source_file/sample_number"
                )
            df = df.drop_duplicates(identity, keep="first").copy()

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
