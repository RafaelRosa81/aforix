from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import typer

from aforix.analysis.section_profiles.inputs import load_points_by_instrument
from aforix.analysis.section_profiles.filters import filter_date_range, filter_instruments, filter_points


def apply_interactive_overrides(cfg: dict[str, Any]) -> dict[str, Any]:
    normalized_root = Path(cfg.get("input_dirs", {}).get("normalized_root", "database/normalized"))
    instruments_cfg = cfg.get("instruments", {})
    df = load_points_by_instrument(normalized_root, instruments_cfg)

    if df.empty:
        typer.echo("No normalized Points data found for section profiles.")
        return cfg

    code_to_name = _instrument_code_map(instruments_cfg)
    available_names = sorted(str(v) for v in df.get("instrument", pd.Series(dtype=str)).dropna().unique())
    available_codes = [_instrument_name_to_code(name, instruments_cfg) for name in available_names]
    available_points = sorted(str(v) for v in df.get("station_id", pd.Series(dtype=str)).dropna().unique(), key=_point_sort_key)
    available_dates = pd.to_datetime(df.get("measurement_date", pd.Series(dtype=str)), errors="coerce").dropna()

    typer.echo("Interactive section profiles mode")
    typer.echo(f"Available instruments: {', '.join(available_codes) or '(none)'}")
    instrument_input = typer.prompt("Select instrument codes, comma-separated, empty = all", default="", show_default=False)
    selected_codes = _parse_csv(instrument_input)
    selected_instruments = [_code_or_name_to_instrument(v, code_to_name) for v in selected_codes] if selected_codes else None

    preview = df.copy()
    if selected_instruments:
        preview = filter_instruments(preview, set(selected_instruments))

    typer.echo(f"Available points: {', '.join(available_points) or '(none)'}")
    point_input = typer.prompt("Select points, comma-separated, empty = all", default="", show_default=False)
    selected_points = _parse_csv(point_input)
    if selected_points:
        preview = filter_points(preview, set(_normalize_point(p) for p in selected_points))

    if not available_dates.empty:
        typer.echo(f"Available date range: {available_dates.min().date()} to {available_dates.max().date()}")
    start_date = typer.prompt("Start date YYYY-MM-DD, empty = no start filter", default="", show_default=False) or None
    end_date = typer.prompt("End date YYYY-MM-DD, empty = no end filter", default="", show_default=False) or None
    preview = filter_date_range(preview, start_date, end_date)

    allowed = cfg.get("allowed", {}) or {}
    allowed_x = allowed.get("x_columns") or []
    allowed_y = allowed.get("y_columns") or []
    available_cols = set(preview.columns)
    x_options = [c for c in allowed_x if c in available_cols] or sorted(preview.columns)
    y_options = [c for c in allowed_y if c in available_cols] or sorted(preview.columns)

    typer.echo(f"Available X columns: {', '.join(x_options)}")
    default_x = cfg.get("defaults", {}).get("x_axis", x_options[0] if x_options else "distance_m")
    x_axis = typer.prompt("X axis", default=default_x)

    typer.echo(f"Available Y columns: {', '.join(y_options)}")
    default_y = cfg.get("defaults", {}).get("y_axis", y_options[0] if y_options else "depth_m")
    y_axis = typer.prompt("Y axis", default=default_y)

    chart_types = allowed.get("chart_types") or ["scatter", "bar"]
    typer.echo(f"Available chart types: {', '.join(chart_types)}")
    chart_type = typer.prompt("Chart type", default=cfg.get("defaults", {}).get("chart_type", "scatter"))

    selection = cfg.setdefault("selection", {})
    selection["instruments"] = selected_instruments or "all"
    selection["points"] = [_normalize_point(p) for p in selected_points] if selected_points else "all"
    selection["start_date"] = start_date
    selection["end_date"] = end_date

    defaults = cfg.setdefault("defaults", {})
    defaults["x_axis"] = x_axis
    defaults["y_axis"] = y_axis
    defaults["chart_type"] = chart_type
    return cfg


def _instrument_code_map(instruments_cfg: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for name, item in instruments_cfg.items():
        code = str(item.get("code", name)).upper()
        out[code] = name
        out[name.lower()] = name
    return out


def _instrument_name_to_code(name: str, instruments_cfg: dict[str, Any]) -> str:
    cfg = instruments_cfg.get(name, {})
    return str(cfg.get("code", name)).upper()


def _code_or_name_to_instrument(value: str, code_to_name: dict[str, str]) -> str:
    key = str(value).strip()
    return code_to_name.get(key.upper()) or code_to_name.get(key.lower()) or key.lower()


def _parse_csv(value: str | None) -> list[str] | None:
    if not value:
        return None
    parsed = [v.strip() for v in value.split(",") if v.strip()]
    return parsed or None


def _normalize_point(value: str) -> str:
    s = str(value).strip().upper()
    if s.startswith("P"):
        digits = "".join(ch for ch in s[1:] if ch.isdigit())
    else:
        digits = "".join(ch for ch in s if ch.isdigit())
    return f"P{int(digits)}" if digits else s


def _point_sort_key(value: str):
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return (int(digits) if digits else 10**9, str(value))
