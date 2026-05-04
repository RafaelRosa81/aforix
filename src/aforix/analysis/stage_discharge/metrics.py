import numpy as np


def regression_metrics(y_true, y_pred) -> dict[str, float]:
    y = np.asarray(y_true, dtype=float)
    yp = np.asarray(y_pred, dtype=float)

    mask = np.isfinite(y) & np.isfinite(yp)
    y = y[mask]
    yp = yp[mask]

    if len(y) == 0:
        return {"r2": np.nan, "rmse": np.nan, "mae": np.nan, "nrmse": np.nan, "bias": np.nan, "pbias_pct": np.nan, "nse": np.nan}

    residuals = y - yp
    ss_res = float(np.sum(residuals**2))
    ss_tot = float(np.sum((y - np.mean(y))**2))

    r2 = np.nan if ss_tot == 0 else 1.0 - ss_res / ss_tot
    rmse = float(np.sqrt(np.mean(residuals**2)))
    mae = float(np.mean(np.abs(residuals)))
    mean_y = float(np.mean(y))
    nrmse = np.nan if mean_y == 0 else rmse / mean_y
    bias = float(np.mean(yp - y))
    pbias_pct = np.nan if np.sum(y) == 0 else float(100.0 * np.sum(yp - y) / np.sum(y))
    nse = r2

    return {
        "r2": r2,
        "rmse": rmse,
        "mae": mae,
        "nrmse": nrmse,
        "bias": bias,
        "pbias_pct": pbias_pct,
        "nse": nse,
    }
