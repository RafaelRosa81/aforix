from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import pandas as pd
from sklearn.linear_model import LinearRegression

from aforix.analysis.correlation.io.gauges import load_gauges_daily
from aforix.analysis.correlation.io.model import load_model_data
from aforix.analysis.correlation.metrics import mae, mape, nse, pbias, pearson, r2, rmse
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


def default_ranking(cfg: dict[str, Any], instruments: Iterable[MeasuringInstrument]) -> list[str]:
    configured = (
        cfg.get("analysis", {})
        .get("correlation", {})
        .get("default_ranking", None)
    )
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
) -> Path:
    """Run gauges vs model correlation.

    Semantics are explicit and corrected from qSL:
      X = gauge measurement [l/s]
      Y = hydrological model [l/s]
    """

    start = _coerce_date(start_date)
    end = _coerce_date(end_date)
    if start is not None and end is not None and end < start:
        raise ValueError("end_date cannot be earlier than start_date")

    ranking_label = "_".join(ranking_codes)
    out_dir = output_dir / "gauges_vs_model" / f"instruments_{ranking_label}"
    out_dir.mkdir(parents=True, exist_ok=True)

    gauges = load_gauges_daily(normalized_root, instruments, ranking_codes)
    modeled = load_model_data(model_dir)

    summary_rows: list[dict[str, Any]] = []

    common_points = sorted(set(gauges) & set(modeled), key=lambda p: int(p))
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
        x = merged["q_gauge_l/s"].to_numpy().reshape(-1, 1)
        y = merged["q_model_l/s"].to_numpy()

        lr = LinearRegression().fit(x, y)
        y_pred = lr.predict(x)
        merged["q_model_pred_l/s"] = y_pred
        merged["residual_l/s"] = y - y_pred
        merged["date_str"] = merged["date"].dt.strftime("%Y-%m-%d")

        dmin = merged["date"].min().strftime("%Y%m%d")
        dmax = merged["date"].max().strftime("%Y%m%d")
        csv_name = f"P{point}_gauge_vs_model_{dmin}_{dmax}.csv"
        merged[
            ["date_str", "q_gauge_l/s", "q_model_l/s", "q_model_pred_l/s", "residual_l/s", "source"]
        ].to_csv(out_dir / csv_name, index=False)

        y_flat = x.flatten()
        n = len(merged)
        rmse_direct = rmse(y, y_flat)
        rmse_reg = rmse(y, y_pred)
        q_mean_model = float(y.mean()) if n else float("nan")
        nrmse_direct = rmse_direct / q_mean_model if q_mean_model else float("nan")

        summary_rows.append(
            {
                "Point": f"P{point}",
                "X variable": "gauge [l/s]",
                "Y variable": "model [l/s]",
                "Linear equation (model vs gauge)": f"model = {lr.coef_[0]:.6f} * gauge + {lr.intercept_:.6f}",
                "slope": float(lr.coef_[0]),
                "intercept": float(lr.intercept_),
                "n": n,
                "R2": r2(y, y_pred),
                "Pearson r": pearson(y_flat, y),
                "RMSE model vs. gauge [l/s]": rmse_direct,
                "RMSE regression vs. model [l/s]": rmse_reg,
                "q mean model [l/s]": q_mean_model,
                "NRMSE model vs. gauge [-]": nrmse_direct,
                "MAE regression vs. model [l/s]": mae(y, y_pred),
                "MAPE regression vs. model [%]": mape(y, y_pred),
                "PBIAS regression vs. model [%]": pbias(y, y_pred),
                "NSE regression vs. model": nse(y, y_pred),
                "start": merged["date"].min().strftime("%Y-%m-%d"),
                "end": merged["date"].max().strftime("%Y-%m-%d"),
                "sources": " ".join(sorted(set(merged["source"].astype(str)))),
            }
        )

    summary = pd.DataFrame(summary_rows)
    if not summary.empty:
        a = start.strftime("%Y%m%d") if start is not None else "NA"
        b = end.strftime("%Y%m%d") if end is not None else "NA"
        summary.to_csv(out_dir / f"summary_gauges_vs_model_{ranking_label}_{a}_{b}.csv", index=False)

    return out_dir
