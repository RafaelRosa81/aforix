from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def save_scatter_with_regression(
    data: pd.DataFrame,
    *,
    x_col: str,
    y_col: str,
    pred_col: str,
    x_label: str,
    y_label: str,
    out_path: Path,
) -> None:
    x = data[x_col].to_numpy()
    y = data[y_col].to_numpy()
    y_pred = data[pred_col].to_numpy()

    plt.figure()
    plt.scatter(x, y, label="Observed")
    if len(x) > 0:
        lo = np.nanmin(x)
        hi = np.nanmax(x)
        xs = np.linspace(lo, hi, 50)
        plt.plot(xs, xs, linestyle="--", label="1:1")
    plt.plot(x, y_pred, label="Regression")
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.legend()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()


def save_time_series(
    data: pd.DataFrame,
    *,
    time_col: str,
    series: list[tuple[str, str]],
    out_path: Path,
) -> None:
    plt.figure()
    t = pd.to_datetime(data[time_col])
    for col, label in series:
        plt.plot(t, data[col], label=label)
    plt.xlabel("Time")
    plt.ylabel("Flow [l/s]")
    plt.legend()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()
