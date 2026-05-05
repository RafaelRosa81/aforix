from __future__ import annotations

import pandas as pd


def filter_instruments(df: pd.DataFrame, instruments: set[str] | None) -> pd.DataFrame:
    if df.empty or not instruments:
        return df
    if 'instrument' not in df.columns:
        return df
    return df[df['instrument'].isin(instruments)].copy()


def filter_points(df: pd.DataFrame, points: set[str] | None) -> pd.DataFrame:
    if df.empty or not points:
        return df
    if 'station_id' not in df.columns:
        return df
    return df[df['station_id'].isin(points)].copy()


def filter_date_range(df: pd.DataFrame, start_date: str | None, end_date: str | None) -> pd.DataFrame:
    if df.empty or 'measurement_date' not in df.columns:
        return df
    if not start_date and not end_date:
        return df

    out = df.copy()
    dates = pd.to_datetime(out['measurement_date'], errors='coerce')
    mask = dates.notna()

    if start_date:
        start = pd.to_datetime(start_date, errors='coerce')
        if pd.notna(start):
            mask &= dates >= start
    if end_date:
        end = pd.to_datetime(end_date, errors='coerce')
        if pd.notna(end):
            mask &= dates <= end
    return out[mask].copy()


def ensure_columns(df: pd.DataFrame, x_axis: str, y_axis: str) -> pd.DataFrame:
    if df.empty:
        return df
    cols = set(df.columns)
    missing = [c for c in (x_axis, y_axis) if c not in cols]
    if missing:
        return df.iloc[0:0].copy()
    return df
