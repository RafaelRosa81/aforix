from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd


def load_points_by_instrument(normalized_root: Path, instruments_cfg: Dict) -> pd.DataFrame:
    dfs: list[pd.DataFrame] = []

    for inst_name, cfg in instruments_cfg.items():
        if not cfg.get('enabled', False):
            continue

        sub = cfg.get('points_table') or cfg.get('points_path')
        if not sub:
            continue

        path = normalized_root / sub
        if not path.exists():
            continue

        files = [path] if path.is_file() else sorted(path.glob('*.csv'))
        for f in files:
            try:
                df = pd.read_csv(f)
            except Exception:
                continue
            if df.empty:
                continue
            df = _standardize(df)
            df['instrument'] = inst_name
            df['instrument_code'] = cfg.get('code', inst_name)
            df['normalized_source_table'] = str(f)
            dfs.append(df)

    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)


def _standardize(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if 'measurement_date' in out.columns:
        out['measurement_date'] = pd.to_datetime(out['measurement_date'], errors='coerce').dt.strftime('%Y-%m-%d')
    elif 'date' in out.columns:
        out['measurement_date'] = pd.to_datetime(out['date'], errors='coerce').dt.strftime('%Y-%m-%d')

    if 'station_id' in out.columns:
        out['station_id'] = out['station_id'].map(_norm_station)
    elif 'point' in out.columns:
        out['station_id'] = out['point'].map(_norm_station)

    if 'measurement_time' in out.columns:
        out['measurement_time'] = out['measurement_time'].astype(str)

    return out


def _norm_station(v) -> str | None:
    if pd.isna(v):
        return None
    s = str(v).strip().upper()
    if not s:
        return None
    if s.startswith('P'):
        digits = ''.join(ch for ch in s[1:] if ch.isdigit())
    else:
        digits = ''.join(ch for ch in s if ch.isdigit())
    if not digits:
        return s
    return f"P{int(digits)}"
