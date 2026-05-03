from __future__ import annotations

from pathlib import Path
from typing import Any


TOP_LEVEL_ALLOWED_KEYS = {
    "project",
    "paths",
    "ingest",
    "build_groups",
    "normalize",
    "validation",
    "export",
    "analysis",
    "external_sources",
    "measuring_instruments",
}

REQUIRED_TOP_LEVEL_KEYS = {"project", "paths"}

SECTION_ALLOWED_KEYS: dict[str, set[str]] = {
    "project": {"name", "description", "timezone"},
    "paths": {"raw_data_dir", "runs_root", "database_root"},
    "ingest": {"flowtracker", "molinete", "nivus", "m9"},
    "build_groups": {
        "enabled",
        "input_runs_root",
        "output_dir",
        "groups",
        "concat_groups",
        "sources",
        "column_aliases",
    },
    "normalize": {
        "enabled",
        "registry_dir",
        "input_dir",
        "output_dir",
        "normalize_summary",
        "groups",
        "concat_groups",
        "sources",
    },
    "validation": {
        "enabled",
        "strict",
        "input_dir",
        "output_dir",
        "traceability_columns",
        "keys",
        "checks",
        "required_columns",
        "completeness",
        "hydraulic_consistency",
        "ranges",
    },
    "export": {"tables", "excel", "input_dir", "output_dir"},
    "analysis": {"correlation", "quality_metrics"},
    "external_sources": {"model", "dinagua"},
}

INGEST_ALLOWED_KEYS: dict[str, set[str]] = {
    "flowtracker": {"enabled", "raw_subdir", "spec_path"},
    "molinete": {"enabled", "raw_subdir", "sheet_name"},
    "nivus": {"enabled", "raw_subdir"},
    "m9": {"enabled", "raw_subdir"},
}

EXPORT_ALLOWED_KEYS: dict[str, set[str]] = {
    "tables": {"enabled", "input_dir", "output_dir"},
    "excel": {"enabled", "input_dir", "output_dir"},
}

PATH_KEYS_MUST_EXIST = {"raw_data_dir", "input_runs_root", "registry_dir", "spec_path"}
PATH_KEYS_CAN_BE_CREATED = {
    "runs_root",
    "database_root",
    "output_dir",
    "input_dir",
    "raw_dir",
    "normalized_dir",
    "output_root",
    "normalized_root",
    "raw_canonical_root",
}


def validate_config(cfg: dict[str, Any], *, config_path: Path | None = None) -> None:
    errors: list[str] = []

    errors.extend(_validate_root_type(cfg))
    if errors:
        raise ValueError(_format_errors(errors))

    errors.extend(_validate_required_top_level_keys(cfg))
    errors.extend(_validate_unknown_top_level_keys(cfg))
    errors.extend(_validate_sections_are_dicts(cfg))
    errors.extend(_validate_unknown_section_keys(cfg))
    errors.extend(_validate_ingest_sections(cfg))
    errors.extend(_validate_export_sections(cfg))
    errors.extend(_validate_project_section(cfg))
    errors.extend(_validate_paths_section(cfg))
    errors.extend(_validate_build_groups_section(cfg))
    errors.extend(_validate_normalize_section(cfg))
    errors.extend(_validate_validation_section(cfg))
    errors.extend(_validate_correlation_section(cfg))
    errors.extend(_validate_quality_metrics_section(cfg))
    errors.extend(_validate_external_sources_section(cfg))
    errors.extend(_validate_measuring_instruments_section(cfg))
    errors.extend(_validate_path_values(cfg, config_path=config_path))

    if errors:
        raise ValueError(_format_errors(errors))


def _validate_root_type(cfg: Any) -> list[str]:
    return [] if isinstance(cfg, dict) else ["Config root must be a mapping/dictionary."]


def _validate_required_top_level_keys(cfg: dict[str, Any]) -> list[str]:
    return [f"Missing required top-level key: '{key}'." for key in sorted(REQUIRED_TOP_LEVEL_KEYS) if key not in cfg]


def _validate_unknown_top_level_keys(cfg: dict[str, Any]) -> list[str]:
    return [
        f"Unknown top-level key: '{key}'. Allowed keys are: {sorted(TOP_LEVEL_ALLOWED_KEYS)}."
        for key in sorted(cfg)
        if key not in TOP_LEVEL_ALLOWED_KEYS
    ]


def _validate_sections_are_dicts(cfg: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key, value in cfg.items():
        if key == "measuring_instruments":
            if not isinstance(value, list):
                errors.append("Section 'measuring_instruments' must be a list.")
            continue
        if key in TOP_LEVEL_ALLOWED_KEYS and not isinstance(value, dict):
            errors.append(f"Section '{key}' must be a mapping/dictionary.")
    return errors


def _validate_unknown_section_keys(cfg: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for section, allowed_keys in SECTION_ALLOWED_KEYS.items():
        value = cfg.get(section)
        if not isinstance(value, dict):
            continue
        for key in sorted(value):
            if key not in allowed_keys:
                errors.append(
                    f"Unknown key '{section}.{key}'. Allowed keys in '{section}' are: {sorted(allowed_keys)}."
                )
    return errors


def _validate_ingest_sections(cfg: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    ingest = cfg.get("ingest")
    if not isinstance(ingest, dict):
        return errors

    for instrument, settings in ingest.items():
        if instrument not in INGEST_ALLOWED_KEYS:
            errors.append(
                f"Unknown ingest instrument: 'ingest.{instrument}'. Allowed instruments are: {sorted(INGEST_ALLOWED_KEYS)}."
            )
            continue
        if not isinstance(settings, dict):
            errors.append(f"Section 'ingest.{instrument}' must be a mapping/dictionary.")
            continue
        allowed = INGEST_ALLOWED_KEYS[instrument]
        for key in sorted(settings):
            if key not in allowed:
                errors.append(f"Unknown key 'ingest.{instrument}.{key}'. Allowed keys are: {sorted(allowed)}.")
        errors.extend(_validate_optional_bool(settings, key="enabled", full_key=f"ingest.{instrument}.enabled"))
        errors.extend(_validate_optional_non_empty_string(settings, key="raw_subdir", full_key=f"ingest.{instrument}.raw_subdir"))
        if instrument == "flowtracker":
            errors.extend(_validate_required_non_empty_string(settings, key="spec_path", full_key="ingest.flowtracker.spec_path"))
        if instrument == "molinete":
            errors.extend(_validate_optional_non_empty_string(settings, key="sheet_name", full_key="ingest.molinete.sheet_name"))
    return errors


def _validate_export_sections(cfg: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    export = cfg.get("export")
    if not isinstance(export, dict):
        return errors

    for export_name, settings in export.items():
        if export_name not in EXPORT_ALLOWED_KEYS:
            errors.append(f"Unknown export section: 'export.{export_name}'. Allowed sections are: {sorted(EXPORT_ALLOWED_KEYS)}.")
            continue
        if not isinstance(settings, dict):
            errors.append(f"Section 'export.{export_name}' must be a mapping/dictionary.")
            continue
        allowed = EXPORT_ALLOWED_KEYS[export_name]
        for key in sorted(settings):
            if key not in allowed:
                errors.append(f"Unknown key 'export.{export_name}.{key}'. Allowed keys are: {sorted(allowed)}.")
        errors.extend(_validate_optional_bool(settings, key="enabled", full_key=f"export.{export_name}.enabled"))
    return errors


def _validate_project_section(cfg: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    project = cfg.get("project")
    if not isinstance(project, dict):
        return errors
    errors.extend(_validate_required_non_empty_string(project, key="name", full_key="project.name"))
    errors.extend(_validate_optional_non_empty_string(project, key="description", full_key="project.description"))
    errors.extend(_validate_optional_non_empty_string(project, key="timezone", full_key="project.timezone"))
    return errors


def _validate_paths_section(cfg: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    paths = cfg.get("paths")
    if not isinstance(paths, dict):
        return errors
    for key in ("raw_data_dir", "runs_root", "database_root"):
        errors.extend(_validate_required_non_empty_string(paths, key=key, full_key=f"paths.{key}"))
    return errors


def _validate_build_groups_section(cfg: dict[str, Any]) -> list[str]:
    section = cfg.get("build_groups")
    if not isinstance(section, dict):
        return []
    return _validate_pipeline_section(
        section,
        section_name="build_groups",
        source_allowed_values=set(INGEST_ALLOWED_KEYS),
        require_sources_non_empty=True,
    )


def _validate_normalize_section(cfg: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    section = cfg.get("normalize")
    if not isinstance(section, dict):
        return errors
    errors.extend(
        _validate_pipeline_section(
            section,
            section_name="normalize",
            source_allowed_values=set(INGEST_ALLOWED_KEYS),
            require_sources_non_empty=True,
        )
    )
    errors.extend(_validate_optional_bool(section, key="normalize_summary", full_key="normalize.normalize_summary"))
    for key in ("registry_dir", "input_dir", "output_dir"):
        errors.extend(_validate_optional_non_empty_string(section, key=key, full_key=f"normalize.{key}"))
    return errors


def _validate_pipeline_section(
    section: dict[str, Any],
    *,
    section_name: str,
    source_allowed_values: set[str],
    require_sources_non_empty: bool,
) -> list[str]:
    errors: list[str] = []
    errors.extend(_validate_optional_bool(section, key="enabled", full_key=f"{section_name}.enabled"))
    if section_name == "build_groups":
        errors.extend(_validate_optional_non_empty_string(section, key="input_runs_root", full_key="build_groups.input_runs_root"))
    errors.extend(_validate_optional_non_empty_string(section, key="output_dir", full_key=f"{section_name}.output_dir"))
    errors.extend(_validate_optional_string_list(section, key="groups", full_key=f"{section_name}.groups", allow_empty=False))
    errors.extend(_validate_optional_string_list(section, key="concat_groups", full_key=f"{section_name}.concat_groups", allow_empty=True))

    sources = section.get("sources")
    if sources is not None:
        if not isinstance(sources, list):
            errors.append(f"'{section_name}.sources' must be a list.")
        elif not sources and require_sources_non_empty:
            errors.append(f"'{section_name}.sources' cannot be empty.")
        else:
            for source in sources:
                if not isinstance(source, str) or not source.strip():
                    errors.append(f"'{section_name}.sources' must contain non-empty strings.")
                elif source not in source_allowed_values:
                    errors.append(
                        f"Unknown source in '{section_name}.sources': '{source}'. Allowed sources are: {sorted(source_allowed_values)}."
                    )

    groups = section.get("groups")
    concat_groups = section.get("concat_groups")
    if isinstance(groups, list) and isinstance(concat_groups, list):
        group_set = {str(g).strip() for g in groups if str(g).strip()}
        concat_set = {str(g).strip() for g in concat_groups if str(g).strip()}
        unknown_concat = sorted(concat_set - group_set)
        if unknown_concat:
            errors.append(
                f"'{section_name}.concat_groups' contains groups not listed in '{section_name}.groups': {unknown_concat}."
            )
    return errors


def _validate_validation_section(cfg: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    section = cfg.get("validation")
    if not isinstance(section, dict):
        return errors
    errors.extend(_validate_optional_bool(section, key="enabled", full_key="validation.enabled"))
    errors.extend(_validate_optional_bool(section, key="strict", full_key="validation.strict"))
    for key in ("input_dir", "output_dir"):
        errors.extend(_validate_optional_non_empty_string(section, key=key, full_key=f"validation.{key}"))
    for key in ("traceability_columns", "keys"):
        errors.extend(_validate_optional_string_list(section, key=key, full_key=f"validation.{key}", allow_empty=False))
    for key in ("checks", "required_columns", "completeness", "hydraulic_consistency", "ranges"):
        value = section.get(key)
        if value is not None and not isinstance(value, dict):
            errors.append(f"'validation.{key}' must be a mapping/dictionary.")
    return errors


def _validate_correlation_section(cfg: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    correlation = _get_nested(cfg, ["analysis", "correlation"])
    if correlation is None:
        return errors
    if not isinstance(correlation, dict):
        return ["'analysis.correlation' must be a mapping/dictionary."]
    errors.extend(_validate_optional_non_empty_string(correlation, key="output_root", full_key="analysis.correlation.output_root"))
    errors.extend(_validate_optional_string_list(correlation, key="default_ranking", full_key="analysis.correlation.default_ranking", allow_empty=False))
    variable_roles = correlation.get("variable_roles")
    if variable_roles is not None and not isinstance(variable_roles, dict):
        errors.append("'analysis.correlation.variable_roles' must be a mapping/dictionary.")
    return errors


def _validate_quality_metrics_section(cfg: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    quality = _get_nested(cfg, ["analysis", "quality_metrics"])
    if quality is None:
        return errors
    if not isinstance(quality, dict):
        return ["'analysis.quality_metrics' must be a mapping/dictionary."]

    allowed = {"enabled", "input_dirs", "input_dir", "output_root", "output_dir", "instruments"}
    for key in sorted(quality):
        if key not in allowed:
            errors.append(f"Unknown key 'analysis.quality_metrics.{key}'. Allowed keys are: {sorted(allowed)}.")

    errors.extend(_validate_optional_bool(quality, key="enabled", full_key="analysis.quality_metrics.enabled"))
    for key in ("input_dir", "output_root", "output_dir"):
        errors.extend(_validate_optional_non_empty_string(quality, key=key, full_key=f"analysis.quality_metrics.{key}"))

    input_dirs = quality.get("input_dirs")
    if input_dirs is not None:
        if not isinstance(input_dirs, dict):
            errors.append("'analysis.quality_metrics.input_dirs' must be a mapping/dictionary.")
        else:
            allowed_input_dirs = {"normalized_root", "raw_canonical_root"}
            for key in sorted(input_dirs):
                if key not in allowed_input_dirs:
                    errors.append(
                        f"Unknown key 'analysis.quality_metrics.input_dirs.{key}'. Allowed keys are: {sorted(allowed_input_dirs)}."
                    )
                else:
                    errors.extend(
                        _validate_optional_non_empty_string(
                            input_dirs,
                            key=key,
                            full_key=f"analysis.quality_metrics.input_dirs.{key}",
                        )
                    )

    instruments = quality.get("instruments")
    if instruments is not None:
        if not isinstance(instruments, dict):
            errors.append("'analysis.quality_metrics.instruments' must be a mapping/dictionary.")
        else:
            for instrument_name, instrument_cfg in instruments.items():
                if not isinstance(instrument_cfg, dict):
                    errors.append(f"'analysis.quality_metrics.instruments.{instrument_name}' must be a mapping/dictionary.")
                    continue
                allowed_instrument_keys = {"enabled", "tables", "columns"}
                for key in sorted(instrument_cfg):
                    if key not in allowed_instrument_keys:
                        errors.append(
                            f"Unknown key 'analysis.quality_metrics.instruments.{instrument_name}.{key}'. "
                            f"Allowed keys are: {sorted(allowed_instrument_keys)}."
                        )
                errors.extend(
                    _validate_optional_bool(
                        instrument_cfg,
                        key="enabled",
                        full_key=f"analysis.quality_metrics.instruments.{instrument_name}.enabled",
                    )
                )
                for nested_key in ("tables", "columns"):
                    nested = instrument_cfg.get(nested_key)
                    if nested is not None and not isinstance(nested, dict):
                        errors.append(
                            f"'analysis.quality_metrics.instruments.{instrument_name}.{nested_key}' must be a mapping/dictionary."
                        )
    return errors


def _validate_external_sources_section(cfg: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    sources = cfg.get("external_sources")
    if not isinstance(sources, dict):
        return errors
    for source_name in ("model", "dinagua"):
        source = sources.get(source_name)
        if source is None:
            continue
        if not isinstance(source, dict):
            errors.append(f"'external_sources.{source_name}' must be a mapping/dictionary.")
            continue
        for key in ("raw_dir", "normalized_dir"):
            errors.extend(_validate_optional_non_empty_string(source, key=key, full_key=f"external_sources.{source_name}.{key}"))
    return errors


def _validate_measuring_instruments_section(cfg: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    instruments = cfg.get("measuring_instruments")
    if instruments is None:
        return errors
    if not isinstance(instruments, list):
        return errors
    for idx, item in enumerate(instruments):
        prefix = f"measuring_instruments[{idx}]"
        if not isinstance(item, dict):
            errors.append(f"'{prefix}' must be a mapping/dictionary.")
            continue
        for key in ("code", "subdir"):
            errors.extend(_validate_required_non_empty_string(item, key=key, full_key=f"{prefix}.{key}"))
        for key in ("name", "summary_format", "flow_column", "flow_unit", "flow_row_label", "time_row_label"):
            errors.extend(_validate_optional_non_empty_string(item, key=key, full_key=f"{prefix}.{key}"))
    return errors


def _validate_path_values(cfg: dict[str, Any], *, config_path: Path | None) -> list[str]:
    base_dir = _get_base_dir(config_path)
    return _collect_path_errors(cfg, base_dir=base_dir, prefix="")


def _collect_path_errors(value: Any, *, base_dir: Path, prefix: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return errors
    for key, item in value.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(item, dict):
            errors.extend(_collect_path_errors(item, base_dir=base_dir, prefix=full_key))
            continue
        if key not in PATH_KEYS_MUST_EXIST and key not in PATH_KEYS_CAN_BE_CREATED:
            continue
        if item is None:
            errors.append(f"Path key '{full_key}' cannot be null.")
            continue
        if not isinstance(item, (str, Path)):
            errors.append(f"Path key '{full_key}' must be a string or Path.")
            continue
        path = _resolve_path(item, base_dir=base_dir)
        if key in PATH_KEYS_MUST_EXIST and not path.exists():
            errors.append(f"Path defined in '{full_key}' does not exist: {path}")
        elif key in PATH_KEYS_CAN_BE_CREATED and not path.parent.exists():
            errors.append(f"Parent directory for '{full_key}' does not exist: {path.parent}")
    return errors


def _resolve_path(value: str | Path, *, base_dir: Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def _get_base_dir(config_path: Path | None) -> Path:
    if config_path is None:
        return Path.cwd()
    resolved = config_path.resolve()
    if len(resolved.parents) >= 3:
        return resolved.parents[2]
    return Path.cwd()


def _get_nested(cfg: dict[str, Any], keys: list[str], default: Any = None) -> Any:
    cur: Any = cfg
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def _validate_required_non_empty_string(section: dict[str, Any], *, key: str, full_key: str) -> list[str]:
    if key not in section:
        return [f"Missing required key: '{full_key}'."]
    return _validate_optional_non_empty_string(section, key=key, full_key=full_key)


def _validate_optional_non_empty_string(section: dict[str, Any], *, key: str, full_key: str) -> list[str]:
    if key not in section:
        return []
    value = section[key]
    if not isinstance(value, str):
        return [f"'{full_key}' must be a string."]
    if not value.strip():
        return [f"'{full_key}' cannot be empty."]
    return []


def _validate_optional_bool(section: dict[str, Any], *, key: str, full_key: str) -> list[str]:
    if key not in section:
        return []
    return [] if isinstance(section[key], bool) else [f"'{full_key}' must be true or false."]


def _validate_optional_string_list(section: dict[str, Any], *, key: str, full_key: str, allow_empty: bool) -> list[str]:
    if key not in section:
        return []
    value = section[key]
    if not isinstance(value, list):
        return [f"'{full_key}' must be a list."]
    if not value and not allow_empty:
        return [f"'{full_key}' cannot be empty."]
    return [f"All items in '{full_key}' must be non-empty strings." for item in value if not isinstance(item, str) or not item.strip()]


def _format_errors(errors: list[str]) -> str:
    joined = "\n".join(f"- {error}" for error in errors)
    return f"Invalid Aforix configuration:\n{joined}"
