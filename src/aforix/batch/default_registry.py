from pathlib import Path
from typing import Any

from aforix.config.loader import load_config
from aforix.export.sih.cli import main as export_sih_main
from aforix.export.tables.cli import main as export_tables_main
from aforix.groups.build import run as run_build_groups
from aforix.ingest.flowtracker import run as run_flowtracker
from aforix.ingest.m9 import run as run_m9
from aforix.ingest.molinete import run as run_molinete
from aforix.ingest.nivus import run as run_nivus
from aforix.normalize.run import normalize_database
from aforix.validation.run import run_validation
from aforix.batch.registry import CommandRegistry, RegisteredCommand


def _config_path(params: dict[str, Any]) -> Path:
    config = params.get("config") or params.get("main_config")
    if not config:
        raise ValueError("Missing required parameter: config")

    return Path(config).resolve()


def _load_validated_config_from_params(params: dict[str, Any]) -> Path:
    config_path = _config_path(params)
    load_config(config_path)
    return config_path


def _extend_if_present(argv: list[str], params: dict[str, Any], key: str, option: str) -> None:
    value = params.get(key)
    if value is None:
        return

    if isinstance(value, list | tuple):
        argv.append(option)
        argv.extend(str(item) for item in value)
        return

    argv.extend([option, str(value)])


def _config_check(params: dict[str, Any]) -> None:
    _load_validated_config_from_params(params)


def _ingest_flowtracker(params: dict[str, Any]) -> None:
    run_flowtracker(_load_validated_config_from_params(params))


def _ingest_molinete(params: dict[str, Any]) -> None:
    run_molinete(_load_validated_config_from_params(params))


def _ingest_nivus(params: dict[str, Any]) -> None:
    run_nivus(_load_validated_config_from_params(params))


def _ingest_m9(params: dict[str, Any]) -> None:
    run_m9(_load_validated_config_from_params(params))


def _build_groups(params: dict[str, Any]) -> None:
    run_build_groups(_load_validated_config_from_params(params))


def _normalize_run(params: dict[str, Any]) -> None:
    normalize_database(_load_validated_config_from_params(params))


def _validate_run(params: dict[str, Any]) -> None:
    run_validation(_load_validated_config_from_params(params))


def _export_tables(params: dict[str, Any]) -> None:
    config_path = _load_validated_config_from_params(params)
    argv = ["-c", str(config_path)]

    if params.get("interactive"):
        argv.append("--interactive")
    else:
        _extend_if_present(argv, params, "table", "--table")
        _extend_if_present(argv, params, "instrument", "--instrument")
        _extend_if_present(argv, params, "points", "--points")
        _extend_if_present(argv, params, "parameters", "--parameters")
        _extend_if_present(argv, params, "early_date", "--early-date")
        _extend_if_present(argv, params, "late_date", "--late-date")
        _extend_if_present(argv, params, "grouping", "--grouping")
        _extend_if_present(argv, params, "format", "--format")
        _extend_if_present(argv, params, "aggregation", "--aggregation")

        if params.get("flat"):
            argv.append("--flat")

    export_tables_main(argv)


def _export_sih(params: dict[str, Any]) -> None:
    config_path = _load_validated_config_from_params(params)
    sih_config = params.get("sih_config", "configs/sih/sih.yaml")

    argv = ["-c", str(config_path), "--sih-config", str(sih_config)]

    selection_file = params.get("selection_file")
    if selection_file:
        argv.extend(["--selection-file", str(selection_file)])

    if params.get("interactive"):
        argv.append("--interactive")

    export_sih_main(argv)


def build_default_registry() -> CommandRegistry:
    registry = CommandRegistry()

    commands = [
        RegisteredCommand("config-check", _config_check, "Validate main project config", "config"),
        RegisteredCommand("ingest.flowtracker", _ingest_flowtracker, "Run FlowTracker ingest", "ingest"),
        RegisteredCommand("ingest.molinete", _ingest_molinete, "Run Molinete ingest", "ingest"),
        RegisteredCommand("ingest.nivus", _ingest_nivus, "Run Nivus ingest", "ingest"),
        RegisteredCommand("ingest.m9", _ingest_m9, "Run M9 ingest", "ingest"),
        RegisteredCommand("build-groups", _build_groups, "Build raw canonical grouped database", "groups"),
        RegisteredCommand("normalize.run", _normalize_run, "Normalize raw canonical database", "normalize"),
        RegisteredCommand("validate.run", _validate_run, "Validate normalized datasets", "validation"),
        RegisteredCommand("export.tables", _export_tables, "Export normalized tables", "export"),
        RegisteredCommand("export.sih", _export_sih, "Export SIH files", "export"),
    ]

    for command in commands:
        registry.register(command)

    return registry
