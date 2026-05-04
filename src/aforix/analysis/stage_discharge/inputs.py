from pathlib import Path

import pandas as pd


def load_manual_stage(manual_dir: Path) -> pd.DataFrame:
    f = manual_dir / "manual_stage.csv"
    if not f.exists():
        return pd.DataFrame()
    df = pd.read_csv(f)
    if "measurement_date" in df.columns:
        df["measurement_date"] = pd.to_datetime(df["measurement_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    if "station_id" in df.columns:
        df["station_id"] = df["station_id"].map(_normalize_station_id)
    df["manual_stage_source_table"] = str(f)
    return df


def load_summary_tables(normalized_root: Path, instruments_cfg: dict) -> pd.DataFrame:
    """Load normalized Summary data.

    Prefer the stable concatenated table database/normalized/Summary.csv.
    Fall back to per-instrument Summary locations when the concatenated table is absent.
    The original source_file column is preserved as traceability, but analysis input
    provenance is recorded separately in normalized_source_table.
    """
    summary_file = normalized_root / "Summary.csv"
    enabled_instruments = {name for name, cfg in instruments_cfg.items() if cfg.get("enabled", False)}

    if summary_file.exists():
        df = pd.read_csv(summary_file)
        df = _standardize_summary_dates_and_ids(df)
        if "instrument" in df.columns and enabled_instruments:
            df["instrument"] = df["instrument"].astype(str).str.lower().str.strip()
            df = df[df["instrument"].isin(enabled_instruments)].copy()
        df["normalized_source_table"] = str(summary_file)
        if "source_file" in df.columns:
            df = df.rename(columns={"source_file": "original_source_file"})
        return df.reset_index(drop=True)

    dfs = []
    for inst, cfg in instruments_cfg.items():
        if not cfg.get("enabled", False):
            continue

        subdir = cfg.get("summary_table")
        path = normalized_root / subdir
        if not path.exists():
            continue

        if path.is_file():
            files = [path]
        else:
            files = sorted(path.glob("*.csv"))

        for f in files:
            df = pd.read_csv(f)
            df = _standardize_summary_dates_and_ids(df)
            df["instrument"] = inst
            df["normalized_source_table"] = str(f)
            if "source_file" in df.columns:
                df = df.rename(columns={"source_file": "original_source_file"})
            dfs.append(df)

    if not dfs:
        return pd.DataFrame()

    return pd.concat(dfs, ignore_index=True)


def _standardize_summary_dates_and_ids(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "measurement_date" in df.columns:
        df["measurement_date"] = pd.to_datetime(df["measurement_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    elif "date" in df.columns:
        df["measurement_date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")

    if "station_id" in df.columns:
        df["station_id"] = df["station_id"].map(_normalize_station_id)
    elif "point" in df.columns:
        df["station_id"] = df["point"].map(_normalize_station_id)

    return df


def _normalize_station_id(value) -> str | None:
    if pd.isna(value):
        return None
    s = str(value).strip().upper()
    if not s:
        return None
    if s.startswith("P"):
        digits = "".join(ch for ch in s[1:] if ch.isdigit())
    else:
        digits = "".join(ch for ch in s if ch.isdigit())
    if not digits:
        return s
    return f"P{int(digits)}"
