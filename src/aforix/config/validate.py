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
}

REQUIRED_TOP_LEVEL_KEYS = {
    "project",
    "paths",
}

SECTION_ALLOWED_KEYS: dict[str, set[str]] = {
    "project": {
        "name",
        "description",
        "timezone",
    },
    "paths": {
        "raw_data_dir",
        "runs_root",
        "database_root",
    },
    "ingest": {
        "flowtracker",
        "molinete",
        "nivus",
        "m9",
    },
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
        "ranges",    "enabled",
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
    "export": {
        "tables",
        "excel",
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
}

INGEST_ALLOWED_KEYS: dict[str, set[str]] = {
    "flowtracker": {
        "enabled",
        "raw_subdir",
        "spec_path",
    },
    "molinete": {
        "enabled",
        "raw_subdir",
        "sheet_name",
    },
    "nivus": {
        "enabled",
        "raw_subdir",
    },
    "m9": {
        "enabled",
        "raw_subdir",
    },
}

EXPORT_ALLOWED_KEYS: dict[str, set[str]] = {
    "tables": {
        "enabled",
        "input_dir",
        "output_dir",
    },
    "excel": {
        "enabled",
        "input_dir",
        "output_dir",
    },
}

PATH_KEYS_MUST_EXIST = {
    "raw_data_dir",
    "input_runs_root",
    "registry_dir",
    "spec_path",
}

PATH_KEYS_CAN_BE_CREATED = {
    "runs_root",
    "database_root",
    "output_dir",
    "input_dir",
}


def validate_config(
    cfg: dict[str, Any],
    *,
    config_path: Path | None = None,
) -> None:
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
    errors.extend(_validate_path_values(cfg, config_path=config_path))

    if errors:
        raise ValueError(_format_errors(errors))


def _validate_root_type(cfg: Any) -> list[str]:
    if not isinstance(cfg, dict):
        return ["Config root must be a mapping/dictionary."]
    return []


def _validate_required_top_level_keys(cfg: dict[str, Any]) -> list[str]:
    return [
        f"Missing required top-level key: '{key}'."
        for key in sorted(REQUIRED_TOP_LEVEL_KEYS)
        if key not in cfg
    ]


def _validate_unknown_top_level_keys(cfg: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    for key in sorted(cfg.keys()):
        if key not in TOP_LEVEL_ALLOWED_KEYS:
            errors.append(
                f"Unknown top-level key: '{key}'. "
                f"Allowed keys are: {sorted(TOP_LEVEL_ALLOWED_KEYS)}."
            )

    return errors


def _validate_sections_are_dicts(cfg: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    for key, value in cfg.items():
        if key in TOP_LEVEL_ALLOWED_KEYS and not isinstance(value, dict):
            errors.append(f"Section '{key}' must be a mapping/dictionary.")

    return errors


def _validate_unknown_section_keys(cfg: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    for section, allowed_keys in SECTION_ALLOWED_KEYS.items():
        value = cfg.get(section)

        if value is None or not isinstance(value, dict):
            continue

        for key in sorted(value.keys()):
            if key not in allowed_keys:
                errors.append(
                    f"Unknown key '{section}.{key}'. "
                    f"Allowed keys in '{section}' are: {sorted(allowed_keys)}."
                )

    return errors


def _validate_ingest_sections(cfg: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    ingest = cfg.get("ingest")
    if ingest is None or not isinstance(ingest, dict):
        return errors

    for instrument, settings in ingest.items():
        if instrument not in INGEST_ALLOWED_KEYS:
            errors.append(
                f"Unknown ingest instrument: 'ingest.{instrument}'. "
                f"Allowed instruments are: {sorted(INGEST_ALLOWED_KEYS)}."
            )
            continue

        if not isinstance(settings, dict):
            errors.append(f"Section 'ingest.{instrument}' must be a mapping/dictionary.")
            continue

        allowed_keys = INGEST_ALLOWED_KEYS[instrument]

        for key in sorted(settings.keys()):
            if key not in allowed_keys:
                errors.append(
                    f"Unknown key 'ingest.{instrument}.{key}'. "
                    f"Allowed keys are: {sorted(allowed_keys)}."
                )

        errors.extend(
            _validate_optional_bool(
                settings,
                key="enabled",
                full_key=f"ingest.{instrument}.enabled",
            )
        )

        errors.extend(
            _validate_optional_non_empty_string(
                settings,
                key="raw_subdir",
                full_key=f"ingest.{instrument}.raw_subdir",
            )
        )

        if instrument == "flowtracker":
            errors.extend(
                _validate_required_non_empty_string(
                    settings,
                    key="spec_path",
                    full_key="ingest.flowtracker.spec_path",
                )
            )

        if instrument == "molinete":
            errors.extend(
                _validate_optional_non_empty_string(
                    settings,
                    key="sheet_name",
                    full_key="ingest.molinete.sheet_name",
                )
            )

    return errors


def _validate_export_sections(cfg: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    export = cfg.get("export")
    if export is None or not isinstance(export, dict):
        return errors

    for export_name, settings in export.items():
        if export_name not in EXPORT_ALLOWED_KEYS:
            errors.append(
                f"Unknown export section: 'export.{export_name}'. "
                f"Allowed sections are: {sorted(EXPORT_ALLOWED_KEYS)}."
            )
            continue

        if not isinstance(settings, dict):
            errors.append(f"Section 'export.{export_name}' must be a mapping/dictionary.")
            continue

        allowed_keys = EXPORT_ALLOWED_KEYS[export_name]

        for key in sorted(settings.keys()):
            if key not in allowed_keys:
                errors.append(
                    f"Unknown key 'export.{export_name}.{key}'. "
                    f"Allowed keys are: {sorted(allowed_keys)}."
                )

        errors.extend(
            _validate_optional_bool(
                settings,
                key="enabled",
                full_key=f"export.{export_name}.enabled",
            )
        )

    return errors


def _validate_project_section(cfg: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    project = cfg.get("project")
    if not isinstance(project, dict):
        return errors

    errors.extend(
        _validate_required_non_empty_string(
            project,
            key="name",
            full_key="project.name",
        )
    )

    errors.extend(
        _validate_optional_non_empty_string(
            project,
            key="description",
            full_key="project.description",
        )
    )

    errors.extend(
        _validate_optional_non_empty_string(
            project,
            key="timezone",
            full_key="project.timezone",
        )
    )

    return errors


def _validate_paths_section(cfg: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    paths = cfg.get("paths")
    if not isinstance(paths, dict):
        return errors

    for key in ("raw_data_dir", "runs_root", "database_root"):
        errors.extend(
            _validate_required_non_empty_string(
                paths,
                key=key,
                full_key=f"paths.{key}",
            )
        )

    return errors


def _validate_build_groups_section(cfg: dict[str, Any]) -> list[str]:
    section = cfg.get("build_groups")
    if section is None or not isinstance(section, dict):
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
    if section is None or not isinstance(section, dict):
        return errors

    errors.extend(
        _validate_pipeline_section(
            section,
            section_name="normalize",
            source_allowed_values=set(INGEST_ALLOWED_KEYS),
            require_sources_non_empty=True,
        )
    )

    errors.extend(
        _validate_optional_bool(
            section,
            key="normalize_summary",
            full_key="normalize.normalize_summary",
        )
    )

    for key in ("registry_dir", "input_dir", "output_dir"):
        errors.extend(
            _validate_optional_non_empty_string(
                section,
                key=key,
                full_key=f"normalize.{key}",
            )
        )

    return errors


def _validate_pipeline_section(
    section: dict[str, Any],
    *,
    section_name: str,
    source_allowed_values: set[str],
    require_sources_non_empty: bool,
) -> list[str]:
    errors: list[str] = []

    errors.extend(
        _validate_optional_bool(
            section,
            key="enabled",
            full_key=f"{section_name}.enabled",
        )
    )

    if section_name == "build_groups":
        errors.extend(
            _validate_optional_non_empty_string(
                section,
                key="input_runs_root",
                full_key="build_groups.input_runs_root",
            )
        )

    errors.extend(
        _validate_optional_non_empty_string(
            section,
            key="output_dir",
            full_key=f"{section_name}.output_dir",
        )
    )

    errors.extend(
        _validate_optional_string_list(
            section,
            key="groups",
            full_key=f"{section_name}.groups",
            allow_empty=False,
        )
    )

    errors.extend(
        _validate_optional_string_list(
            section,
            key="concat_groups",
            full_key=f"{section_name}.concat_groups",
            allow_empty=True,
        )
    )

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
                    continue

                if source not in source_allowed_values:
                    errors.append(
                        f"Unknown source in '{section_name}.sources': '{source}'. "
                        f"Allowed sources are: {sorted(source_allowed_values)}."
                    )

    groups = section.get("groups")
    concat_groups = section.get("concat_groups")

    if isinstance(groups, list) and isinstance(concat_groups, list):
        group_set = {str(g).strip() for g in groups if str(g).strip()}
        concat_set = {str(g).strip() for g in concat_groups if str(g).strip()}
        unknown_concat = sorted(concat_set - group_set)

        if unknown_concat:
            errors.append(
                f"'{section_name}.concat_groups' contains groups not listed in "
                f"'{section_name}.groups': {unknown_concat}."
            )

    return errors


def _validate_validation_section(cfg: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    section = cfg.get("validation")
    if section is None or not isinstance(section, dict):
        return errors

    # básicos
    errors.extend(
        _validate_optional_bool(
            section,
            key="enabled",
            full_key="validation.enabled",
        )
    )

    errors.extend(
        _validate_optional_bool(
            section,
            key="strict",
            full_key="validation.strict",
        )
    )

    # paths
    for key in ("input_dir", "output_dir"):
        errors.extend(
            _validate_optional_non_empty_string(
                section,
                key=key,
                full_key=f"validation.{key}",
            )
        )

    # listas clave
    for key in ("traceability_columns", "keys"):
        errors.extend(
            _validate_optional_string_list(
                section,
                key=key,
                full_key=f"validation.{key}",
                allow_empty=False,
            )
        )

    # checks (dict libre, no validamos contenido aún)
    checks = section.get("checks")
    if checks is not None and not isinstance(checks, dict):
        errors.append("'validation.checks' must be a mapping/dictionary.")

    # required_columns
    required = section.get("required_columns")
    if required is not None and not isinstance(required, dict):
        errors.append("'validation.required_columns' must be a mapping/dictionary.")

    # completeness
    completeness = section.get("completeness")
    if completeness is not None and not isinstance(completeness, dict):
        errors.append("'validation.completeness' must be a mapping/dictionary.")

    # hydraulic_consistency
    hc = section.get("hydraulic_consistency")
    if hc is not None and not isinstance(hc, dict):
        errors.append("'validation.hydraulic_consistency' must be a mapping/dictionary.")

    # ranges
    ranges = section.get("ranges")
    if ranges is not None and not isinstance(ranges, dict):
        errors.append("'validation.ranges' must be a mapping/dictionary.")

    return errors


def _validate_path_values(
    cfg: dict[str, Any],
    *,
    config_path: Path | None,
) -> list[str]:
    base_dir = _get_base_dir(config_path)
    return _collect_path_errors(cfg, base_dir=base_dir, prefix="")


def _collect_path_errors(
    value: Any,
    *,
    base_dir: Path,
    prefix: str,
) -> list[str]:
    errors: list[str] = []

    if not isinstance(value, dict):
        return errors

    for key, item in value.items():
        full_key = f"{prefix}.{key}" if prefix else key

        if isinstance(item, dict):
            errors.extend(
                _collect_path_errors(
                    item,
                    base_dir=base_dir,
                    prefix=full_key,
                )
            )
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

        if key in PATH_KEYS_MUST_EXIST:
            if not path.exists():
                errors.append(f"Path defined in '{full_key}' does not exist: {path}")

        elif key in PATH_KEYS_CAN_BE_CREATED:
            parent = path.parent
            if not parent.exists():
                errors.append(
                    f"Parent directory for '{full_key}' does not exist: {parent}"
                )

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


def _validate_required_non_empty_string(
    section: dict[str, Any],
    *,
    key: str,
    full_key: str,
) -> list[str]:
    if key not in section:
        return [f"Missing required key: '{full_key}'."]

    return _validate_optional_non_empty_string(
        section,
        key=key,
        full_key=full_key,
    )


def _validate_optional_non_empty_string(
    section: dict[str, Any],
    *,
    key: str,
    full_key: str,
) -> list[str]:
    if key not in section:
        return []

    value = section[key]

    if not isinstance(value, str):
        return [f"'{full_key}' must be a string."]

    if not value.strip():
        return [f"'{full_key}' cannot be empty."]

    return []


def _validate_optional_bool(
    section: dict[str, Any],
    *,
    key: str,
    full_key: str,
) -> list[str]:
    if key not in section:
        return []

    value = section[key]

    if not isinstance(value, bool):
        return [f"'{full_key}' must be true or false."]

    return []


def _validate_optional_string_list(
    section: dict[str, Any],
    *,
    key: str,
    full_key: str,
    allow_empty: bool,
) -> list[str]:
    if key not in section:
        return []

    value = section[key]

    if not isinstance(value, list):
        return [f"'{full_key}' must be a list."]

    if not value and not allow_empty:
        return [f"'{full_key}' cannot be empty."]

    errors: list[str] = []

    for item in value:
        if not isinstance(item, str) or not item.strip():
            errors.append(f"All items in '{full_key}' must be non-empty strings.")

    return errors


def _format_errors(errors: list[str]) -> str:
    joined = "\n".join(f"- {error}" for error in errors)
    return f"Invalid Aforix configuration:\n{joined}"