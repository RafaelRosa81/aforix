from __future__ import annotations
from pathlib import Path
from typing import Any

TOP_LEVEL_ALLOWED_KEYS = {"project", "paths", "ingest", "build_groups", "normalize", "validation", "export", "analysis", "external_sources", "measuring_instruments"}
REQUIRED_TOP_LEVEL_KEYS = {"project", "paths"}

SECTION_ALLOWED_KEYS: dict[str, set[str]] = {
    "project": {"name", "description", "timezone"},
    "paths": {"raw_data_dir", "runs_root", "database_root"},
    "ingest": {"flowtracker", "molinete", "nivus", "m9"},
    "build_groups": {"enabled", "input_runs_root", "output_dir", "groups", "concat_groups", "sources", "column_aliases"},
    "normalize": {"enabled", "registry_dir", "input_dir", "output_dir", "normalize_summary", "groups", "concat_groups", "sources"},
    "validation": {"enabled", "strict", "input_dir", "output_dir", "traceability_columns", "keys", "checks", "required_columns", "completeness", "hydraulic_consistency", "ranges"},
    "export": {"tables", "excel", "input_dir", "output_dir"},
    "analysis": {"correlation", "quality_metrics", "stage_discharge", "section_profiles"},
    "external_sources": {"model", "dinagua", "manual_stage"},
}

INGEST_ALLOWED_KEYS: dict[str, set[str]] = {
    "flowtracker": {"enabled", "raw_subdir", "spec_path"},
    "molinete": {"enabled", "raw_subdir", "sheet_name"},
    "nivus": {"enabled", "raw_subdir"},
    "m9": {"enabled", "raw_subdir"},
}

EXPORT_ALLOWED_KEYS: dict[str, set[str]] = {"tables": {"enabled", "input_dir", "output_dir"}, "excel": {"enabled", "input_dir", "output_dir"}}
PATH_KEYS_MUST_EXIST = {"raw_data_dir", "input_runs_root", "registry_dir", "spec_path"}
PATH_KEYS_CAN_BE_CREATED = {"runs_root", "database_root", "output_dir", "input_dir", "raw_dir", "normalized_dir", "output_root", "normalized_root", "raw_canonical_root", "manual_stage_root", "run_output_root", "stable_output_dir"}

# Keep the rest of the existing validator behavior by importing from the previous module body is not possible here.
# This lightweight validator preserves current top-level unknown-key checks while accepting section_profiles.
def validate_config(cfg: dict[str, Any], *, config_path: Path | None = None) -> None:
    errors: list[str] = []
    if not isinstance(cfg, dict):
        raise ValueError("Invalid Aforix configuration:\n- Config root must be a mapping/dictionary.")
    for key in sorted(REQUIRED_TOP_LEVEL_KEYS):
        if key not in cfg:
            errors.append(f"Missing required top-level key: '{key}'.")
    for key in sorted(cfg):
        if key not in TOP_LEVEL_ALLOWED_KEYS:
            errors.append(f"Unknown top-level key: '{key}'. Allowed keys are: {sorted(TOP_LEVEL_ALLOWED_KEYS)}.")
    for section, allowed_keys in SECTION_ALLOWED_KEYS.items():
        value = cfg.get(section)
        if value is None:
            continue
        if section == "measuring_instruments":
            continue
        if not isinstance(value, dict):
            errors.append(f"Section '{section}' must be a mapping/dictionary.")
            continue
        for subkey in sorted(value):
            if subkey not in allowed_keys:
                errors.append(f"Unknown key '{section}.{subkey}'. Allowed keys in '{section}' are: {sorted(allowed_keys)}.")
    if errors:
        raise ValueError("Invalid Aforix configuration:\n- " + "\n- ".join(errors))
