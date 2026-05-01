from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd

from .config import get_export_root, get_normalized_root, enabled_instruments
from .writers import write_csv, write_metadata, write_xlsx

ID_COLUMNS = {
    "instrument", "station_id", "station_name", "measurement_date", "measurement_time",
    "date", "Date", "time", "Time", "datetime", "timestamp", "group_key", "period",
}
METADATA_COLUMNS = {
    "source_csv", "source_run_dir", "source_file", "source_path", "run_dir", "run_timestamp",
    "raw_file", "input_file", "config_used", "notes",
}
DATE_CANDIDATES = ["measurement_date", "Date", "date", "datetime", "timestamp"]
POINT_CANDIDATES = ["station_id", "Point", "point", "station", "site_id"]


@dataclass(frozen=True)
class ExportRequest:
    table: str
    instrument: str = "all"
    points: tuple[str, ...] = ()
    parameters: tuple[str, ...] = ()
    early_date: str | None = None
    late_date: str | None = None
    grouping: str = "none"
    fmt: str = "xlsx"
    pivot: bool | None = None
    include_metadata_columns: bool = False
    aggregation: str = "mean"


@dataclass(frozen=True)
class ExportResult:
    output_file: Path
    metadata_file: Path | None
    row_count: int
    source_files: tuple[Path, ...]


def discover_normalized_tables(config: dict) -> list[str]:
    root = get_normalized_root(config)
    if not root.exists():
        return []
    return sorted([p.name for p in root.iterdir() if p.is_dir() and list(p.glob("*.csv"))], key=str.lower)


def table_dir(config: dict, table: str) -> Path:
    root = get_normalized_root(config)
    candidates = [p for p in root.iterdir() if p.is_dir() and p.name.lower() == table.lower()] if root.exists() else []
    if not candidates:
        raise FileNotFoundError(f"Normalized table not found: {root / table}")
    return candidates[0]


