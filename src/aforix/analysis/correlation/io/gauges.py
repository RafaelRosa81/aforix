from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterable, List

import pandas as pd

from aforix.analysis.correlation.types import MeasuringInstrument

_SUMMARY_RE = re.compile(r"^P(\d+)_Summary_(\d{8})_(\d{6})\.csv$")
_MIN_VALID_DATE = pd.Timestamp("1990-01-01")


def _to_lps(values: pd.Series, unit: str) -> pd.Series:
    unit_norm = unit.strip().lower().replace(" ", "")
    vals = pd.to_numeric(values, errors="coerce")
    if unit_norm in {"m3/s", "m^3/s", "m3s", "cms"}:
        return vals * 1000.0
    return vals


def _date_from_summary_filename(path: Path) -> pd.Timestamp | None:
    match = _SUMMARY_RE.match(path.name)
    if not match:
        return None
    return pd.to_datetime(match.group(2), format="%Y%m%d", errors="coerce")


def _point_from_summary_filename(path: Path) -> str | None:
    match = _SUMMARY_RE.match(path.name)
    if not match:
        return None
    return match.group(1)


def _find_col(df: pd.DataFrame, candidates: list[str], *, allow_contains: bool = True) -> str | None:
    lowered = {str(c).lower(): c for c in df.columns}
    for c in candidates:
        if c.lower() in lowered:
            return lowered[c.lower()]
    if allow_contains:
        for original in df.columns:
            lo = str(original).lower()
            if any(c.lower() in lo for c in candidates):
                return original
    return None


def _parse_dates(series: pd.Series) -> pd.Series:
    raw = series.astype(str).str.strip()
    parsed = pd.to_datetime(raw, format="%Y%m%d", errors="coerce")
    missing = parsed.isna()
    if missing.any():
        parsed.loc[missing] = pd.to_datetime(raw.loc[missing], errors="coerce", dayfirst=True)
    return parsed.dt.normalize()


