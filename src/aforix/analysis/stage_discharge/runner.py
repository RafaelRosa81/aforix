from pathlib import Path

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


def run_stage_discharge(config_path: Path) -> Path:
    cfg = load_stage_discharge_config(config_path)

    normalized_root = Path(cfg.get("input_dirs", {}).get("normalized_root", "database/normalized"))
    manual_root = Path(cfg.get("input_dirs", {}).get("manual_stage_root", "database/external/normalized/manual_stage"))
    output_root = Path(cfg.get("output", {}).get("run_output_root", "runs/analysis_stage_discharge"))

    instruments_cfg = cfg.get("instruments", {})
    ranking = cfg.get("instrument_selection", {}).get("ranking", [])

    selection_cfg = cfg.get("selection", {}) or {}
    depth_mode = selection_cfg.get("depth_mode", cfg.get("depth_mode", "both"))
    instrument_stage_mode = selection_cfg.get("instrument_stage_mode", cfg.get("instrument_stage_mode", "both"))

    df_summary = load_summary_tables(normalized_root, instruments_cfg)
    df_points_max = load_points_max_stage(normalized_root, instruments_cfg)
    df_summary = add_points_max_stage(df_summary, df_points_max)

    df_manual = load_manual_stage(manual_root)

    df = match_manual_and_instrument(df_summary, df_manual)
    df = apply_ranking(df, ranking)

    analysis_pairs = build_analysis_pairs(
        df,
        depth_mode=depth_mode,
        instrument_stage_mode=instrument_stage_mode,
    )

    out_dir = write_outputs(df, output_root, analysis_pairs=analysis_pairs)

    # Fitting
    fits_df, metrics_df = run_fitting(analysis_pairs)
    fits_df.to_csv(out_dir / "stage_discharge_fits.csv", index=False, encoding="utf-8-sig")
    metrics_df.to_csv(out_dir / "stage_discharge_metrics.csv", index=False, encoding="utf-8-sig")

    # Model selection
    best_df = select_best_models(metrics_df)
    best_df.to_csv(out_dir / "stage_discharge_best_models.csv", index=False, encoding="utf-8-sig")

    # Plotting
    write_best_model_plots(
        analysis_pairs=analysis_pairs,
        best_models=best_df,
        fits_df=fits_df,
        output_dir=out_dir,
    )

    return out_dir
