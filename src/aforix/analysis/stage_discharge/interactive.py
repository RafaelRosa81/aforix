from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import typer

from aforix.analysis.stage_discharge.config import load_stage_discharge_config
from aforix.analysis.stage_discharge.runner import run_stage_discharge


def run_interactive(config_path: Path) -> Path:
    cfg = load_stage_discharge_config(config_path)
    cfg = _copy_config(cfg)

    typer.echo("\nStage-discharge interactive analysis")
    typer.echo("Using main YAML as defaults. Press Enter to keep defaults.\n")

    _configure_instruments(cfg)
    _configure_points(cfg)
    _configure_depth_modes(cfg)
    _configure_outputs(cfg)

    return run_stage_discharge(config_path, override_config=cfg)


def _configure_instruments(cfg: dict[str, Any]) -> None:
    instruments_cfg = cfg.get("instruments", {})
    available = [name for name, inst in instruments_cfg.items() if inst.get("enabled", False)]
    default = _default_list(cfg, ["interactive_defaults", "instruments"], available)
    selected = _prompt_list("Instruments", available, default)

    for name, inst in instruments_cfg.items():
        inst["enabled"] = name in selected

    ranking_default = _default_list(cfg, ["interactive_defaults", "ranking"], selected)
    ranking = _prompt_list("Instrument ranking", selected, [r for r in ranking_default if r in selected])
    cfg.setdefault("instrument_selection", {})["ranking"] = ranking


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
    cfg.setdefault("selection", {})["points"] = "all" if value.lower() == "all" else _parse_list(value)


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
    selected = _parse_list(value)
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


def _copy_config(cfg: dict[str, Any]) -> dict[str, Any]:
    import copy

    return copy.deepcopy(cfg)
