from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from aforix.config.loader import load_config


DEFAULT_STAGE_DISCHARGE_CONFIG: dict[str, Any] = {
    "enabled": True,
    "input_dirs": {
        "normalized_root": "database/normalized",
        "manual_stage_root": "database/external/normalized/manual_stage",
    },
    "output": {
        "run_output_root": "runs/analysis_stage_discharge",
        "stable_output_dir": "database/analysis/stage_discharge",
        "write_stable_copy": False,
    },
    "instruments": {
        "nivus": {"enabled": True, "code": "NV"},
        "flowtracker": {"enabled": True, "code": "FT"},
        "molinete": {"enabled": True, "code": "ML"},
        "m9": {"enabled": False, "code": "M9"},
    },
    "instrument_selection": {
        "ranking": ["nivus", "flowtracker", "molinete", "m9"],
    },
    "selection": {
        "points": "all",
        "instruments": "all",
        "start_date": None,
        "end_date": None,
        "depth_mode": "both",
        "instrument_stage_mode": "both",
    },
    "interactive_defaults": {
        "instruments": ["nivus", "flowtracker", "molinete"],
        "ranking": ["nivus", "flowtracker", "molinete"],
        "depth_mode": "both",
        "instrument_stage_mode": "both",
    },
    "plotting": {
        "enabled": True,
        "max_plots": 40,
    },
    "excel": {
        "enabled": True,
    },
}


def load_stage_discharge_config(config_path: Path) -> dict:
    """Load stage-discharge configuration and fill omitted module defaults.

    The stage-discharge block initially used a lighter schema than the current
    runner and interactive CLI. This adapter keeps existing user YAML files
    compatible while guaranteeing that both entry points receive the same
    canonical instrument, selection, plotting and Excel defaults.
    """
    root_config = load_config(config_path)
    configured = root_config.get("analysis", {}).get("stage_discharge", {}) or {}
    cfg = _deep_merge(DEFAULT_STAGE_DISCHARGE_CONFIG, configured)
    _apply_selection_instruments(cfg)
    return cfg


def _apply_selection_instruments(cfg: dict[str, Any]) -> None:
    """Honor legacy selection.instruments when it is not 'all'."""
    selected = cfg.get("selection", {}).get("instruments", "all")
    if selected is None or selected == "all":
        return
    if isinstance(selected, str):
        selected_names = {selected.strip().lower()}
    else:
        selected_names = {str(value).strip().lower() for value in selected}
    for name, instrument_cfg in cfg.get("instruments", {}).items():
        instrument_cfg["enabled"] = name in selected_names


def _deep_merge(defaults: dict[str, Any], configured: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(defaults)
    for key, value in configured.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged
