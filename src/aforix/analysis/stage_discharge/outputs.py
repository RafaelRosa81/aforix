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

    df.to_csv(diagnostic_path, index=False)

    matched = _build_matched_pairs(df)
    matched.to_csv(matched_path, index=False)

    analysis_clean, analysis_log_rows = _clean_analysis_pairs(analysis_pairs)
    analysis_clean.to_csv(analysis_path, index=False)

    log = _build_log(df, matched, analysis_clean, analysis_log_rows)
    log.to_csv(log_path, index=False)

    return out_dir


def _build_matched_pairs(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=MATCHED_COLUMNS)

    out = pd.DataFrame(index=df.index)
    for col in MATCHED_COLUMNS:
        out[col] = _pick_column(df, col)

    out = out.dropna(how="all")
    out = out.dropna(axis=1, how="all")
    return out.reset_index(drop=True)


def _clean_analysis_pairs(analysis_pairs: pd.DataFrame | None) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    if analysis_pairs is None or analysis_pairs.empty:
        empty = pd.DataFrame(columns=ANALYSIS_COLUMNS)
        return empty, [
            {"metric": "analysis_rows_input", "value": 0},
            {"metric": "analysis_rows_output", "value": 0},
            {"metric": "analysis_rows_removed_missing_required", "value": 0},
        ]

    df = analysis_pairs.copy()
    rows_input = len(df)

    out = pd.DataFrame(index=df.index)
    for col in ANALYSIS_COLUMNS:
        out[col] = _pick_column(df, col)

    out["q_total_ls"] = pd.to_numeric(out["q_total_ls"], errors="coerce")
    out["q_total_m3s"] = pd.to_numeric(out["q_total_m3s"], errors="coerce")
    out["stage_m"] = pd.to_numeric(out["stage_m"], errors="coerce")

    before_required = len(out)
    out = out.dropna(subset=REQUIRED_ANALYSIS_COLUMNS)
    removed_missing = before_required - len(out)

    out = out.dropna(how="all")
    out = out.dropna(axis=1, how="all")
    out = out.sort_values(["station_id", "measurement_date", "analysis_group", "stage_origin", "stage_type"]).reset_index(drop=True)

    log_rows = [
        {"metric": "analysis_rows_input", "value": int(rows_input)},
        {"metric": "analysis_rows_output", "value": int(len(out))},
        {"metric": "analysis_rows_removed_missing_required", "value": int(removed_missing)},
    ]

    if "stage_origin" in out.columns:
        for key, value in out["stage_origin"].value_counts(dropna=False).items():
            log_rows.append({"metric": f"analysis_stage_origin.{key}", "value": int(value)})
    if "stage_type" in out.columns:
        for key, value in out["stage_type"].value_counts(dropna=False).items():
            log_rows.append({"metric": f"analysis_stage_type.{key}", "value": int(value)})

    return out, log_rows


def _pick_column(df: pd.DataFrame, base_name: str) -> pd.Series:
    candidates = [base_name, f"{base_name}_x", f"{base_name}_y"]
    for col in candidates:
        if col in df.columns:
            return df[col]
    return pd.Series([pd.NA] * len(df), index=df.index)


def _build_log(
    df: pd.DataFrame,
    matched: pd.DataFrame,
    analysis_clean: pd.DataFrame,
    analysis_log_rows: list[dict[str, object]],
) -> pd.DataFrame:
    rows = [
        {"metric": "rows_diagnostic", "value": int(len(df))},
        {"metric": "rows_matched", "value": int(len(matched))},
        {"metric": "rows_analysis", "value": int(len(analysis_clean))},
    ]

    if "manual_stage_m" in matched.columns:
        rows.append({"metric": "manual_stage_matched", "value": int(matched["manual_stage_m"].notna().sum())})
        rows.append({"metric": "manual_stage_missing", "value": int(matched["manual_stage_m"].isna().sum())})

    if "analysis_group" in matched.columns:
        counts = matched["analysis_group"].value_counts(dropna=False)
        for key, value in counts.items():
            rows.append({"metric": f"analysis_group.{key}", "value": int(value)})

    if "instrument" in matched.columns:
        counts = matched["instrument"].value_counts(dropna=False)
        for key, value in counts.items():
            rows.append({"metric": f"instrument.{key}", "value": int(value)})

    rows.extend(analysis_log_rows)
    return pd.DataFrame(rows)
