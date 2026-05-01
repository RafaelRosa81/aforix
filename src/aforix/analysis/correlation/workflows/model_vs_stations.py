from __future__ import annotations

from itertools import product
from pathlib import Path
from typing import Iterable

import pandas as pd
from openpyxl import Workbook
from sklearn.linear_model import LinearRegression

from aforix.analysis.correlation.excel import add_pair_sheet, safe_save_workbook, write_summary_sheet
from aforix.analysis.correlation.io.model import load_model_data
from aforix.analysis.correlation.io.stations import load_station_series
from aforix.analysis.correlation.metrics import mae, mape, nse, pbias, pearson, r2, rmse
from aforix.analysis.correlation.plotting import save_scatter_with_regression, save_time_series


def _available_station_ids(stations_dir: Path, timestep: str) -> list[str]:
    return sorted({p.name.split("_")[0] for p in stations_dir.glob(f"*_{timestep}_station_data.csv")})


def _pairs_from_all(stations_dir: Path, model_dir: Path, timestep: str) -> list[tuple[str, str]]:
    station_ids = _available_station_ids(stations_dir, timestep)
    model_ids = sorted(load_model_data(model_dir).keys(), key=lambda x: int(x))
    return list(product(station_ids, model_ids))


def run_model_vs_stations(
    *,
    stations_dir: Path,
    model_dir: Path,
    output_dir: Path,
    pairs: Iterable[tuple[str, str]] | None,
    timestep: str = "daily",
    all_pairs: bool = False,
) -> Path:
    out_dir = output_dir / "model_vs_stations" / timestep
    plots_dir = out_dir / "plots"
    out_dir.mkdir(parents=True, exist_ok=True)

    wb = Workbook()
    wb.remove(wb.active)

    model_data = load_model_data(model_dir)
    selected_pairs = list(pairs or [])
    if all_pairs:
        selected_pairs = _pairs_from_all(stations_dir, model_dir, timestep)
    if not selected_pairs:
        raise ValueError("model_vs_stations requires explicit pairs unless all_pairs=True")

    summary_rows = []

    for station_id, point_id in selected_pairs:
        point_id = str(point_id).replace("Pm", "").replace("P", "")
        if point_id not in model_data:
            continue

        try:
            station_df = load_station_series(stations_dir, str(station_id), timestep)
        except Exception:
            continue

        model_df = model_data[point_id].copy()
        model_df["date"] = pd.to_datetime(model_df["date"]).dt.normalize()

        merged = pd.merge(station_df, model_df, on="date", how="inner")
        if merged.empty:
            continue

        x = merged["q_station_l/s"].to_numpy().reshape(-1, 1)
        y = merged["q_model_l/s"].to_numpy()

        lr = LinearRegression().fit(x, y)
        y_pred = lr.predict(x)
        merged["q_model_pred_l/s"] = y_pred
        merged["residual_l/s"] = y - y_pred
        merged["time"] = merged["date"].dt.strftime("%Y-%m-%d")

        export = merged[["time", "q_station_l/s", "q_model_l/s", "q_model_pred_l/s", "residual_l/s"]]
        export.to_csv(out_dir / f"S{station_id}_Pm{point_id}_model_vs_stations_{timestep}.csv", index=False)

        station_values = x.flatten()
        rmse_direct = rmse(y, station_values)
        rmse_reg = rmse(y, y_pred)
        q_mean_model = float(y.mean()) if len(y) else float("nan")

        row = {
            "Station": f"S{station_id}",
            "Model point": f"Pm{point_id}",
            "X variable": "station [l/s]",
            "Y variable": "model [l/s]",
            "Linear equation": f"model = {lr.coef_[0]:.6f} * station + {lr.intercept_:.6f}",
            "slope": float(lr.coef_[0]),
            "intercept": float(lr.intercept_),
            "n": int(len(merged)),
            "R2": r2(y, y_pred),
            "Pearson r": pearson(station_values, y),
            "RMSE": rmse_direct,
            "NRMSE": rmse_direct / q_mean_model if q_mean_model else float("nan"),
            "MAE": mae(y, y_pred),
            "MAPE": mape(y, y_pred),
            "PBIAS": pbias(y, y_pred),
            "NSE": nse(y, y_pred),
        }

        summary_rows.append(row)

        add_pair_sheet(
            wb,
            f"S{station_id}_Pm{point_id}",
            export,
            row,
            x_col="q_station_l/s",
            y_col="q_model_l/s",
            pred_col="q_model_pred_l/s",
            time_col="time",
            x_label="Station q [l/s]",
            y_label="Model q [l/s]",
        )

        save_scatter_with_regression(export, x_col="q_station_l/s", y_col="q_model_l/s", pred_col="q_model_pred_l/s", x_label="Station q [l/s]", y_label="Model q [l/s]", out_path=plots_dir / f"S{station_id}_Pm{point_id}_scatter.png")
        save_time_series(export, time_col="time", series=[("q_station_l/s", "Station"), ("q_model_l/s", "Model")], out_path=plots_dir / f"S{station_id}_Pm{point_id}_timeseries.png")

    if summary_rows:
        pd.DataFrame(summary_rows).to_csv(out_dir / f"summary_model_vs_stations_{timestep}.csv", index=False)
        write_summary_sheet(wb, "SummaryMetrics", summary_rows)
        safe_save_workbook(wb, out_dir / f"correlation_model_vs_stations_{timestep}.xlsx")

    return out_dir
