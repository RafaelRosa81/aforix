from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.linear_model import LinearRegression

from aforix.analysis.correlation.io.gauges import load_gauges_daily
from aforix.analysis.correlation.io.stations import load_station_series
from aforix.analysis.correlation.metrics import rmse, r2, pearson
from aforix.analysis.correlation.types import MeasuringInstrument


def _apply_window_merge(df_g: pd.DataFrame, df_s: pd.DataFrame, days_window: int) -> pd.DataFrame:
    merged_rows = []
    for _, row in df_g.iterrows():
        d = row["date"]
        mask = (df_s["date"] >= d - pd.Timedelta(days=days_window)) & (
            df_s["date"] <= d + pd.Timedelta(days=days_window)
        )
        subset = df_s.loc[mask]
        if subset.empty:
            continue
        closest = subset.iloc[(subset["date"] - d).abs().argsort()].iloc[0]
        merged_rows.append({
            "date": d,
            "q_gauge_l/s": row["q_gauge_l/s"],
            "q_station_l/s": closest["q_station_l/s"],
        })
    return pd.DataFrame(merged_rows)


def run_gauges_vs_stations(
    *,
    normalized_root: Path,
    stations_dir: Path,
    output_dir: Path,
    instruments: list[MeasuringInstrument],
    ranking_codes: list[str],
    timestep: str = "daily",
    match_mode: str = "exact",
    window_days: int = 0,
) -> Path:
    gauges = load_gauges_daily(normalized_root, instruments, ranking_codes)

    out_dir = output_dir / "gauges_vs_stations" / timestep
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = []

    for station_file in stations_dir.glob(f"*_{timestep}_station_data.csv"):
        station_id = station_file.name.split("_")[0]
        df_station = load_station_series(stations_dir, station_id, timestep)

        for point, df_gauge in gauges.items():
            df_gauge = df_gauge.copy()

            if match_mode == "exact":
                merged = pd.merge(df_gauge, df_station, on="date", how="inner")
            else:
                merged = _apply_window_merge(df_gauge, df_station, window_days)

            if merged.empty:
                continue

            x = merged["q_station_l/s"].to_numpy().reshape(-1, 1)
            y = merged["q_gauge_l/s"].to_numpy()

            lr = LinearRegression().fit(x, y)
            y_pred = lr.predict(x)

            summary.append({
                "station": station_id,
                "point": point,
                "slope": lr.coef_[0],
                "intercept": lr.intercept_,
                "R2": r2(y, y_pred),
                "RMSE": rmse(y, y_pred),
                "r": pearson(x.flatten(), y),
            })

    pd.DataFrame(summary).to_csv(out_dir / "summary_gauges_vs_stations.csv", index=False)

    return out_dir
