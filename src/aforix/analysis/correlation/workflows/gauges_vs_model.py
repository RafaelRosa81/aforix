from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.linear_model import LinearRegression

from aforix.analysis.correlation.io.model import load_model_data
from aforix.analysis.correlation.metrics import rmse, r2, pearson


def run_gauges_vs_model(model_dir: Path, gauges: dict[str, pd.DataFrame]) -> None:
    """Minimal working version of gauges vs model correlation.

    NOTE: X = gauges, Y = model (corrected semantics).
    """

    modeled = load_model_data(model_dir)

    for point, df_model in modeled.items():
        if point not in gauges:
            continue

        df_g = gauges[point]

        merged = pd.merge(df_model, df_g, on="date", how="inner")
        if merged.empty:
            continue

        x = merged["q_gauge_l/s"].to_numpy().reshape(-1, 1)
        y = merged["q_model_l/s"].to_numpy()

        lr = LinearRegression().fit(x, y)
        y_pred = lr.predict(x)

        print(f"P{point}")
        print(f"  slope={lr.coef_[0]:.3f} intercept={lr.intercept_:.3f}")
        print(f"  R2={r2(y, y_pred):.3f} RMSE={rmse(y, y_pred):.3f} r={pearson(x.flatten(), y):.3f}")
