from __future__ import annotations

import json

import numpy as np
import pandas as pd

from aforix.analysis.stage_discharge.metrics import regression_metrics


MIN_POINTS_DEFAULT = 3
GROUP_COLS = [
    "station_id",
    "analysis_group",
    "instrument",
    "stage_origin",
    "stage_type",
]


def predict_model(model: str, coefficients, x_values):
    x = np.asarray(x_values, dtype=float)
    coefs = _parse_coefficients(coefficients)
    if coefs is None:
        return np.full_like(x, np.nan, dtype=float)

    if model == "poly1":
        a, b = coefs
        return a * x + b
    if model == "poly2":
        a, b, c = coefs
        return a * x**2 + b * x + c
    if model == "power":
        a, b = coefs
        y = np.full_like(x, np.nan, dtype=float)
        mask = x > 0
        y[mask] = a * (x[mask] ** b)
        return y
    return np.full_like(x, np.nan, dtype=float)


def coefficient_dict(model: str, coefficients) -> dict[str, float]:
    coefs = _parse_coefficients(coefficients)
    if coefs is None:
        return {}
    if model == "poly1":
        return {"a": coefs[0], "b": coefs[1]}
    if model == "poly2":
        return {"a": coefs[0], "b": coefs[1], "c": coefs[2]}
    if model == "power":
        return {"a": coefs[0], "b": coefs[1]}
    return {}


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

    for model in models:
        try:
            if model == "poly1":
                coeffs, y_pred = _poly_fit(x, y, 1)
            elif model == "poly2":
                if len(x) < 3:
                    continue
                coeffs, y_pred = _poly_fit(x, y, 2)
            elif model == "power":
                coeffs, y_pred = _power_fit(x, y)
                if coeffs is None:
                    continue
            else:
                continue

            metrics = regression_metrics(y, y_pred)
            coeff_dict = coefficient_dict(model, coeffs)

            results.append(
                {
                    "model": model,
                    "coefficients": json.dumps(coeff_dict, ensure_ascii=False),
                    "n_points": int(len(x)),
                    **metrics,
                }
            )
        except Exception:
            continue

    return results


def run_fitting(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    fits_rows = []
    metrics_rows = []

    for keys, group in df.groupby(GROUP_COLS):
        fit_results = fit_group(group)
        for result in fit_results:
            row = dict(zip(GROUP_COLS, keys))
            fits_rows.append(
                {
                    **row,
                    "model": result["model"],
                    "coefficients": result["coefficients"],
                    "n_points": result["n_points"],
                }
            )
            metrics_rows.append(
                {
                    **row,
                    "model": result["model"],
                    **{k: v for k, v in result.items() if k not in ["model", "coefficients"]},
                }
            )

    return pd.DataFrame(fits_rows), pd.DataFrame(metrics_rows)


def _poly_fit(x, y, degree: int):
    coeffs = np.polyfit(x, y, degree)
    p = np.poly1d(coeffs)
    return coeffs.tolist(), p(x)


def _power_fit(x, y):
    mask = (x > 0) & (y > 0)
    if np.sum(mask) < 3:
        return None, None
    lx = np.log(x[mask])
    ly = np.log(y[mask])
    b, loga = np.polyfit(lx, ly, 1)
    a = float(np.exp(loga))
    y_pred = np.full_like(y, np.nan, dtype=float)
    positive_x = x > 0
    y_pred[positive_x] = a * (x[positive_x] ** float(b))
    return [a, float(b)], y_pred


def _parse_coefficients(coefficients):
    if isinstance(coefficients, dict):
        if "c" in coefficients:
            return [float(coefficients["a"]), float(coefficients["b"]), float(coefficients["c"])]
        return [float(coefficients["a"]), float(coefficients["b"])]
    if isinstance(coefficients, str):
        try:
            return _parse_coefficients(json.loads(coefficients))
        except Exception:
            return None
    if isinstance(coefficients, (list, tuple, np.ndarray)):
        return [float(v) for v in coefficients]
    return None
