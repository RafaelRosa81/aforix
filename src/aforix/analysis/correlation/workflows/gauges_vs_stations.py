from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import Workbook

from aforix.analysis.correlation.excel import add_pair_sheet, safe_save_workbook, write_summary_sheet, write_run_config_sheet
from aforix.analysis.correlation.io.gauges import load_gauges_daily
from aforix.analysis.correlation.io.stations import load_station_series
from aforix.analysis.correlation.metrics import mae, mape, nse, pbias, pearson, r2, rmse
from aforix.analysis.correlation.plotting import save_scatter_with_regression, save_time_series
from aforix.analysis.correlation.types import MeasuringInstrument


def _linear_fit(x: np.ndarray, y: np.ndarray) -> tuple[float, float, np.ndarray]:
    if len(x) < 2 or np.nanstd(x) == 0:
        slope = 0.0
        intercept = float(np.nanmean(y)) if len(y) else float("nan")
        return slope, intercept, np.full_like(y, intercept, dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    y_pred = slope * x + intercept
    return float(slope), float(intercept), y_pred


def _apply_window_merge(df_g: pd.DataFrame, df_s: pd.DataFrame, days_window: int) -> pd.DataFrame:
    merged_rows = []
    for _, row in df_g.iterrows():
        d = row["date"]
        mask = (df_s["date"] >= d - pd.Timedelta(days=days_window)) & (df_s["date"] <= d + pd.Timedelta(days=days_window))
        subset = df_s.loc[mask]
        if subset.empty:
            continue
        closest = subset.iloc[(subset["date"] - d).abs().argsort()].iloc[0]
        merged_rows.append({"date": d, "q_gauge_l/s": row["q_gauge_l/s"], "q_station_l/s": closest["q_station_l/s"], "source": row.get("source", "")})
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
    ranking_label = "_".join(ranking_codes)
    out_dir = output_dir / "gauges_vs_stations" / timestep / f"instruments_{ranking_label}" / f"match_{match_mode}_window_{window_days}"
    plots_dir = out_dir / "plots"
    out_dir.mkdir(parents=True, exist_ok=True)

    wb = Workbook()
    wb.remove(wb.active)
    write_run_config_sheet(wb, {
        "analysis_type": "gauges_vs_stations",
        "ranking": ranking_codes,
        "timestep": timestep,
        "match_mode": match_mode,
        "window_days": window_days,
        "points": "ALL",
        "stations": "ALL",
        "normalized_root": str(normalized_root),
        "stations_dir": str(stations_dir),
        "output_dir": str(out_dir),
    })
    summary_rows = []

    for station_file in stations_dir.glob(f"*_{timestep}_station_data.csv"):
        station_id = station_file.name.split("_")[0]
        df_station = load_station_series(stations_dir, station_id, timestep)
        if timestep != "daily":
            continue

        for point, df_gauge in gauges.items():
            df_gauge = df_gauge.copy()
            merged = pd.merge(df_gauge, df_station, on="date", how="inner") if match_mode == "exact" else _apply_window_merge(df_gauge, df_station, window_days)
            if merged.empty:
                continue

            merged = merged.sort_values("date").reset_index(drop=True)
            station_values = merged["q_station_l/s"].to_numpy(dtype=float)
            y = merged["q_gauge_l/s"].to_numpy(dtype=float)
            slope, intercept, y_pred = _linear_fit(station_values, y)
            merged["q_gauge_pred_l/s"] = y_pred
            merged["residual_l/s"] = y - y_pred
            merged["time"] = merged["date"].dt.strftime("%Y-%m-%d")

            dmin = merged["date"].min().strftime("%Y%m%d")
            dmax = merged["date"].max().strftime("%Y%m%d")
            export = merged[["time", "q_station_l/s", "q_gauge_l/s", "q_gauge_pred_l/s", "residual_l/s"]].copy()
            export.to_csv(out_dir / f"S{station_id}_P{point}_gauges_vs_stations_{timestep}_{match_mode}_{dmin}_{dmax}.csv", index=False)

            rmse_direct = rmse(y, station_values)
            rmse_reg = rmse(y, y_pred)
            q_mean_gauge = float(y.mean()) if len(y) else float("nan")
            row = {
                "Station": f"S{station_id}",
                "Point": f"P{point}",
                "X variable": "station [l/s]",
                "Y variable": "gauge [l/s]",
                "Linear equation (gauge vs station)": f"gauge = {slope:.6f} * station + {intercept:.6f}",
                "slope": slope,
                "intercept": intercept,
                "n": int(len(merged)),
                "R2": r2(y, y_pred),
                "Pearson r": pearson(station_values, y),
                "RMSE gauge vs. station [l/s]": rmse_direct,
                "RMSE regression vs. gauge [l/s]": rmse_reg,
                "q mean gauge [l/s]": q_mean_gauge,
                "NRMSE gauge vs. station [-]": rmse_direct / q_mean_gauge if q_mean_gauge else float("nan"),
                "MAE regression vs. gauge [l/s]": mae(y, y_pred),
                "MAPE regression vs. gauge [%]": mape(y, y_pred),
                "PBIAS regression vs. gauge [%]": pbias(y, y_pred),
                "NSE regression vs. gauge": nse(y, y_pred),
                "match_mode": match_mode,
                "window_days": window_days,
                "start": dmin,
                "end": dmax,
            }
            summary_rows.append(row)
            sheet = f"S{station_id}_P{point}"
            add_pair_sheet(wb, sheet, export, row, x_col="q_station_l/s", y_col="q_gauge_l/s", pred_col="q_gauge_pred_l/s", time_col="time", x_label="Station q [l/s]", y_label="Gauge q [l/s]")
            save_scatter_with_regression(export, x_col="q_station_l/s", y_col="q_gauge_l/s", pred_col="q_gauge_pred_l/s", x_label="Station q [l/s]", y_label="Gauge q [l/s]", out_path=plots_dir / f"S{station_id}_P{point}_scatter_gauges_vs_stations.png")
            save_time_series(export, time_col="time", series=[("q_station_l/s", "Station"), ("q_gauge_l/s", "Gauge")], out_path=plots_dir / f"S{station_id}_P{point}_timeseries_gauges_vs_stations.png")

    if summary_rows:
        pd.DataFrame(summary_rows).to_csv(out_dir / f"summary_gauges_vs_stations_{timestep}_{match_mode}_window_{window_days}.csv", index=False)
        write_summary_sheet(wb, "SummaryMetrics", summary_rows)
        safe_save_workbook(wb, out_dir / f"correlation_gauges_vs_stations_{timestep}_{ranking_label}_{match_mode}_window_{window_days}.xlsx")
    return out_dir