def load_normalized_table(config: dict, table: str) -> tuple[pd.DataFrame, list[Path]]:
    tdir = table_dir(config, table)
    files = sorted(tdir.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files found in normalized table directory: {tdir}")
    frames = []
    for f in files:
        frames.append(pd.read_csv(f))
    df = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
    return df, files


def discover_instruments(df: pd.DataFrame, config: dict | None = None) -> list[str]:
    if "instrument" not in df.columns:
        return []
    values = sorted({str(x).strip() for x in df["instrument"].dropna().unique() if str(x).strip()}, key=str.lower)
    if config is not None:
        enabled = enabled_instruments(config)
        if enabled is not None:
            values = [v for v in values if v.lower() in enabled]
    return values


def get_point_column(df: pd.DataFrame) -> str | None:
    for col in POINT_CANDIDATES:
        if col in df.columns:
            return col
    return None


def get_date_column(df: pd.DataFrame) -> str | None:
    for col in DATE_CANDIDATES:
        if col in df.columns:
            return col
    return None


def normalize_point_token(token: str) -> str:
    s = str(token).strip()
    if not s:
        return s
    if s.upper().startswith("P"):
        return "P" + s[1:]
    if s.isdigit():
        return "P" + s
    return s


def available_points(df: pd.DataFrame) -> list[str]:
    col = get_point_column(df)
    if not col:
        return []
    vals = [normalize_point_token(v) for v in df[col].dropna().astype(str).unique()]
    def key(x: str):
        return (0, int(x[1:])) if x.upper().startswith("P") and x[1:].isdigit() else (1, x)
    return sorted(set(vals), key=key)


def parameter_columns(df: pd.DataFrame, include_metadata: bool = False) -> list[str]:
    excluded = set(ID_COLUMNS)
    if not include_metadata:
        excluded |= METADATA_COLUMNS
    candidates = [c for c in df.columns if c not in excluded]
    numeric = [c for c in candidates if pd.api.types.is_numeric_dtype(df[c])]
    non_numeric = [c for c in candidates if c not in numeric]
    return numeric + non_numeric


def _clean_date_series(s: pd.Series) -> pd.Series:
    as_str = s.astype(str).str.strip()
    extracted = as_str.str.extract(r"(\d{8})")[0]
    missing = extracted.isna()
    if missing.any():
        parsed = pd.to_datetime(as_str[missing], errors="coerce")
        extracted.loc[missing] = parsed.dt.strftime("%Y%m%d")
    return extracted


def _apply_date_filter(df: pd.DataFrame, early: str | None, late: str | None) -> pd.DataFrame:
    date_col = get_date_column(df)
    if date_col is None:
        if early or late:
            raise KeyError("No date column found. Expected one of: " + ", ".join(DATE_CANDIDATES))
        return df
    out = df.copy()
    out["__date_str"] = _clean_date_series(out[date_col])
    out = out.dropna(subset=["__date_str"])
    if early:
        out = out[out["__date_str"] >= str(early)]
    if late:
        out = out[out["__date_str"] <= str(late)]
    return out


def _date_bounds(df: pd.DataFrame, early: str | None, late: str | None) -> tuple[str | None, str | None]:
    if early and late:
        return early, late
    if "__date_str" not in df.columns or df.empty:
        return early, late
    return early or str(df["__date_str"].min()), late or str(df["__date_str"].max())


def _periods_for_range(early: str | None, late: str | None, grouping: str) -> list[str]:
    if not early or not late:
        return []
    start = pd.to_datetime(early, format="%Y%m%d", errors="raise")
    end = pd.to_datetime(late, format="%Y%m%d", errors="raise")
    if grouping == "monthly":
        return pd.period_range(start=start, end=end, freq="M").astype(str).str.replace("-", "").tolist()
    if grouping == "daily":
        return pd.date_range(start=start, end=end, freq="D").strftime("%Y%m%d").tolist()
    return []


def _aggregate(values: pd.core.groupby.generic.DataFrameGroupBy, method: str) -> pd.DataFrame:
    method = (method or "mean").lower()
    if method == "mean":
        return values.mean(numeric_only=True)
    if method == "sum":
        return values.sum(numeric_only=True)
    if method == "median":
        return values.median(numeric_only=True)
    if method == "min":
        return values.min(numeric_only=True)
    if method == "max":
        return values.max(numeric_only=True)
    if method == "first":
        return values.first()
    raise ValueError(f"Unsupported aggregation: {method}")


def _selected_instruments_for_rows(work: pd.DataFrame, requested_instrument: str | None) -> list[str]:
    if "instrument" not in work.columns:
        return []
    vals = sorted({str(v).strip() for v in work["instrument"].dropna().unique() if str(v).strip()}, key=str.lower)
    if requested_instrument and requested_instrument.lower() != "all":
        return [requested_instrument]
    return vals


def _make_complete_index(work: pd.DataFrame, row_keys: list[str], requested_points: Sequence[str], requested_instrument: str | None) -> pd.Index | pd.MultiIndex | None:
    if not requested_points:
        return None
    points = [normalize_point_token(p) for p in requested_points]
    points = list(dict.fromkeys(points))
    if row_keys == ["station_id"]:
        return pd.Index(points, name="station_id")
    if row_keys == ["instrument", "station_id"]:
        instruments = _selected_instruments_for_rows(work, requested_instrument)
        return pd.MultiIndex.from_product([instruments, points], names=["instrument", "station_id"])
    return None


def _build_pivot(
    df: pd.DataFrame,
    parameters: Sequence[str],
    grouping: str,
    early: str | None,
    late: str | None,
    aggregation: str,
    requested_points: Sequence[str] = (),
    requested_instrument: str | None = None,
) -> pd.DataFrame:
    if grouping not in {"monthly", "daily"}:
        raise ValueError("Pivot export requires grouping=monthly or grouping=daily.")
    date_col = get_date_column(df)
    point_col = get_point_column(df)
    if not date_col:
        raise KeyError("Pivot export requires a date column.")
    if not point_col:
        raise KeyError("Pivot export requires a point/station column.")

    work = df.copy()
    if "__date_str" not in work.columns:
        work["__date_str"] = _clean_date_series(work[date_col])
    work["station_id"] = work[point_col].map(normalize_point_token)
    if grouping == "monthly":
        work["period"] = work["__date_str"].str[:6]
    else:
        work["period"] = work["__date_str"]

    row_keys = ["station_id"]
    if "instrument" in work.columns and (requested_instrument or work["instrument"].nunique(dropna=True) > 1):
        row_keys = ["instrument", "station_id"]

    numeric_params = [p for p in parameters if p in work.columns and pd.api.types.is_numeric_dtype(work[p])]
    if not numeric_params:
        raise ValueError("No numeric parameter columns selected for grouped/pivot export.")

    grouped = _aggregate(work.groupby(row_keys + ["period"], dropna=False)[numeric_params], aggregation).reset_index()
    pivot = grouped.pivot(index=row_keys, columns="period", values=numeric_params)
    pivot = pivot.swaplevel(0, 1, axis=1)

    periods = _periods_for_range(early, late, grouping)
    if periods:
        desired_columns = pd.MultiIndex.from_product([periods, numeric_params], names=["period", None])
        pivot = pivot.reindex(columns=desired_columns)
    else:
        pivot = pivot.sort_index(axis=1, level=[0, 1])

    complete_index = _make_complete_index(work, row_keys, requested_points, requested_instrument)
    if complete_index is not None:
        pivot = pivot.reindex(complete_index)
    return pivot.reset_index()


def _build_flat(df: pd.DataFrame, parameters: Sequence[str]) -> pd.DataFrame:
    base_cols = []
    for col in ["instrument", get_point_column(df), "station_name", get_date_column(df), "measurement_time"]:
        if col and col in df.columns and col not in base_cols:
            base_cols.append(col)
    cols = base_cols + [p for p in parameters if p in df.columns and p not in base_cols]
    return df[cols].copy()


def _slug(value: str | None) -> str:
    text = str(value or "").strip().lower()
    keep = []
    for ch in text:
        if ch.isalnum():
            keep.append(ch)
        elif ch in {"_", "-"}:
            keep.append("_")
        elif ch.isspace():
            keep.append("_")
    slug = "".join(keep).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "export"


def _table_short_name(table: str) -> str:
    mapping = {
        "summary": "summary",
        "points": "points",
        "sections": "sections",
        "gates": "gates",
    }
    return mapping.get(str(table).strip().lower(), _slug(table))


def _grouping_short_name(grouping: str, is_pivot: bool) -> str:
    grouping = (grouping or "none").lower()
    if grouping == "monthly":
        return "monthly"
    if grouping == "daily":
        return "daily"
    return "flat" if not is_pivot else "pivot"


def _instrument_short_name(instrument: str | None) -> str:
    tag = (instrument or "all").strip().lower()
    if tag in {"", "all"}:
        return "allinst"
    mapping = {
        "flowtracker": "ft",
        "molinete": "mol",
        "nivus": "nivus",
        "m9": "m9",
    }
    return mapping.get(tag, _slug(tag))


def _aggregation_short_name(aggregation: str | None) -> str:
    mapping = {
        "mean": "avg",
        "sum": "sum",
        "median": "med",
        "min": "min",
        "max": "max",
        "first": "first",
    }
    return mapping.get((aggregation or "mean").lower(), _slug(aggregation))


def _date_range_short_name(early: str | None, late: str | None) -> str:
    if early and late:
        return f"{early}-{late}"
    if early:
        return f"from_{early}"
    if late:
        return f"to_{late}"
    return "all_dates"


def _build_output_stem(
    request: ExportRequest,
    grouping: str,
    is_pivot: bool,
    early: str | None,
    late: str | None,
) -> str:
    """Build compact, descriptive export file stems.

    Examples:
    - summary_20250801-20260131_monthly_avg_allinst
    - summary_20250801-20260131_monthly_avg_ft
    - points_20251201-20251231_daily_sum_nivus
    - summary_all_dates_flat_allinst
    """
    table = _table_short_name(request.table)
    date_range = _date_range_short_name(early, late)
    period = _grouping_short_name(grouping, is_pivot)
    instrument = _instrument_short_name(request.instrument)
    if grouping in {"monthly", "daily"}:
        aggregation = _aggregation_short_name(request.aggregation)
        return f"{table}_{date_range}_{period}_{aggregation}_{instrument}"
    return f"{table}_{date_range}_{period}_{instrument}"


def run_export_tables(config: dict, request: ExportRequest) -> ExportResult:
    df, source_files = load_normalized_table(config, request.table)

    if request.instrument and request.instrument.lower() != "all":
        if "instrument" not in df.columns:
            raise KeyError("Cannot filter by instrument because column 'instrument' is missing.")
        df = df[df["instrument"].astype(str).str.lower() == request.instrument.lower()]

    point_col = get_point_column(df)
    if request.points:
        if not point_col:
            raise KeyError("Cannot filter by points because no station/point column was found.")
        wanted = {normalize_point_token(p) for p in request.points}
        df = df[df[point_col].map(normalize_point_token).isin(wanted)]

    df = _apply_date_filter(df, request.early_date, request.late_date)
    early_eff, late_eff = _date_bounds(df, request.early_date, request.late_date)

    params = list(request.parameters) if request.parameters else parameter_columns(df, request.include_metadata_columns)
    missing = [p for p in params if p not in df.columns]
    if missing:
        raise KeyError("Selected parameter columns not found: " + ", ".join(missing))

    grouping = (request.grouping or "none").lower()
    pivot = request.pivot if request.pivot is not None else grouping in {"monthly", "daily"}
    if pivot:
        out_df = _build_pivot(df, params, grouping, early_eff, late_eff, request.aggregation, request.points, request.instrument)
    elif grouping in {"monthly", "daily"}:
        out_df = _build_pivot(df, params, grouping, early_eff, late_eff, request.aggregation, request.points, request.instrument)
    else:
        out_df = _build_flat(df, params)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_root = get_export_root(config) / ts
    export_root.mkdir(parents=True, exist_ok=True)
    fmt = request.fmt.lower()
    if fmt not in {"xlsx", "csv"}:
        raise ValueError("Output format must be xlsx or csv.")
    stem = _build_output_stem(request, grouping, bool(pivot or grouping in {"monthly", "daily"}), early_eff, late_eff)
    output_file = export_root / f"{stem}.{fmt}"
    metadata_file = export_root / f"{stem}_metadata.txt"

    metadata = {
        "table": request.table,
        "instrument": request.instrument,
        "points": list(request.points),
        "parameters": params,
        "early_date_requested": request.early_date,
        "late_date_requested": request.late_date,
        "early_date_effective": early_eff,
        "late_date_effective": late_eff,
        "grouping": grouping,
        "pivot": bool(pivot or grouping in {"monthly", "daily"}),
        "aggregation": request.aggregation,
        "output_stem": stem,
        "filename_pattern": "{table}_{date_range}_{period}_{aggregation}_{instrument}.{fmt}" if grouping in {"monthly", "daily"} else "{table}_{date_range}_{shape}_{instrument}.{fmt}",
        "column_order": "period_major" if grouping in {"monthly", "daily"} else "flat",
        "point_selection_rule": "numeric point tokens are treated as station codes; use idx:N or [N] to force index selection",
        "row_count": int(len(out_df)),
        "source_files": [str(p) for p in source_files],
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }

    if fmt == "xlsx":
        write_xlsx(out_df, output_file, metadata)
    else:
        write_csv(out_df, output_file)
    write_metadata(metadata_file, metadata)
    return ExportResult(output_file=output_file, metadata_file=metadata_file, row_count=len(out_df), source_files=tuple(source_files))
