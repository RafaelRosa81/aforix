from datetime import datetime
from pathlib import Path

import pandas as pd


MATCHED_COLUMNS = [
    "station_id",
    "station_name",
    "measurement_date",
    "measurement_time",
    "analysis_group",
    "instrument",
    "rank",
    "q_total_ls",
    "q_total_m3s",
    "manual_stage_m",
    "normalized_source_table",
    "original_source_file",
    "manual_stage_source_table",
    "run_id",
]

ANALYSIS_COLUMNS = [
    "station_id",
    "station_name",
    "measurement_date",
    "measurement_time",
    "analysis_group",
    "instrument",
    "rank",
    "q_total_ls",
    "q_total_m3s",
    "stage_origin",
    "stage_type",
    "stage_source",
    "stage_m",
    "normalized_source_table",
    "original_source_file",
    "run_id",
]

REQUIRED_ANALYSIS_COLUMNS = ["station_id", "measurement_date", "analysis_group", "instrument", "q_total_ls", "stage_m"]


def write_outputs(df: pd.DataFrame, output_root: Path, analysis_pairs: pd.DataFrame | None = None) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = output_root / ts
    out_dir.mkdir(parents=True, exist_ok=True)

    diagnostic_path = out_dir / "stage_discharge_matched_pairs_diagnostic.csv"
    matched_path = out_dir / "stage_discharge_matched_pairs.csv"
    analysis_path = out_dir / "stage_discharge_analysis_pairs.csv"
    log_path = out_dir / "stage_discharge_log.csv"

    df.to_csv(diagnostic_path, index=False, encoding="utf-8-sig")

    matched = _build_matched_pairs(df)
    matched.to_csv(matched_path, index=False, encoding="utf-8-sig")

    analysis_clean, analysis_log_rows = _clean_analysis_pairs(analysis_pairs)
    analysis_clean.to_csv(analysis_path, index=False, encoding="utf-8-sig")

    log = _build_log(df, matched, analysis_clean, analysis_log_rows)
    log.to_csv(log_path, index=False, encoding="utf-8-sig")

    return out_dir

# (rest unchanged)
