from pathlib import Path

import pandas as pd

from aforix.analysis.stage_discharge.config import load_stage_discharge_config
from aforix.analysis.stage_discharge.inputs import (
    load_manual_stage,
    load_summary_tables,
    load_points_max_stage,
    add_points_max_stage,
)
from aforix.analysis.stage_discharge.matching import match_manual_and_instrument
from aforix.analysis.stage_discharge.instrument_selection import apply_ranking
from aforix.analysis.stage_discharge.outputs import write_outputs
from aforix.analysis.stage_discharge.stage_sources import build_analysis_pairs
from aforix.analysis.stage_discharge.fitting import run_fitting
from aforix.analysis.stage_discharge.model_selection import select_best_models
from aforix.analysis.stage_discharge.plotting import write_best_model_plots
from aforix.analysis.stage_discharge.excel import write_excel_report


def run_stage_discharge(config_path: Path, override_config: dict | None = None) -> Path:
    cfg = override_config or load_stage_discharge_config(config_path)

    normalized_root = Path(cfg.get("input_dirs", {}).get("normalized_root", "database/normalized"))
    manual_root = Path(cfg.get("input_dirs", {}).get("manual_stage_root", "database/external/normalized/manual_stage"))
    output_root = Path(cfg.get("output", {}).get("run_output_root", "runs/analysis_stage_discharge"))

    instruments_cfg = cfg.get("instruments", {})
    ranking = cfg.get("instrument_selection", {}).get("ranking", [])

    selection_cfg = cfg.get("selection", {}) or {}
    depth_mode = selection_cfg.get("depth_mode", cfg.get("depth_mode", "both"))
    instrument_stage_mode = selection_cfg.get("instrument_stage_mode", cfg.get("instrument_stage_mode", "both"))
    selected_points = selection_cfg.get("points", "all")
    start_date = selection_cfg.get("start_date")
    end_date = selection_cfg.get("end_date")

    df_summary = load_summary_tables(normalized_root, instruments_cfg)
    df_points_max = load_points_max_stage(normalized_root, instruments_cfg)
    df_summary = add_points_max_stage(df_summary, df_points_max)

    df_manual = load_manual_stage(manual_root)

    df = match_manual_and_instrument(df_summary, df_manual)
    df = _filter_selected_points(df, selected_points)
    df = _filter_date_range(df, start_date=start_date, end_date=end_date)
    df = apply_ranking(df, ranking)

    analysis_pairs = build_analysis_pairs(
        df,
        depth_mode=depth_mode,
        instrument_stage_mode=instrument_stage_mode,
    )

    out_dir = write_outputs(df, output_root, analysis_pairs=analysis_pairs)

    fits_df, metrics_df = run_fitting(analysis_pairs)
    fits_df.to_csv(out_dir / "stage_discharge_fits.csv", index=False, encoding="utf-8-sig")
    metrics_df.to_csv(out_dir / "stage_discharge_metrics.csv", index=False, encoding="utf-8-sig")

    best_df = select_best_models(metrics_df)
    best_df.to_csv(out_dir / "stage_discharge_best_models.csv", index=False, encoding="utf-8-sig")

    plotting_cfg = cfg.get("plotting", {}) or {}
    if plotting_cfg.get("enabled", True):
        write_best_model_plots(
            analysis_pairs=analysis_pairs,
            best_models=best_df,
            fits_df=fits_df,
            output_dir=out_dir,
            max_plots=plotting_cfg.get("max_plots", 40),
        )

    excel_cfg = cfg.get("excel", {}) or {}
    if excel_cfg.get("enabled", True):
        write_excel_report(
            output_dir=out_dir,
            matched=df,
            analysis_pairs=analysis_pairs,
            fits=fits_df,
            metrics=metrics_df,
            best_models=best_df,
            config=cfg,
        )

    return out_dir


def _filter_selected_points(df, selected_points):
    if selected_points is None or selected_points == "all":
        return df
    if isinstance(selected_points, str):
        if selected_points.strip().lower() == "all":
            return df
        points = [selected_points]
    else:
        points = list(selected_points)
    normalized_points = {_normalize_station_id(p) for p in points}
    if "station_id" not in df.columns or not normalized_points:
        return df
    return df[df["station_id"].map(_normalize_station_id).isin(normalized_points)].copy()


def _filter_date_range(df, *, start_date=None, end_date=None):
    if df.empty or "measurement_date" not in df.columns:
        return df
    if not start_date and not end_date:
        return df

    out = df.copy()
    dates = pd.to_datetime(out["measurement_date"], errors="coerce")
    mask = dates.notna()
    if start_date:
        start = pd.to_datetime(start_date, errors="coerce")
        if pd.notna(start):
            mask &= dates >= start
    if end_date:
        end = pd.to_datetime(end_date, errors="coerce")
        if pd.notna(end):
            mask &= dates <= end
    return out[mask].copy()


def _normalize_station_id(value) -> str:
    s = str(value).strip().upper()
    if s.startswith("P"):
        digits = "".join(ch for ch in s[1:] if ch.isdigit())
    else:
        digits = "".join(ch for ch in s if ch.isdigit())
    return f"P{int(digits)}" if digits else s