def _source_key(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", "", str(value).upper())


def _build_source_code_map(instruments: Iterable[MeasuringInstrument]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for instrument in instruments:
        code = instrument.code.upper().strip()
        for value in (instrument.code, instrument.name, instrument.subdir):
            if value:
                mapping[_source_key(value)] = code
    return mapping


def _normalize_source_series(series: pd.Series, source_code_map: dict[str, str]) -> pd.Series:
    raw = series.astype(str).str.upper().str.strip()
    return raw.map(lambda value: source_code_map.get(_source_key(value), value))


def _load_summary_table(path: Path, default_source: str | None = None) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()

    df = pd.read_csv(path)
    if df.empty:
        return pd.DataFrame()

    point_col = _find_col(df, ["station_id", "point", "point_id", "measurement_point", "punto", "site", "station", "p"])
    date_col = _find_col(df, ["measurement_date", "date", "fecha", "datetime"], allow_contains=False)
    source_col = _find_col(df, ["instrument", "source", "instrument_code", "instrument_used", "source_code"])
    q_col = _find_col(df, ["q_l/s", "q_ls", "q_total_ls", "q_mean_ls", "q_meas_ls", "caudal_ls", "flow_ls"])
    q_m3s_col = _find_col(df, ["q_m3s", "q_total_m3s", "q(m3/s)", "caudal_m3s", "caudal", "q"])

    if not point_col or not date_col or (not q_col and not q_m3s_col):
        print(f"Summary table found but required columns were not detected: {path}. Columns={list(df.columns)}")
        return pd.DataFrame()

    out = pd.DataFrame()
    out["point"] = df[point_col].astype(str).str.replace("P", "", regex=False).str.strip()
    out["date"] = _parse_dates(df[date_col])
    out["source"] = df[source_col].astype(str).str.upper() if source_col else (default_source or "UNK").upper()
    out["source_table"] = str(path)

    if q_col:
        out["q_gauge_l/s"] = pd.to_numeric(df[q_col], errors="coerce")
    else:
        out["q_gauge_l/s"] = pd.to_numeric(df[q_m3s_col], errors="coerce") * 1000.0

    out = out.dropna(subset=["point", "date", "q_gauge_l/s"])
    out = out[out["date"] >= _MIN_VALID_DATE]
    return out


def _finalize_rows(
    df: pd.DataFrame,
    ranking_codes: list[str],
    source_code_map: dict[str, str],
) -> Dict[str, pd.DataFrame]:
    if df.empty:
        return {}

    out = df.copy()
    out["point"] = out["point"].astype(str).str.strip()
    out["source"] = _normalize_source_series(out["source"], source_code_map)
    out = out[out["point"].str.fullmatch(r"\d+")]
    if out.empty:
        return {}

    # First aggregate repeated measurements from the same instrument on the same
    # point/day. Then apply the inter-instrument ranking to choose one daily value.
    out = (
        out.groupby(["point", "date", "source"], as_index=False)["q_gauge_l/s"]
        .mean()
        .reset_index(drop=True)
    )

    normalized_ranking = [source_code_map.get(_source_key(code), str(code).upper()) for code in ranking_codes]
    rank = {code.upper(): idx for idx, code in enumerate(normalized_ranking)}
    out["rank"] = out["source"].map(lambda c: rank.get(str(c).upper(), 10_000))
    out = out.sort_values(["point", "date", "rank"]).drop_duplicates(["point", "date"], keep="first")
    out = out.drop(columns=["rank"])

    result: Dict[str, pd.DataFrame] = {}
    for point, group in out.groupby("point"):
        cols = ["date", "q_gauge_l/s", "source"]
        result[str(point)] = group[cols].sort_values("date").reset_index(drop=True)
    return result


def _load_matrix_summary(path: Path, instrument: MeasuringInstrument) -> tuple[pd.Timestamp | None, float | None]:
    df = pd.read_csv(path, header=None)
    flow_label = instrument.flow_row_label or "q [l/s]"
    mask = df[0].astype(str) == flow_label
    if not mask.any():
        return None, None
    q = _to_lps(df.loc[mask].iloc[0, 1:], instrument.flow_unit).dropna()
    if q.empty:
        return None, None
    return _date_from_summary_filename(path), float(q.mean())


def _load_wide_summary(path: Path, instrument: MeasuringInstrument) -> list[tuple[pd.Timestamp, float]]:
    df = pd.read_csv(path)
    if not instrument.flow_column or instrument.flow_column not in df.columns:
        return []
    d = df.copy()
    q = _to_lps(d[instrument.flow_column], instrument.flow_unit)
    date_col = None
    for candidate in ["measurement_date", "date", "datetime", "etime", "timestamp", "fecha"]:
        if candidate in d.columns:
            date_col = candidate
            break
    if date_col:
        dates = _parse_dates(d[date_col])
    else:
        fallback_date = _date_from_summary_filename(path)
        if fallback_date is None or pd.isna(fallback_date):
            return []
        dates = pd.Series([fallback_date.normalize()] * len(d), index=d.index)
    tmp = pd.DataFrame({"date": dates, "q_gauge_l/s": q}).dropna()
    tmp = tmp[tmp["date"] >= _MIN_VALID_DATE]
    if tmp.empty:
        return []
    grouped = tmp.groupby("date", as_index=False)["q_gauge_l/s"].mean()
    return [(pd.to_datetime(r["date"]).normalize(), float(r["q_gauge_l/s"])) for _, r in grouped.iterrows()]


def load_gauges_daily(
    normalized_root: Path,
    instruments: Iterable[MeasuringInstrument],
    ranking_codes: List[str],
) -> Dict[str, pd.DataFrame]:
    """Load daily gauge series from every available normalized Summary source.

    The loader combines all available Summary tables instead of trusting only the
    global Summary.csv. It normalizes instrument names to configured instrument
    codes before applying ranking, so the ranking is fully config-driven.
    """

    instruments_list = list(instruments)
    source_code_map = _build_source_code_map(instruments_list)
    frames: list[pd.DataFrame] = []

    global_summary = _load_summary_table(normalized_root / "Summary.csv")
    if not global_summary.empty:
        frames.append(global_summary)

    for instrument in instruments_list:
        table = _load_summary_table(
            normalized_root / instrument.subdir / "Summary.csv",
            default_source=instrument.code,
        )
        if not table.empty:
            frames.append(table)

    rows: list[dict[str, object]] = []
    for instrument in instruments_list:
        code = instrument.code.upper()
        summary_dir = normalized_root / instrument.subdir / "Summary"
        if not summary_dir.exists():
            continue
        for file in sorted(summary_dir.glob("P*_Summary_*.csv")):
            point = _point_from_summary_filename(file)
            if not point:
                continue
            if instrument.summary_format.lower() in {"matrix", "long", "row"}:
                date, q = _load_matrix_summary(file, instrument)
                if date is not None and q is not None and date >= _MIN_VALID_DATE:
                    rows.append({"point": point, "date": date.normalize(), "q_gauge_l/s": q, "source": code})
            else:
                for date, q in _load_wide_summary(file, instrument):
                    rows.append({"point": point, "date": date.normalize(), "q_gauge_l/s": q, "source": code})

    if rows:
        frames.append(pd.DataFrame(rows))

    if not frames:
        return {}

    all_rows = pd.concat(frames, ignore_index=True, sort=False)
    return _finalize_rows(all_rows, ranking_codes, source_code_map)
