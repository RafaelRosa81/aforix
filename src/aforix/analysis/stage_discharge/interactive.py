from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import typer

from aforix.analysis.stage_discharge.config import load_stage_discharge_config
from aforix.analysis.stage_discharge.runner import run_stage_discharge


INSTRUMENT_CODES = {
    "NV": "nivus",
    "FT": "flowtracker",
    "ML": "molinete",
    "M9": "m9",
}
INSTRUMENT_NAMES_TO_CODES = {v: k for k, v in INSTRUMENT_CODES.items()}


def run_interactive(config_path: Path) -> Path:
    cfg = load_stage_discharge_config(config_path)
    cfg = _copy_config(cfg)

    typer.echo("\nStage-discharge interactive analysis")
    typer.echo("Using main YAML as defaults. Press Enter to keep defaults.\n")

    _configure_instruments(cfg)
    _configure_points(cfg)
    _configure_date_range(cfg)
    _configure_depth_modes(cfg)
    _configure_outputs(cfg)

    return run_stage_discharge(config_path, override_config=cfg)


def _configure_date_range(cfg: dict[str, Any]) -> None:
    selection = cfg.setdefault("selection", {})
    start_default = selection.get("start_date") or ""
    end_default = selection.get("end_date") or ""

    start = typer.prompt("Start date (YYYY-MM-DD or empty)", default=str(start_default)).strip()
    end = typer.prompt("End date (YYYY-MM-DD or empty)", default=str(end_default)).strip()

    selection["start_date"] = start or None
    selection["end_date"] = end or None


def _configure_instruments(cfg: dict[str, Any]) -> None:
    instruments_cfg = cfg.get("instruments", {})
    available_names = [name for name, inst in instruments_cfg.items() if inst.get("enabled", False)]
    available_codes = [_to_code(name) for name in available_names]

    default_names = _default_list(cfg, ["interactive_defaults", "instruments"], available_names)
    default_codes = [_to_code(name) for name in default_names if name in available_names]

    selected_codes = _prompt_list("Instruments", available_codes, default_codes)
    selected_names = [_to_name(code) for code in selected_codes]

    for name, inst in instruments_cfg.items():
        inst["enabled"] = name in selected_names

    ranking_default_names = _default_list(cfg, ["interactive_defaults", "ranking"], selected_names)
    ranking_default_codes = [_to_code(name) for name in ranking_default_names if name in selected_names]
    ranking_codes = _prompt_list("Instrument ranking", selected_codes, ranking_default_codes)
    cfg.setdefault("instrument_selection", {})["ranking"] = [_to_name(code) for code in ranking_codes]


def _configure_points(cfg: dict[str, Any]) -> None:
    normalized_root = Path(cfg.get("input_dirs", {}).get("normalized_root", "database/normalized"))
    summary_file = normalized_root / "Summary.csv"
    available_points: list[str] = []
    if summary_file.exists():
        df = pd.read_csv(summary_file, usecols=lambda c: c in {"station_id"})
        if "station_id" in df.columns:
            available_points = sorted(df["station_id"].dropna().astype(str).unique().tolist())

    default_points = cfg.get("selection", {}).get("points", "all")
    typer.echo(f"Available points detected: {len(available_points)}")
    prompt = "Points to analyze (all or comma-separated list)"
    value = typer.prompt(prompt, default=str(default_points))
    value = value.strip()
    cfg.setdefault("selection", {})["points"] = "all" if value.lower() == "all" else [_normalize_station_id(v) for v in _parse_list(value)]


def _configure_depth_modes(cfg: dict[str, Any]) -> None:
    defaults = cfg.get("interactive_defaults", {})
    selection = cfg.setdefault("selection", {})

    depth_default = selection.get("depth_mode", defaults.get("depth_mode", "both"))
    depth_mode = typer.prompt("Depth mode [manual/instrument/both]", default=str(depth_default)).strip().lower()
    if depth_mode not in {"manual", "instrument", "both"}:
        typer.echo("Invalid depth mode. Using 'both'.")
        depth_mode = "both"
    selection["depth_mode"] = depth_mode

    stage_default = selection.get("instrument_stage_mode", defaults.get("instrument_stage_mode", "both"))
    stage_mode = typer.prompt("Instrument stage mode [mean/max/both]", default=str(stage_default)).strip().lower()
    if stage_mode not in {"mean", "max", "both"}:
        typer.echo("Invalid instrument stage mode. Using 'both'.")
        stage_mode = "both"
    selection["instrument_stage_mode"] = stage_mode


def _configure_outputs(cfg: dict[str, Any]) -> None:
    plotting = cfg.setdefault("plotting", {})
    default_enabled = plotting.get("enabled", True)
    plotting["enabled"] = typer.confirm("Generate plots?", default=bool(default_enabled))
    if plotting["enabled"]:
        max_default = plotting.get("max_plots", 40)
        max_value = typer.prompt("Maximum number of plots", default=str(max_default)).strip()
        plotting["max_plots"] = None if max_value.lower() in {"none", "all"} else int(max_value)

    excel = cfg.setdefault("excel", {})
    excel["enabled"] = typer.confirm("Generate Excel report?", default=bool(excel.get("enabled", True)))


def _prompt_list(label: str, available: list[str], default: list[str]) -> list[str]:
    typer.echo(f"{label} available: {', '.join(available) if available else '(none)'}")
    value = typer.prompt(f"{label} to use", default=", ".join(default))
    selected = [v.upper() for v in _parse_list(value)]
    valid = [item for item in selected if item in available]
    return valid or default


def _parse_list(value: str) -> list[str]:
    return [v.strip() for v in str(value).split(",") if v.strip()]


def _default_list(cfg: dict[str, Any], path: list[str], fallback: list[str]) -> list[str]:
    cur: Any = cfg
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return fallback
        cur = cur[key]
    return cur if isinstance(cur, list) else fallback


def _to_code(name: str) -> str:
    return INSTRUMENT_NAMES_TO_CODES.get(str(name).lower(), str(name).upper())


def _to_name(code: str) -> str:
    return INSTRUMENT_CODES.get(str(code).upper(), str(code).lower())


def _normalize_station_id(value: str) -> str:
    s = str(value).strip().upper()
    if s.startswith("P"):
        digits = "".join(ch for ch in s[1:] if ch.isdigit())
    else:
        digits = "".join(ch for ch in s if ch.isdigit())
    return f"P{int(digits)}" if digits else s


def _copy_config(cfg: dict[str, Any]) -> dict[str, Any]:
    import copy

    return copy.deepcopy(cfg)
