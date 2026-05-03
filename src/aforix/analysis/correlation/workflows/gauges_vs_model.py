from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from openpyxl import Workbook

from aforix.analysis.correlation.excel import add_pair_sheet, safe_save_workbook, write_summary_sheet, write_run_config_sheet
from aforix.analysis.correlation.io.gauges import load_gauges_daily
from aforix.analysis.correlation.io.model import load_model_data
from aforix.analysis.correlation.metrics import mae, mape, nse, pbias, pearson, r2, rmse
from aforix.analysis.correlation.plotting import save_scatter_with_regression, save_time_series
from aforix.analysis.correlation.types import MeasuringInstrument


def _coerce_date(value: str | None) -> pd.Timestamp | None:
    if not value:
        return None
    return pd.to_datetime(value, format="%Y%m%d")


def _date_window(df: pd.DataFrame, start_date: pd.Timestamp | None, end_date: pd.Timestamp | None) -> pd.DataFrame:
    out = df
    if start_date is not None:
        out = out[out["date"] >= start_date]
    if end_date is not None:
        out = out[out["date"] <= end_date]
    return out


def _linear_fit(x: np.ndarray, y: np.ndarray) -> tuple[float, float, np.ndarray]:
    if len(x) < 2 or np.nanstd(x) == 0:
        slope = 0.0
        intercept = float(np.nanmean(y)) if len(y) else float("nan")
        return slope, intercept, np.full_like(y, intercept, dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    y_pred = slope * x + intercept
    return float(slope), float(intercept), y_pred


def _require_roles(variable_roles: dict[str, str] | None, workflow_name: str) -> dict[str, str]:
    if not variable_roles:
        raise ValueError(f"variable_roles must be provided from config for {workflow_name}")
    missing = {"x", "y"} - set(variable_roles)
    if missing:
        raise ValueError(f"Missing variable_roles key(s) for {workflow_name}: {', '.join(sorted(missing))}")
    return {"x": str(variable_roles["x"]).lower(), "y": str(variable_roles["y"]).lower()}


def _role_columns(roles: dict[str, str]) -> tuple[str, str, str, str, str]:
    role_to_col = {"gauge": "q_gauge_l/s", "model": "q_model_l/s"}
    if roles["x"] not in role_to_col or roles["y"] not in role_to_col:
        raise ValueError(f"Invalid variable_roles for gauges_vs_model: {roles}")
    x_col = role_to_col[roles["x"]]
    y_col = role_to_col[roles["y"]]
    pred_col = f"q_{roles['y']}_pred_l/s"
    x_label = f"{roles['x'].capitalize()} q [l/s]"
    y_label = f"{roles['y'].capitalize()} q [l/s]"
    return x_col, y_col, pred_col, x_label, y_label


def default_ranking(cfg: dict[str, Any], instruments: Iterable[MeasuringInstrument]) -> list[str]:
    configured = cfg.get("analysis", {}).get("correlation", {}).get("default_ranking", None)
    if configured:
        return [str(x).upper() for x in configured]
    return [inst.code.upper() for inst in instruments]


def run_gauges_vs_model(
    *,
    normalized_root: Path,
    model_dir: Path,
    output_dir: Path,
    instruments: list[MeasuringInstrument],
    ranking_codes: list[str],
    start_date: str | None = None,
    end_date: str | None = None,
    points: list[str] | None = None,
    variable_roles: dict[str, str] | None = None,
) -> Path:
    roles = _require_roles(variable_roles, "gauges_vs_model")
    x_col, y_col, pred_col, x_label, y_label = _role_columns(roles)
    start = _coerce_date(start_date)
    end = _coerce_date(end_date)
    if start is not None and end is not None and end < start:
        raise ValueError("end_date cannot be earlier than start_date")

    selected_points = {str(p).replace("P", "").strip() for p in points or [] if str(p).strip()}

    ranking_label = "_".join(ranking_codes)
    points_label = "all_points" if not selected_points else "points_" + "_".join(sorted(selected_points, key=lambda p: int(p)))
    out_dir = output_dir / "gauges_vs_model" / f"instruments_{ranking_label}" / points_label
    plots_dir = out_dir / "plots"
    out_dir.mkdir(parents=True, exist_ok=True)

    wb = Workbook()
    wb.remove(wb.active)

    write_run_config_sheet(wb, {
        "analysis_type": "gauges_vs_model",
        "x_role": roles["x"],
        "y_role": roles["y"],
        "x_column": x_col,
        "y_column": y_col,
        "ranking": ranking_codes,
        "points": sorted(selected_points, key=lambda p: int(p)) if selected_points else "ALL",
        "start_date": start_date,
        "end_date": end_date,
        "normalized_root": str(normalized_root),
        "model_dir": str(model_dir),
        "output_dir": str(out_dir),
    })

    gauges = load_gauges_daily(normalized_root, instruments, ranking_codes)
    modeled = load_model_data(model_dir)
    summary_rows: list[dict[str, Any]] = []

    common_points = sorted(set(gauges) & set(modeled), key=lambda p: int(p))
    if selected_points:
        common_points = [p for p in common_points if p in selected_points]

    for point in common_points:
        df_model = modeled[point].copy()
        df_gauge = gauges[point].copy()
        df_model["date"] = pd.to_datetime(df_model["date"]).dt.normalize()
        df_gauge["date"] = pd.to_datetime(df_gauge["date"]).dt.normalize()

        merged = pd.merge(df_gauge, df_model, on="date", how="inner")
        merged = _date_window(merged, start, end)
        if merged.empty:
            continue

        merged = merged.sort_values("date").reset_index(drop=True)
        x_values = merged[x_col].to_numpy(dtype=float)
        y_values = merged[y_col].to_numpy(dtype=float)
        slope, intercept, y_pred = _linear_fit(x_values, y_values)
        merged[pred_col] = y_pred
        merged["residual_l/s"] = y_values - y_pred
        merged["date_str"] = merged["date"].dt.strftime("%Y-%m-%d")

        dmin = merged["date"].min().strftime("%Y%m%d")
        dmax = merged["date"].max().strftime("%Y%m%d")
        export_cols = ["date_str", "q_gauge_l/s", "q_model_l/s", pred_col, "residual_l/s", "source"]
        export = merged[export_cols].copy().rename(columns={"date_str": "time"})
        export.to_csv(out_dir / f"P{point}_gauge_vs_model_{dmin}_{dmax}.csv", index=False)

        n = len(merged)
        rmse_direct = rmse(y_values, x_values)
        rmse_reg = rmse(y_values, y_pred)
        q_mean_y = float(y_values.mean()) if n else float("nan")
        nrmse_direct = rmse_direct / q_mean_y if q_mean_y else float("nan")

        row = {
            "Point": f"P{point}",
            "X role": roles["x"],
            "Y role": roles["y"],
            "X variable": f"{roles['x']} [l/s]",
            "Y variable": f"{roles['y']} [l/s]",
            "X column": x_col,
            "Y column": y_col,
            "Linear equation": f"{roles['y']} = {slope:.6f} * {roles['x']} + {intercept:.6f}",
            "slope": slope,
            "intercept": intercept,
            "n": n,
            "R2": r2(y_values, y_pred),
            "Pearson r": pearson(x_values, y_values),
            "RMSE Y vs. X [l/s]": rmse_direct,
            "RMSE regression vs. Y [l/s]": rmse_reg,
            "q mean Y [l/s]": q_mean_y,
            "NRMSE Y vs. X [-]": nrmse_direct,
            "MAE regression vs. Y [l/s]": mae(y_values, y_pred),
            "MAPE regression vs. Y [%]": mape(y_values, y_pred),
            "PBIAS regression vs. Y [%]": pbias(y_values, y_pred),
            "NSE regression vs. Y": nse(y_values, y_pred),
            "start": merged["date"].min().strftime("%Y-%m-%d"),
            "end": merged["date"].max().strftime("%Y-%m-%d"),
            "sources": " ".join(sorted(set(merged["source"].astype(str)))),
        }
        summary_rows.append(row)

        add_pair_sheet(
            wb,
            f"P{point}",
            export,
            row,
            x_col=x_col,
            y_col=y_col,
            pred_col=pred_col,
            time_col="time",
            x_label=x_label,
            y_label=y_label,
        )
        save_scatter_with_regression(export, x_col=x_col, y_col=y_col, pred_col=pred_col, x_label=x_label, y_label=y_label, out_path=plots_dir / f"P{point}_scatter_gauge_vs_model.png")
        save_time_series(export, time_col="time", series=[(x_col, roles["x"].capitalize()), (y_col, roles["y"].capitalize())], out_path=plots_dir / f"P{point}_timeseries_gauge_vs_model.png")

    if summary_rows:
        a = start.strftime("%Y%m%d") if start is not None else "NA"
        b = end.strftime("%Y%m%d") if end is not None else "NA"
        pd.DataFrame(summary_rows).to_csv(out_dir / f"summary_gauges_vs_model_{ranking_label}_{a}_{b}.csv", index=False)
        write_summary_sheet(wb, "SummaryMetrics", summary_rows)
        safe_save_workbook(wb, out_dir / f"correlation_gauges_vs_model_{ranking_label}_{a}_{b}.xlsx")

    return out_dir
