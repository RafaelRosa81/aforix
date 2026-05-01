from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterable, List

import pandas as pd

from aforix.analysis.correlation.types import MeasuringInstrument

_SUMMARY_RE = re.compile(r"^P(\d+)_Summary_(\d{8})_(\d{6})\.csv$")


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


def _find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    lowered = {str(c).lower(): c for c in df.columns}
    for c in candidates:
        if c.lower() in lowered:
            return lowered[c.lower()]
    for original in df.columns:
        lo = str(original).lower()
        if any(c.lower() in lo for c in candidates):
            return original
    return None


def _load_summary_table(path: Path, ranking_codes: list[str], default_source: str | None = None) -> Dict[str, pd.DataFrame]:
    if not path.exists():
        return {}

    df = pd.read_csv(path)
    if df.empty:
        return {}

    point_col = _find_col(df, ["point", "point_id", "measurement_point", "punto", "site", "station", "p"])
    date_col = _find_col(df, ["date", "datetime", "fecha", "time"])
    source_col = _find_col(df, ["source", "instrument", "instrument_code", "instrument_used", "source_code"])

    q_col = _find_col(df, ["q_l/s", "q_ls", "q_total_ls", "q_mean_ls", "q_meas_ls", "caudal_ls", "flow_ls"])
    q_m3s_col = _find_col(df, ["q_m3s", "q(m3/s)", "caudal_m3s", "caudal", "q"])

    if not point_col or not date_col or (not q_col and not q_m3s_col):
        print(f"Summary table found but required columns were not detected: {path}. Columns={list(df.columns)}")
        return {}

    out = pd.DataFrame()
    out["point"] = df[point_col].astype(str).str.replace("P", "", regex=False).str.strip()
    out["date"] = pd.to_datetime(df[date_col], errors="coerce").dt.normalize()

    if source_col:
        out["source"] = df[source_col].astype(str).str.upper()
    else:
        out["source"] = (default_source or "UNK").upper()

    if q_col:
        out["q_gauge_l/s"] = pd.to_numeric(df[q_col], errors="coerce")
    else:
        out["q_gauge_l/s"] = pd.to_numeric(df[q_m3s_col], errors="coerce") * 1000.0

    out = out.dropna(subset=["point", "date", "q_gauge_l/s"])
    if out.empty:
        return {}

    rank = {code.upper(): idx for idx, code in enumerate(ranking_codes)}
    out["rank"] = out["source"].map(lambda c: rank.get(str(c).upper(), 10_000))
    out = out.sort_values(["point", "date", "rank"]).drop_duplicates(["point", "date"], keep="first")
    out = out.drop(columns=["rank"])

    result: Dict[str, pd.DataFrame] = {}
    for point, group in out.groupby("point"):
        result[str(point)] = group[["date", "q_gauge_l/s", "source"]].sort_values("date").reset_index(drop=True)
    return result


def _merge_gauge_dicts(dicts: list[Dict[str, pd.DataFrame]], ranking_codes: list[str]) -> Dict[str, pd.DataFrame]:
    rows = []
    for item in dicts:
        for point, df in item.items():
            d = df.copy()
            d["point"] = point
            rows.append(d)
    if not rows:
        return {}

    all_rows = pd.concat(rows, ignore_index=True)
    rank = {code.upper(): idx for idx, code in enumerate(ranking_codes)}
    all_rows["rank"] = all_rows["source"].map(lambda c: rank.get(str(c).upper(), 10_000))
    all_rows = all_rows.sort_values(["point", "date", "rank"]).drop_duplicates(["point", "date"], keep="first")
    all_rows = all_rows.drop(columns=["rank"])

    result: Dict[str, pd.DataFrame] = {}
    for point, group in all_rows.groupby("point"):
        result[str(point)] = group[["date", "q_gauge_l/s", "source"]].sort_values("date").reset_index(drop=True)
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
    for candidate in ["date", "datetime", "etime", "timestamp", "fecha", "time"]:
        if candidate in d.columns:
            date_col = candidate
            break
    if date_col:
        dates = pd.to_datetime(d[date_col], errors="coerce").dt.normalize()
    else:
        fallback_date = _date_from_summary_filename(path)
        if fallback_date is None or pd.isna(fallback_date):
            return []
        dates = pd.Series([fallback_date.normalize()] * len(d), index=d.index)
    tmp = pd.DataFrame({"date": dates, "q_gauge_l/s": q}).dropna()
    if tmp.empty:
        return []
    grouped = tmp.groupby("date", as_index=False)["q_gauge_l/s"].mean()
    return [(pd.to_datetime(r["date"]).normalize(), float(r["q_gauge_l/s"])) for _, r in grouped.iterrows()]


def load_gauges_daily(
    normalized_root: Path,
    instruments: Iterable[MeasuringInstrument],
    ranking_codes: List[str],
) -> Dict[str, pd.DataFrame]:
    """Load daily gauge series from normalized Aforix outputs.

    Loading order:
    1. database/normalized/Summary.csv
    2. database/normalized/<instrument>/Summary.csv
    3. legacy database/normalized/<instrument>/Summary/P*_Summary_*.csv
    """

    consolidated = _load_summary_table(normalized_root / "Summary.csv", ranking_codes)
    if consolidated:
        return consolidated

    per_instrument = []
    instruments_list = list(instruments)
    for instrument in instruments_list:
        table = _load_summary_table(
            normalized_root / instrument.subdir / "Summary.csv",
            ranking_codes,
            default_source=instrument.code,
        )
        if table:
            per_instrument.append(table)

    merged_per_instrument = _merge_gauge_dicts(per_instrument, ranking_codes)
    if merged_per_instrument:
        return merged_per_instrument

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
                if date is not None and q is not None:
                    rows.append({"point": point, "date": date.normalize(), "q_gauge_l/s": q, "source": code})
            else:
                for date, q in _load_wide_summary(file, instrument):
                    rows.append({"point": point, "date": date.normalize(), "q_gauge_l/s": q, "source": code})

    if not rows:
        return {}

    df = pd.DataFrame(rows)
    rank = {code.upper(): idx for idx, code in enumerate(ranking_codes)}
    df["rank"] = df["source"].map(lambda c: rank.get(str(c).upper(), 10_000))
    df = df.sort_values(["point", "date", "rank"]).drop_duplicates(["point", "date"], keep="first")
    df = df.drop(columns=["rank"])

    result: Dict[str, pd.DataFrame] = {}
    for point, group in df.groupby("point"):
        result[str(point)] = group[["date", "q_gauge_l/s", "source"]].sort_values("date").reset_index(drop=True)
    return result
