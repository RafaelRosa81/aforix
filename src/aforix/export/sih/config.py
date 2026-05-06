from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_sih_config(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"SIH config file not found: {p}")

    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        raise ValueError(f"SIH config must contain a YAML mapping: {p}")

    if "sih" not in data or not isinstance(data["sih"], dict):
        raise ValueError("SIH config must contain a top-level 'sih' mapping.")

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


def sih_section(config: dict[str, Any]) -> dict[str, Any]:
    section = config.get("sih", {})
    if not isinstance(section, dict):
        raise ValueError("SIH config section must be a mapping.")
    return section


def get_output_dir(config: dict[str, Any]) -> Path:
    sih = sih_section(config)
    output = sih.get("output", {}) or {}
    return resolve_project_path(config, output.get("output_dir"), "outputs/sih")


def get_normalized_input_dir(config: dict[str, Any]) -> Path:
    sih = sih_section(config)
    inputs = sih.get("inputs", {}) or {}
    return resolve_project_path(config, inputs.get("normalized_input_dir"), "database/normalized")


def get_raw_canonical_input_dir(config: dict[str, Any]) -> Path:
    sih = sih_section(config)
    inputs = sih.get("inputs", {}) or {}
    return resolve_project_path(config, inputs.get("raw_canonical_input_dir"), "database/raw_canonical")


def get_workbook_path(config: dict[str, Any]) -> Path:
    sih = sih_section(config)
    workbook = sih.get("workbook", {}) or {}
    return resolve_project_path(config, workbook.get("path"), "configs/sih/sih_mapping.xlsx")


def get_default_selection_file(config: dict[str, Any]) -> Path:
    sih = sih_section(config)
    selection = sih.get("selection", {}) or {}
    batch_file = selection.get("batch_file", {}) or {}
    return resolve_project_path(config, batch_file.get("path"), "configs/sih/selection_template.csv")
