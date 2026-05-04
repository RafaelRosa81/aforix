from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from aforix.analysis.stage_discharge.fitting import predict_model


GROUP_COLS = [
    "station_id",
    "analysis_group",
    "instrument",
    "stage_origin",
    "stage_type",
]


def write_best_model_plots(
    analysis_pairs: pd.DataFrame,
    best_models: pd.DataFrame,
    fits_df: pd.DataFrame,
    output_dir: Path,
    *,
    max_plots: int | None = None,
) -> Path:
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    if analysis_pairs.empty or best_models.empty or fits_df.empty:
        return plots_dir

    count = 0
    for _, best_row in best_models.iterrows():
        if max_plots is not None and count >= max_plots:
            break

        group_filter = _group_filter(analysis_pairs, best_row)
        group_data = analysis_pairs[group_filter].copy()
        if group_data.empty:
            continue

        fit_filter = _group_filter(fits_df, best_row) & (fits_df["model"] == best_row["model"])
        fit_rows = fits_df[fit_filter]
        if fit_rows.empty:
            continue

        fit_row = fit_rows.iloc[0]
        out_path = plots_dir / _plot_filename(best_row)
        _write_single_plot(group_data, best_row, fit_row, out_path)
        count += 1

    return plots_dir


def _write_single_plot(group_data: pd.DataFrame, best_row: pd.Series, fit_row: pd.Series, out_path: Path) -> None:
    x = pd.to_numeric(group_data["stage_m"], errors="coerce").to_numpy(dtype=float)
    y = pd.to_numeric(group_data["q_total_ls"], errors="coerce").to_numpy(dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]
    if len(x) < 2:
        return

    x_min, x_max = float(np.min(x)), float(np.max(x))
    if x_min == x_max:
        x_min *= 0.95
        x_max *= 1.05
    x_line = np.linspace(x_min, x_max, 100)
    y_line = predict_model(str(best_row["model"]), fit_row["coefficients"], x_line)

    plt.figure(figsize=(7, 5))
    plt.scatter(x, y, label="Observed")
    valid = np.isfinite(y_line)
    if valid.any():
        plt.plot(x_line[valid], y_line[valid], label=f"Fit: {best_row['model']}")

    title = (
        f"{best_row['station_id']} | {best_row['analysis_group']} | "
        f"{best_row['stage_origin']}:{best_row['stage_type']}"
    )
    plt.title(title)
    plt.xlabel("Stage / depth [m]")
    plt.ylabel("Discharge [L/s]")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.text(
        0.02,
        0.98,
        f"R²={best_row.get('r2', np.nan):.3f}\nRMSE={best_row.get('rmse', np.nan):.2f} L/s\nn={int(best_row.get('n_points', 0))}",
        transform=plt.gca().transAxes,
        va="top",
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.8},
    )
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()


def _group_filter(df: pd.DataFrame, row: pd.Series):
    mask = pd.Series(True, index=df.index)
    for col in GROUP_COLS:
        mask &= df[col].astype(str) == str(row[col])
    return mask


def _plot_filename(row: pd.Series) -> str:
    parts = [
        str(row["station_id"]),
        str(row["analysis_group"]),
        str(row["stage_origin"]),
        str(row["stage_type"]),
        str(row["model"]),
    ]
    safe = [p.replace(" ", "_").replace("/", "-").replace("\\", "-") for p in parts]
    return "_".join(safe) + ".png"
