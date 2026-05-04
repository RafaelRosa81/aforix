from __future__ import annotations

import numpy as np
import pandas as pd

from aforix.analysis.stage_discharge.metrics import regression_metrics


MIN_POINTS_DEFAULT = 3


def _poly_fit(x, y, degree: int):
    coeffs = np.polyfit(x, y, degree)
    p = np.poly1d(coeffs)
    return coeffs, p(x)


def _power_fit(x, y):
    mask = (x > 0) & (y > 0)
    if np.sum(mask) < 2:
        return None, None
    lx = np.log(x[mask])
    ly = np.log(y[mask])
    b, loga = np.polyfit(lx, ly, 1)
    a = np.exp(loga)
    y_pred = a * (x ** b)
    return (a, b), y_pred


def fit_group(df: pd.DataFrame, models: list[str] | None = None, min_points: int = MIN_POINTS_DEFAULT):
    if models is None:
        models = ["poly1", "poly2", "power"]

    x = df["stage_m"].to_numpy(dtype=float)
    y = df["q_total_ls"].to_numpy(dtype=float)

    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]

    if len(x) < min_points:
        return []

    results = []

    for m in models:
        try:
            if m == "poly1":
                coeffs, y_pred = _poly_fit(x, y, 1)
            elif m == "poly2":
                if len(x) < 3:
                    continue
                coeffs, y_pred = _poly_fit(x, y, 2)
            elif m == "power":
                coeffs, y_pred = _power_fit(x, y)
                if coeffs is None:
                    continue
            else:
                continue

            metrics = regression_metrics(y, y_pred)

            results.append({
                "model": m,
                "coefficients": coeffs,
                **metrics,
            })
        except Exception:
            continue

    return results


def run_fitting(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    group_cols = [
        "station_id",
        "analysis_group",
        "instrument",
        "stage_origin",
        "stage_type",
    ]

    fits_rows = []
    metrics_rows = []

    for keys, g in df.groupby(group_cols):
        fit_results = fit_group(g)
        for r in fit_results:
            row = dict(zip(group_cols, keys))
            fits_rows.append({**row, "model": r["model"], "coefficients": r["coefficients"]})
            metrics_rows.append({**row, "model": r["model"], **{k: v for k, v in r.items() if k not in ["model", "coefficients"]}})

    return pd.DataFrame(fits_rows), pd.DataFrame(metrics_rows)
