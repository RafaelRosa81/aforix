from pathlib import Path

import pandas as pd


KEYS = ["station_id", "measurement_date", "measurement_time", "instrument"]


def load_manual_stage(manual_dir: Path) -> pd.DataFrame:
    f = manual_dir / "manual_stage.csv"
    if not f.exists():
        return pd.DataFrame()
    df = pd.read_csv(f)
    if "measurement_date" in df.columns:
        df["measurement_date"] = _normalize_measurement_date(df["measurement_date"])
    if "station_id" in df.columns:
        df["station_id"] = df["station_id"].map(_normalize_station_id)
    df["manual_stage_source_table"] = str(f)
    return df


def load_summary_tables(normalized_root: Path, instruments_cfg: dict) -> pd.DataFrame:
    """Load normalized Summary data from database/normalized."""
    summary_file = normalized_root / "Summary.csv"
    enabled_instruments = {name for name, cfg in instruments_cfg.items() if cfg.get("enabled", False)}

    if summary_file.exists():
        df = pd.read_csv(summary_file)
        df = _standardize_dates_ids_instrument(df)
        if "instrument" in df.columns and enabled_instruments:
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

        files = [path] if path.is_file() else sorted(path.glob("*.csv"))
        for f in files:
            df = pd.read_csv(f)
            df = _standardize_dates_ids_instrument(df)
            df["instrument"] = inst
            df["normalized_source_table"] = str(f)
            if "source_file" in df.columns:
                df = df.rename(columns={"source_file": "original_source_file"})
            dfs.append(df)

    if not dfs:
        return pd.DataFrame()

    return pd.concat(dfs, ignore_index=True)


def load_points_max_stage(normalized_root: Path, instruments_cfg: dict) -> pd.DataFrame:
    """Compute instrument max stage/depth from normalized Points.csv.

    Uses depth_m when available and groups by measurement identity.
    """
    points_file = normalized_root / "Points.csv"
    enabled_instruments = {name for name, cfg in instruments_cfg.items() if cfg.get("enabled", False)}

    if not points_file.exists():
        return pd.DataFrame(columns=KEYS + ["instrument_stage_max_m", "points_source_table"])

    df = pd.read_csv(points_file)
    df = _standardize_dates_ids_instrument(df)

    if "instrument" in df.columns and enabled_instruments:
        df = df[df["instrument"].isin(enabled_instruments)].copy()

    if "depth_m" not in df.columns:
        return pd.DataFrame(columns=KEYS + ["instrument_stage_max_m", "points_source_table"])

    for key in KEYS:
        if key not in df.columns:
            df[key] = pd.NA

    df["depth_m"] = pd.to_numeric(df["depth_m"], errors="coerce")
    out = (
        df.dropna(subset=["station_id", "measurement_date", "instrument", "depth_m"])
        .groupby(KEYS, dropna=False, as_index=False)["depth_m"]
        .max()
        .rename(columns={"depth_m": "instrument_stage_max_m"})
    )
    out["points_source_table"] = str(points_file)
    return out


def add_points_max_stage(df_summary: pd.DataFrame, df_points_max: pd.DataFrame) -> pd.DataFrame:
    if df_summary.empty or df_points_max.empty:
        return df_summary

    join_keys = [k for k in KEYS if k in df_summary.columns and k in df_points_max.columns]
    if not join_keys:
        return df_summary

    return df_summary.merge(df_points_max, on=join_keys, how="left")


def _standardize_dates_ids_instrument(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "measurement_date" in df.columns:
        df["measurement_date"] = _normalize_measurement_date(df["measurement_date"])
    elif "date" in df.columns:
        df["measurement_date"] = _normalize_measurement_date(df["date"])

    if "station_id" in df.columns:
        df["station_id"] = df["station_id"].map(_normalize_station_id)
    elif "point" in df.columns:
        df["station_id"] = df["point"].map(_normalize_station_id)

    if "instrument" in df.columns:
        df["instrument"] = df["instrument"].astype(str).str.lower().str.strip()

    return df


def _normalize_measurement_date(values: pd.Series) -> pd.Series:
    """Return ISO dates while preserving compact YYYYMMDD identifiers.

    Pandas interprets numeric values such as 20251217 as nanoseconds from the
    Unix epoch unless an explicit format is supplied. Normalized Aforix tables
    commonly use that compact form, so parse it before generic date parsing.
    """
    raw = values.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)
    out = pd.Series(pd.NaT, index=values.index, dtype="datetime64[ns]")

    compact_mask = raw.str.fullmatch(r"\d{8}", na=False)
    if compact_mask.any():
        out.loc[compact_mask] = pd.to_datetime(raw.loc[compact_mask], format="%Y%m%d", errors="coerce")

    other_mask = ~compact_mask & raw.notna() & raw.ne("")
    if other_mask.any():
        out.loc[other_mask] = pd.to_datetime(raw.loc[other_mask], errors="coerce")

    return out.dt.strftime("%Y-%m-%d")


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