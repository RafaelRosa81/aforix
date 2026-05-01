from __future__ import annotations

import numpy as np
from sklearn.metrics import mean_squared_error, r2_score
from scipy.stats import pearsonr


def rmse(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.sqrt(np.mean((a - b) ** 2)))


def mae(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean(np.abs(a - b)))


def mape(a: np.ndarray, b: np.ndarray) -> float:
    mask = a != 0
    if not np.any(mask):
        return float("nan")
    return float(100.0 * np.mean(np.abs((b[mask] - a[mask]) / a[mask])))


def pbias(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.sum(a)
    if denom == 0:
        return float("nan")
    return float(100.0 * np.sum(b - a) / denom)


def nse(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.sum((a - np.mean(a)) ** 2)
    if denom == 0:
        return float("nan")
    return float(1.0 - np.sum((a - b) ** 2) / denom)


def r2(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 2:
        return float("nan")
    return float(r2_score(a, b))


def pearson(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 2:
        return float("nan")
    try:
        return float(pearsonr(a, b)[0])
    except Exception:
        return float("nan")
