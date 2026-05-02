from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_station_series(stations_dir: Path, station_id: str, timestep: str) -> pd.DataFrame:
    """Load a DINAGUA station series in l/s for hourly, daily, or monthly."""

    path = stations_dir / f"{station_id}_{timestep}_station_data.csv"
    if not path.exists() and timestep == "monthly":
        path = stations_dir / f"{station_id}_daily_station_data.csv"
    if not path.exists() and timestep == "daily":
        path = stations_dir / f"{station_id}_hourly_station_data.csv"
    if not path.exists():
        raise FileNotFoundError(f"Station file not found for station={station_id}, timestep={timestep}")

    df = pd.read_csv(path)
    if "date" not in df.columns or "q(m3/s)" not in df.columns:
        raise ValueError(f"Station file {path.name} must include date and q(m3/s)")

    out = df.copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out["q_station_l/s"] = pd.to_numeric(out["q(m3/s)"], errors="coerce") * 1000.0
    out = out.dropna(subset=["date", "q_station_l/s"])

    if timestep == "hourly":
        if "time" not in out.columns:
            raise ValueError(f"Hourly station file {path.name} must include time")
        out["time"] = out["time"].fillna("00:00:00").astype(str)
        out["date"] = out["date"].dt.normalize()
        return out[["date", "time", "q_station_l/s"]]

    if timestep == "monthly":
        out["month"] = out["date"].dt.to_period("M").dt.to_timestamp()
        return out.groupby("month", as_index=False)["q_station_l/s"].mean()

    out["date"] = out["date"].dt.normalize()
    return out.groupby("date", as_index=False)["q_station_l/s"].mean()
