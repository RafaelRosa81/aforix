import pandas as pd


BASE_COLUMNS = [
    "station_id",
    "station_name",
    "measurement_date",
    "measurement_time",
    "analysis_group",
    "instrument",
    "rank",
    "q_total_ls",
    "q_total_m3s",
    "normalized_source_table",
    "original_source_file",
    "run_id",
]


def build_analysis_pairs(
    df: pd.DataFrame,
    *,
    depth_mode: str = "both",
    instrument_stage_mode: str = "both",
) -> pd.DataFrame:
    """Expand matched discharge-stage data to long analytical form."""
    if df.empty:
        return _empty_analysis_pairs()

    depth_mode = _normalize_depth_mode(depth_mode)
    instrument_stage_mode = _normalize_instrument_stage_mode(instrument_stage_mode)

    frames: list[pd.DataFrame] = []

    if depth_mode in {"manual", "both"}:
        frames.append(
            _make_stage_frame(
                df,
                stage_col="manual_stage_m",
                stage_origin="manual",
                stage_type="manual",
                stage_source="manual_stage_m",
            )
        )

    if depth_mode in {"instrument", "both"}:
        if instrument_stage_mode in {"mean", "both"}:
            frames.append(
                _make_stage_frame(
                    df,
                    stage_col="depth_mean_m",
                    stage_origin="instrument",
                    stage_type="mean",
                    stage_source="depth_mean_m",
                )
            )
        if instrument_stage_mode in {"max", "both"}:
            max_col = _first_existing_column(df, ["max_depth_m", "instrument_stage_max_m"])
            frames.append(
                _make_stage_frame(
                    df,
                    stage_col=max_col,
                    stage_origin="instrument",
                    stage_type="max",
                    stage_source=max_col,
                )
            )

    if not frames:
        return _empty_analysis_pairs()

    out = pd.concat(frames, ignore_index=True)
    out = out.dropna(subset=["station_id", "measurement_date", "q_total_ls", "stage_m"])
    return out.reset_index(drop=True)


def _make_stage_frame(
    df: pd.DataFrame,
    *,
    stage_col: str | None,
    stage_origin: str,
    stage_type: str,
    stage_source: str | None,
) -> pd.DataFrame:
    out = pd.DataFrame(index=df.index)
    for col in BASE_COLUMNS:
        out[col] = _pick_column(df, col)
    out["stage_origin"] = stage_origin
    out["stage_type"] = stage_type
    out["stage_source"] = stage_source
    out["stage_m"] = _pick_column(df, stage_col) if stage_col else pd.NA
    return out


def _pick_column(df: pd.DataFrame, base_name: str | None) -> pd.Series:
    if base_name is None:
        return pd.Series([pd.NA] * len(df), index=df.index)
    candidates = [base_name, f"{base_name}_x", f"{base_name}_y"]
    for col in candidates:
        if col in df.columns:
            return df[col]
    return pd.Series([pd.NA] * len(df), index=df.index)


def _first_existing_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def _normalize_depth_mode(value: str) -> str:
    v = str(value or "both").strip().lower()
    aliases = {"ambas": "both", "instrumento": "instrument"}
    v = aliases.get(v, v)
    if v not in {"manual", "instrument", "both"}:
        raise ValueError("depth_mode must be one of: manual, instrument, both")
    return v


def _normalize_instrument_stage_mode(value: str) -> str:
    v = str(value or "both").strip().lower()
    aliases = {"ambas": "both", "media": "mean", "maxima": "max", "máxima": "max"}
    v = aliases.get(v, v)
    if v not in {"mean", "max", "both"}:
        raise ValueError("instrument_stage_mode must be one of: mean, max, both")
    return v


def _empty_analysis_pairs() -> pd.DataFrame:
    cols = BASE_COLUMNS + ["stage_origin", "stage_type", "stage_source", "stage_m"]
    return pd.DataFrame(columns=cols)
