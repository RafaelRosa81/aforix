from __future__ import annotations

from itertools import product
from pathlib import Path
from typing import Iterable

import pandas as pd
from sklearn.linear_model import LinearRegression

from aforix.analysis.correlation.io.model import load_model_data
from aforix.analysis.correlation.io.stations import load_station_series
from aforix.analysis.correlation.metrics import mae, mape, nse, pbias, pearson, r2, rmse


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
    """Run model vs stations correlation.

    Default behavior follows qSL: user-provided pairs are expected.
    Optional all_pairs=True compares every station against every modeled point.

    Corrected semantics:
      X = DINAGUA station [l/s]
      Y = hydrological model [l/s]
    """

    out_dir = output_dir / "model_vs_stations" / timestep
    out_dir.mkdir(parents=True, exist_ok=True)

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

        if timestep == "monthly":
            model_df["month"] = model_df["date"].dt.to_period("M").dt.to_timestamp()
            model_df = model_df.groupby("month", as_index=False)["q_model_l/s"].mean()
            merged = pd.merge(station_df, model_df, on="month", how="inner")
            time_col = "month"
            time_fmt = "%Y%m"
        else:
            merged = pd.merge(station_df, model_df, on="date", how="inner")
            time_col = "date"
            time_fmt = "%Y%m%d"

        if merged.empty:
            continue

        x = merged["q_station_l/s"].to_numpy().reshape(-1, 1)
        y = merged["q_model_l/s"].to_numpy()

        lr = LinearRegression().fit(x, y)
        y_pred = lr.predict(x)
        merged["q_model_pred_l/s"] = y_pred
        merged["residual_l/s"] = y - y_pred

        tmin = pd.to_datetime(merged[time_col].min()).strftime(time_fmt)
        tmax = pd.to_datetime(merged[time_col].max()).strftime(time_fmt)
        csv_name = f"S{station_id}_Pm{point_id}_model_vs_stations_{timestep}_{tmin}_{tmax}.csv"
        export_cols = [time_col, "q_station_l/s", "q_model_l/s", "q_model_pred_l/s", "residual_l/s"]
        merged[export_cols].to_csv(out_dir / csv_name, index=False)

        station_values = x.flatten()
        rmse_direct = rmse(y, station_values)
        rmse_reg = rmse(y, y_pred)
        q_mean_model = float(y.mean()) if len(y) else float("nan")

        summary_rows.append({
            "Station": f"S{station_id}",
            "Model point": f"Pm{point_id}",
            "X variable": "station [l/s]",
            "Y variable": "model [l/s]",
            "Linear equation (model vs station)": f"model = {lr.coef_[0]:.6f} * station + {lr.intercept_:.6f}",
            "slope": float(lr.coef_[0]),
            "intercept": float(lr.intercept_),
            "n": int(len(merged)),
            "R2": r2(y, y_pred),
            "Pearson r": pearson(station_values, y),
            "RMSE model vs. station [l/s]": rmse_direct,
            "RMSE regression vs. model [l/s]": rmse_reg,
            "q mean model [l/s]": q_mean_model,
            "NRMSE model vs. station [-]": rmse_direct / q_mean_model if q_mean_model else float("nan"),
            "MAE regression vs. model [l/s]": mae(y, y_pred),
            "MAPE regression vs. model [%]": mape(y, y_pred),
            "PBIAS regression vs. model [%]": pbias(y, y_pred),
            "NSE regression vs. model": nse(y, y_pred),
            "start": tmin,
            "end": tmax,
        })

    pd.DataFrame(summary_rows).to_csv(out_dir / f"summary_model_vs_stations_{timestep}.csv", index=False)
    return out_dir
