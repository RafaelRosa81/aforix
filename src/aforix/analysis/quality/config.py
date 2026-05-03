from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aforix.config.loader import load_config


@dataclass(frozen=True)
class QualityPaths:
    normalized_root: Path
    raw_canonical_root: Path
    output_root: Path


@dataclass(frozen=True)
class NivusQualityConfig:
    normalized_points: Path
    raw_points: Path
    weight_column: str
    tq_candidates: tuple[str, ...]


@dataclass(frozen=True)
class QualityConfig:
    enabled: bool
    paths: QualityPaths
    nivus: NivusQualityConfig


def load_quality_config(config_path: str | Path) -> QualityConfig:
    config_path = Path(config_path).resolve()
    cfg = load_config(config_path)
    quality_cfg = _get_nested(cfg, ["analysis", "quality_metrics"], {}) or {}

    enabled = bool(quality_cfg.get("enabled", True))
    project_root = _project_root_from_config(config_path)

    input_dirs = quality_cfg.get("input_dirs", {}) or {}
    normalized_root = _resolve_path(
        input_dirs.get("normalized_root", quality_cfg.get("input_dir", "database/normalized")),
        project_root=project_root,
    )
    raw_canonical_root = _resolve_path(
        input_dirs.get("raw_canonical_root", "database/raw_canonical"),
        project_root=project_root,
    )
    output_root = _resolve_path(
        quality_cfg.get("output_root", quality_cfg.get("output_dir", "runs/analysis_quality_metrics")),
        project_root=project_root,
    )

    nivus_cfg = _get_nested(quality_cfg, ["instruments", "nivus"], {}) or {}
    tables = nivus_cfg.get("tables", {}) or {}
    columns = nivus_cfg.get("columns", {}) or {}

    normalized_points_rel = tables.get("normalized_points", "nivus/Points")
    raw_points_rel = tables.get("raw_points", "nivus/Points")

    tq_candidates = tuple(
        columns.get(
            "tq_candidates",
            ["tq [%]", "tq(%)", "tq", "atq [%]", "hq [%]"],
        )
    )

    return QualityConfig(
        enabled=enabled,
        paths=QualityPaths(
            normalized_root=normalized_root,
            raw_canonical_root=raw_canonical_root,
            output_root=output_root,
        ),
        nivus=NivusQualityConfig(
            normalized_points=normalized_root / normalized_points_rel,
            raw_points=raw_canonical_root / raw_points_rel,
            weight_column=str(columns.get("weight_column", "percent_q")),
            tq_candidates=tq_candidates,
        ),
    )


def _get_nested(cfg: dict[str, Any], keys: list[str], default: Any = None) -> Any:
    cur: Any = cfg
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def _project_root_from_config(config_path: Path) -> Path:
    resolved = config_path.resolve()
    if resolved.parent.name == "examples" and resolved.parent.parent.name == "configs":
        return resolved.parent.parent.parent
    if resolved.parent.name == "configs":
        return resolved.parent.parent
    if len(resolved.parents) >= 3:
        return resolved.parents[2]
    return Path.cwd().resolve()


def _resolve_path(value: str | Path, *, project_root: Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = project_root / path
    return path.resolve()
