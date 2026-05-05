from __future__ import annotations

import re
from pathlib import Path
from typing import Dict

import pandas as pd

FILENAME_RE = re.compile(r"(?P<station>P\d+)_Points_(?P<date>\d{8})(?:_(?P<time>\d{6}))?", re.IGNORECASE)


def load_points_by_instrument(normalized_root: Path, instruments_cfg: Dict) -> pd.DataFrame:
    dfs: list[pd.DataFrame] = []

    for inst_name, cfg in instruments_cfg.items():
        if not cfg.get("enabled", False):
            continue

        sub = cfg.get("points_table") or cfg.get("points_path")
        if not sub:
            continue

        path = normalized_root / sub
        if not path.exists():
            continue

        files = [path] if path.is_file() else sorted(path.glob("*.csv"))
        for f in files:
            try:
                df = pd.read_csv(f)
            except Exception:
                continue
            if df.empty:
                continue

            meta = _metadata_from_filename(f)
            df = _standardize(df, meta=meta)
            df["instrument"] = inst_name
            df["instrument_code"] = cfg.get("code", inst_name)
            df["normalized_source_table"] = str(f)
            dfs.append(df)

    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)


def _metadata_from_filename(path: Path) -> dict[str, str | None]:
    match = FILENAME_RE.search(path.name)
    if not match:
        return {"station_id": None, "measurement_date": None, "measurement_time": None}

    raw_date = match.group("date")
    raw_time = match.group("time")
    date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
    time = None
    if raw_time:
        time = f"{raw_time[:2]}:{raw_time[2:4]}:{raw_time[4:6]}"

    return {
        "station_id": _norm_station(match.group("station")),
        "measurement_date": date,
        "measurement_time": time,
    }


def _standardize(df: pd.DataFrame, *, meta: dict[str, str | None]) -> pd.DataFrame:
    out = df.copy()

    parsed_date = None
    if "measurement_date" in out.columns:
        parsed_date = pd.to_datetime(out["measurement_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    elif "date" in out.columns:
        parsed_date = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")

    if parsed_date is not None:
        out["measurement_date"] = parsed_date
    else:
        out["measurement_date"] = pd.NA

    if meta.get("measurement_date"):
        invalid_date = out["measurement_date"].isna() | out["measurement_date"].isin(["NaT", "1970-01-01"])
        out.loc[invalid_date, "measurement_date"] = meta["measurement_date"]

    if "station_id" in out.columns:
        out["station_id"] = out["station_id"].map(_norm_station)
    elif "point" in out.columns:
        out["station_id"] = out["point"].map(_norm_station)
    else:
        out["station_id"] = pd.NA

    if meta.get("station_id"):
        out["station_id"] = out["station_id"].fillna(meta["station_id"])

    if "measurement_time" in out.columns:
        out["measurement_time"] = out["measurement_time"].astype(str).replace({"nan": pd.NA, "NaT": pd.NA})
    else:
        out["measurement_time"] = pd.NA

    if meta.get("measurement_time"):
        out["measurement_time"] = out["measurement_time"].fillna(meta["measurement_time"])

    return out


def _norm_station(v) -> str | None:
    if pd.isna(v):
        return None
    s = str(v).strip().upper()
    if not s:
        return None
    if s.startswith("P"):
        digits = "".join(ch for ch in s[1:] if ch.isdigit())
    else:
        digits = "".join(ch for ch in s if ch.isdigit())
    if not digits:
        return s
    return f"P{int(digits)}"
