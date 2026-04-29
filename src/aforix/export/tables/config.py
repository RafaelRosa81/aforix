from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_config(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {p}")
    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a YAML mapping: {p}")
    data["__config_path__"] = str(p.resolve())
    data["__repo_root__"] = str(_infer_repo_root(p))
    return data


def _infer_repo_root(config_path: Path) -> Path:
    config_path = config_path.resolve()
    for parent in [config_path.parent, *config_path.parents]:
        if (parent / "pyproject.toml").exists() or (parent / "src" / "aforix").exists():
            return parent
    return Path.cwd().resolve()


def resolve_project_path(config: dict[str, Any], value: str | Path | None, default: str | Path) -> Path:
    repo_root = Path(config.get("__repo_root__", Path.cwd())).resolve()
    raw = Path(value if value not in (None, "") else default)
    return raw if raw.is_absolute() else (repo_root / raw).resolve()


def get_database_root(config: dict[str, Any]) -> Path:
    project = config.get("project", {}) or {}
    return resolve_project_path(config, project.get("database_root"), "database")


def get_runs_root(config: dict[str, Any]) -> Path:
    project = config.get("project", {}) or {}
    return resolve_project_path(config, project.get("runs_root"), "runs")


def get_normalized_root(config: dict[str, Any]) -> Path:
    export_cfg = config.get("export_tables", {}) or {}
    if export_cfg.get("normalized_root"):
        return resolve_project_path(config, export_cfg.get("normalized_root"), "database/normalized")
    normalized_cfg = config.get("normalized_data", {}) or {}
    if normalized_cfg.get("root"):
        return resolve_project_path(config, normalized_cfg.get("root"), "database/normalized")
    return get_database_root(config) / "normalized"


def get_export_root(config: dict[str, Any]) -> Path:
    export_cfg = config.get("export_tables", {}) or {}
    return resolve_project_path(config, export_cfg.get("output_root") or export_cfg.get("output_dir"), get_runs_root(config) / "export_tables")


def enabled_instruments(config: dict[str, Any]) -> set[str] | None:
    instruments = config.get("instruments")
    if not isinstance(instruments, dict):
        return None
    enabled = {str(k).lower() for k, v in instruments.items() if not isinstance(v, dict) or v.get("enabled", True)}
    return enabled or None
