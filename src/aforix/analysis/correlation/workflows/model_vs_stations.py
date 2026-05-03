from __future__ import annotations

from itertools import product
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from openpyxl import Workbook

from aforix.analysis.correlation.excel import add_pair_sheet, safe_save_workbook, write_summary_sheet, write_run_config_sheet
from aforix.analysis.correlation.io.model import load_model_data
from aforix.analysis.correlation.io.stations import load_station_series
from aforix.analysis.correlation.metrics import mae, mape, nse, pbias, pearson, r2, rmse
from aforix.analysis.correlation.plotting import save_scatter_with_regression, save_time_series


def _require_roles(variable_roles: dict[str, str] | None, workflow_name: str) -> dict[str, str]:
    if not variable_roles:
        raise ValueError(f"variable_roles must be provided from config for {workflow_name}")
    missing = {"x", "y"} - set(variable_roles)
    if missing:
        raise ValueError(f"Missing variable_roles key(s) for {workflow_name}: {', '.join(sorted(missing))}")
    return {"x": str(variable_roles["x"]).lower(), "y": str(variable_roles["y"]).lower()}


def _linear_fit(x: np.ndarray, y: np.ndarray) -> tuple[float, float, np.ndarray]:
    if len(x) < 2 or np.nanstd(x) == 0:
        slope = 0.0
        intercept = float(np.nanmean(y)) if len(y) else float("nan")
        return slope, intercept, np.full_like(y, intercept, dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    y_pred = slope * x + intercept
    return float(slope), float(intercept), y_pred


def _role_columns(roles: dict[str, str]) -> tuple[str, str, str, str, str]:
    role_to_col = {"station": "q_station_l/s", "model": "q_model_l/s"}
    if roles["x"] not in role_to_col or roles["y"] not in role_to_col:
        raise ValueError(f"Invalid variable_roles for model_vs_stations: {roles}")
    x_col = role_to_col[roles["x"]]
    y_col = role_to_col[roles["y"]]
    pred_col = f"q_{roles['y']}_pred_l/s"
    x_label = f"{roles['x'].capitalize()} q [l/s]"
    y_label = f"{roles['y'].capitalize()} q [l/s]"
    return x_col, y_col, pred_col, x_label, y_label


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
    variable_roles: dict[str, str] | None = None,
) -> Path:
    roles = _require_roles(variable_roles, "model_vs_stations")
    x_col, y_col, pred_col, x_label, y_label = _role_columns(roles)
    out_dir = output_dir / "model_vs_stations" / timestep
    plots_dir = out_dir / "plots"
    out_dir.mkdir(parents=True, exist_ok=True)

    wb = Workbook()
    wb.remove(wb.active)

    write_run_config_sheet(wb, {
        "analysis_type": "model_vs_stations",
        "x_role": roles["x"],
        "y_role": roles["y"],
        "x_column": x_col,
        "y_column": y_col,
        "pairs": list(pairs or []),
        "all_pairs": all_pairs,
        "timestep": timestep,
        "stations_dir": str(stations_dir),
        "model_dir": str(model_dir),
        "output_dir": str(out_dir),
    })

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

        x_values = merged[x_col].to_numpy(dtype=float)
        y_values = merged[y_col].to_numpy(dtype=float)
        slope, intercept, y_pred = _linear_fit(x_values, y_values)

        merged[pred_col] = y_pred
        merged["residual_l/s"] = y_values - y_pred
        merged["time"] = merged["date"].dt.strftime("%Y-%m-%d")

        export = merged[["time", "q_station_l/s", "q_model_l/s", pred_col, "residual_l/s"]]
        export.to_csv(out_dir / f"S{station_id}_Pm{point_id}_model_vs_stations_{timestep}.csv", index=False)

        rmse_direct = rmse(y_values, x_values)
        rmse_reg = rmse(y_values, y_pred)
        q_mean_y = float(y_values.mean()) if len(y_values) else float("nan")

        row = {
            "Station": f"S{station_id}",
            "Model point": f"Pm{point_id}",
            "X role": roles["x"],
            "Y role": roles["y"],
            "X variable": f"{roles['x']} [l/s]",
            "Y variable": f"{roles['y']} [l/s]",
            "X column": x_col,
            "Y column": y_col,
            "Linear equation": f"{roles['y']} = {slope:.6f} * {roles['x']} + {intercept:.6f}",
            "slope": slope,
            "intercept": intercept,
            "n": int(len(merged)),
            "R2": r2(y_values, y_pred),
            "Pearson r": pearson(x_values, y_values),
            "RMSE Y vs. X [l/s]": rmse_direct,
            "RMSE regression vs. Y [l/s]": rmse_reg,
            "q mean Y [l/s]": q_mean_y,
            "NRMSE Y vs. X [-]": rmse_direct / q_mean_y if q_mean_y else float("nan"),
            "MAE regression vs. Y [l/s]": mae(y_values, y_pred),
            "MAPE regression vs. Y [%]": mape(y_values, y_pred),
            "PBIAS regression vs. Y [%]": pbias(y_values, y_pred),
            "NSE regression vs. Y": nse(y_values, y_pred),
        }

        summary_rows.append(row)

        add_pair_sheet(
            wb,
            f"S{station_id}_Pm{point_id}",
            export,
            row,
            x_col=x_col,
            y_col=y_col,
            pred_col=pred_col,
            time_col="time",
            x_label=x_label,
            y_label=y_label,
        )

        save_scatter_with_regression(export, x_col=x_col, y_col=y_col, pred_col=pred_col, x_label=x_label, y_label=y_label, out_path=plots_dir / f"S{station_id}_Pm{point_id}_scatter.png")
        save_time_series(export, time_col="time", series=[(x_col, roles["x"].capitalize()), (y_col, roles["y"].capitalize())], out_path=plots_dir / f"S{station_id}_Pm{point_id}_timeseries.png")

    if summary_rows:
        pd.DataFrame(summary_rows).to_csv(out_dir / f"summary_model_vs_stations_{timestep}.csv", index=False)
        write_summary_sheet(wb, "SummaryMetrics", summary_rows)
        safe_save_workbook(wb, out_dir / f"correlation_model_vs_stations_{timestep}.xlsx")

    return out_dir
