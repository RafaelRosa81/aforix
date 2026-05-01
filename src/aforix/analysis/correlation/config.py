from __future__ import annotations

from pathlib import Path
from typing import Any

from aforix.config.loader import load_config
from aforix.analysis.correlation.types import CorrelationPaths


def load_correlation_config(config_path: Path) -> dict[str, Any]:
    """Load Aforix config and return the full dictionary."""

    return load_config(config_path)


def _get_nested(cfg: dict[str, Any], keys: list[str], default: Any = None) -> Any:
    cur: Any = cfg
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def resolve_correlation_paths(config_path: Path) -> CorrelationPaths:
    """Resolve correlation input/output paths with backward-compatible fallbacks."""

    cfg = load_config(config_path)
    root = config_path.parent.parent if config_path.parent.name == "examples" else Path.cwd()

    normalized_root = Path(
        _get_nested(cfg, ["database", "normalized_dir"], "database/normalized")
    )
    model_dir = Path(
        _get_nested(
            cfg,
            ["external_sources", "model", "normalized_dir"],
            cfg.get("output_model_data_path_dir", "database/external/normalized/model"),
        )
    )
    stations_dir = Path(
        _get_nested(
            cfg,
            ["external_sources", "dinagua", "normalized_dir"],
            cfg.get("output_estacionDINAGUA_data_path_dir", "database/external/normalized/dinagua"),
        )
    )
    output_root = Path(
        _get_nested(
            cfg,
            ["analysis", "correlation", "output_root"],
            cfg.get("correlation_path_dir", "runs/analysis_correlation"),
        )
    )

    def abs_path(p: Path) -> Path:
        return p if p.is_absolute() else (root / p).resolve()

    return CorrelationPaths(
        normalized_root=abs_path(normalized_root),
        external_model_dir=abs_path(model_dir),
        external_stations_dir=abs_path(stations_dir),
        output_root=abs_path(output_root),
    )


def get_external_source_config(cfg: dict[str, Any], source_name: str) -> dict[str, Any]:
    return _get_nested(cfg, ["external_sources", source_name], {}) or {}


def get_correlation_section(cfg: dict[str, Any], workflow_name: str) -> dict[str, Any]:
    return _get_nested(cfg, ["analysis", "correlation", workflow_name], {}) or {}
