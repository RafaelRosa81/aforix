from datetime import datetime
from pathlib import Path

import pandas as pd


CLEAN_COLUMNS = [
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
    "source_file",
    "run_id",
]


def write_outputs(df: pd.DataFrame, output_root: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = output_root / ts
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_path = out_dir / "stage_discharge_matched_pairs_raw.csv"
    clean_path = out_dir / "stage_discharge_matched_pairs.csv"
    log_path = out_dir / "stage_discharge_log.csv"

    df.to_csv(raw_path, index=False)

    clean = _build_clean_matched_pairs(df)
    clean.to_csv(clean_path, index=False)

    log = _build_log(df, clean)
    log.to_csv(log_path, index=False)

    return out_dir


def _build_clean_matched_pairs(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=CLEAN_COLUMNS)

    out = pd.DataFrame(index=df.index)
    for col in CLEAN_COLUMNS:
        out[col] = _pick_column(df, col)

    out = out.dropna(axis=1, how="all")
    return out.reset_index(drop=True)


def _pick_column(df: pd.DataFrame, base_name: str) -> pd.Series:
    candidates = [base_name, f"{base_name}_x", f"{base_name}_y"]
    for col in candidates:
        if col in df.columns:
            return df[col]
    return pd.Series([pd.NA] * len(df), index=df.index)


def _build_log(df: pd.DataFrame, clean: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame([
            {"metric": "rows_raw", "value": 0},
            {"metric": "rows_clean", "value": 0},
        ])

    rows = [
        {"metric": "rows_raw", "value": int(len(df))},
        {"metric": "rows_clean", "value": int(len(clean))},
    ]

    if "manual_stage_m" in clean.columns:
        rows.append({"metric": "manual_stage_matched", "value": int(clean["manual_stage_m"].notna().sum())})
        rows.append({"metric": "manual_stage_missing", "value": int(clean["manual_stage_m"].isna().sum())})

    if "analysis_group" in clean.columns:
        counts = clean["analysis_group"].value_counts(dropna=False)
        for key, value in counts.items():
            rows.append({"metric": f"analysis_group.{key}", "value": int(value)})

    if "instrument" in clean.columns:
        counts = clean["instrument"].value_counts(dropna=False)
        for key, value in counts.items():
            rows.append({"metric": f"instrument.{key}", "value": int(value)})

    return pd.DataFrame(rows)
