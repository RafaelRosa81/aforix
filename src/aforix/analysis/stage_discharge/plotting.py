from pathlib import Path

import matplotlib

matplotlib.use("Agg")

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
    max_plots: int | None = 40,
) -> Path:
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    if analysis_pairs.empty or best_models.empty or fits_df.empty:
        return plots_dir

    count = 0
    log_rows = []
    for _, best_row in best_models.iterrows():
        if max_plots is not None and count >= max_plots:
            break

        try:
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
            ok = _write_single_plot(group_data, best_row, fit_row, out_path)
            if ok:
                count += 1
                log_rows.append({"plot": out_path.name, "status": "ok"})
        except Exception as exc:
            log_rows.append({"plot": _plot_filename(best_row), "status": "failed", "message": str(exc)})
            plt.close("all")
            continue

    pd.DataFrame(log_rows).to_csv(plots_dir / "plot_log.csv", index=False, encoding="utf-8-sig")
    return plots_dir


def _write_single_plot(group_data: pd.DataFrame, best_row: pd.Series, fit_row: pd.Series, out_path: Path) -> bool:
    x = pd.to_numeric(group_data["stage_m"], errors="coerce").to_numpy(dtype=float)
    y = pd.to_numeric(group_data["q_total_ls"], errors="coerce").to_numpy(dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]
    if len(x) < 2:
        return False

    x_min, x_max = float(np.min(x)), float(np.max(x))
    if x_min == x_max:
        delta = abs(x_min) * 0.05 if x_min != 0 else 0.05
        x_min -= delta
        x_max += delta
    x_line = np.linspace(x_min, x_max, 80)
    y_line = predict_model(str(best_row["model"]), fit_row["coefficients"], x_line)

    fig, ax = plt.subplots(figsize=(6, 4), dpi=120)
    try:
        ax.scatter(x, y, label="Observed", s=20)
        valid = np.isfinite(y_line)
        if valid.any():
            ax.plot(x_line[valid], y_line[valid], label=f"Fit: {best_row['model']}")

        title = (
            f"{best_row['station_id']} | {best_row['analysis_group']} | "
            f"{best_row['stage_origin']}:{best_row['stage_type']}"
        )
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("Stage / depth [m]")
        ax.set_ylabel("Discharge [L/s]")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)
        ax.text(
            0.02,
            0.98,
            f"R²={best_row.get('r2', np.nan):.3f}\nRMSE={best_row.get('rmse', np.nan):.2f} L/s\nn={int(best_row.get('n_points', 0))}",
            transform=ax.transAxes,
            va="top",
            fontsize=8,
            bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.8},
        )
        fig.savefig(out_path, dpi=120, bbox_inches="tight")
        return True
    finally:
        plt.close(fig)


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
