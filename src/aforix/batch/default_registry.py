from pathlib import Path
from typing import Any, Callable
import copy

import pandas as pd

from aforix.analysis.correlation.config import load_correlation_config, resolve_correlation_paths, get_variable_roles
from aforix.analysis.correlation.instruments import load_instruments
from aforix.analysis.correlation.pairs import parse_pairs, validate_pair_selection
from aforix.analysis.correlation.workflows.gauges_vs_model import default_ranking, run_gauges_vs_model
from aforix.analysis.correlation.workflows.gauges_vs_stations import run_gauges_vs_stations
from aforix.analysis.correlation.workflows.model_vs_stations import run_model_vs_stations
from aforix.analysis.quality.config import load_quality_config
from aforix.analysis.quality.runner import run_quality_metrics
from aforix.analysis.section_profiles.cli import _apply_cli_overrides as apply_section_profiles_overrides
from aforix.analysis.section_profiles.config import load_section_profiles_config
from aforix.analysis.section_profiles.runner import run_section_profiles
from aforix.analysis.stage_discharge.cli import _apply_cli_overrides
from aforix.analysis.stage_discharge.config import load_stage_discharge_config
from aforix.analysis.stage_discharge.runner import run_stage_discharge
from aforix.batch.models import CommandResult
from aforix.batch.registry import CommandRegistry, RegisteredCommand
from aforix.config.loader import load_config
from aforix.export.sih.config import (
    get_default_selection_file,
    get_lookup_file_paths,
    get_normalized_input_dir,
    get_raw_canonical_input_dir,
    load_sih_config,
)
from aforix.export.sih.runner import SihExportRequest, run_sih_export
from aforix.export.tables.config import (
    get_normalized_root,
    load_config as load_export_tables_config,
)
from aforix.export.tables.runner import ExportRequest, run_export_tables
from aforix.groups.build import run as run_build_groups
from aforix.ingest.flowtracker import run as run_flowtracker
from aforix.ingest.m9 import run as run_m9
from aforix.ingest.molinete import run as run_molinete
from aforix.ingest.nivus import run as run_nivus
from aforix.normalize.run import normalize_database
from aforix.validation.run import run_validation


def _config_path(params: dict[str, Any]) -> Path:
    config = params.get("config") or params.get("main_config")
    if not config:
        raise ValueError("Missing required parameter: config")

    return Path(config).resolve()


def _load_validated_config_from_params(params: dict[str, Any]) -> Path:
    config_path = _config_path(params)
    load_config(config_path)
    return config_path


def _as_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value)
    if isinstance(value, str):
        return tuple(item for item in value.replace(",", " ").split() if item)
    return (str(value),)


def _as_csv_list(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    parsed = [item.strip() for item in str(value).split(",") if item.strip()]
    return parsed or None


def _parse_points(raw: str | None) -> list[str]:
    if not raw:
        return []
    normalized = str(raw).replace(",", " ").replace(";", " ")
    return [token.replace("P", "").strip() for token in normalized.split() if token.strip()]


def _file_size_mb(path: str | Path | None) -> float | None:
    if not path:
        return None

    p = Path(path)
    if not p.exists() or not p.is_file():
        return None

    return round(p.stat().st_size / (1024 * 1024), 4)


def _paths_size_mb(paths: list[str | Path]) -> float | None:
    sizes = [_file_size_mb(path) for path in paths]
    valid = [size for size in sizes if size is not None]

    if not valid:
        return None

    return round(sum(valid), 4)


def _directory_size_mb(path: str | Path | None) -> float | None:
    if not path:
        return None

    root = Path(path)
    if not root.exists():
        return None

    total = 0
    for file_path in root.rglob("*"):
        if file_path.is_file():
            total += file_path.stat().st_size

    return round(total / (1024 * 1024), 4)


def _count_files(path: str | Path | None) -> int | None:
    if not path:
        return None

    root = Path(path)
    if not root.exists():
        return None

    if root.is_file():
        return 1

    return sum(1 for p in root.rglob("*") if p.is_file())


def _count_csv_rows(path: str | Path) -> int | None:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return None

    try:
        return int(len(pd.read_csv(p)))
    except Exception:
        return None


def _sum_csv_rows(paths: list[str | Path]) -> int | None:
    total = 0
    found = False
    for path in paths:
        rows = _count_csv_rows(path)
        if rows is not None:
            total += rows
            found = True
    return total if found else None


def _list_output_files(path: str | Path) -> list[str]:
    root = Path(path)
    if not root.exists():
        return []
    if root.is_file():
        return [str(root)]
    return [str(p) for p in sorted(root.rglob("*")) if p.is_file()]


def _validation_issue_rows(summary_path: Path) -> int | None:
    if not summary_path.exists():
        return None

    try:
        df = pd.read_csv(summary_path)
    except Exception:
        return None

    if "n_rows" not in df.columns:
        return None

    if "status" in df.columns:
        df = df[df["status"].astype(str) != "ok"]

    return int(pd.to_numeric(df["n_rows"], errors="coerce").fillna(0).sum())


def _raw_input_dir(cfg: dict[str, Any], instrument: str) -> Path:
    raw_root = Path(cfg.get("paths", {}).get("raw_data_dir", "data/raw"))
    instrument_cfg = cfg.get("ingest", {}).get(instrument, {}) or {}
    raw_subdir = instrument_cfg.get("raw_subdir")
    if raw_subdir:
        return raw_root / str(raw_subdir)
    return raw_root


def _ingest_result(
    params: dict[str, Any],
    *,
    instrument: str,
    run_callable: Callable[[Path], Path],
) -> CommandResult:
    config_path = _load_validated_config_from_params(params)
    cfg = load_config(config_path)
    input_dir = _raw_input_dir(cfg, instrument)

    input_size_mb = _directory_size_mb(input_dir)
    run_dir = run_callable(config_path)
    output_files = _list_output_files(run_dir)
    csv_outputs = [path for path in output_files if str(path).lower().endswith(".csv")]

    return CommandResult(
        status="success",
        outputs=[str(run_dir), *output_files],
        metrics={
            "ingest_instrument": instrument,
            "input_dir": str(input_dir),
            "input_size_mb": input_size_mb,
            "output_size_mb": _directory_size_mb(run_dir),
            "rows_processed": _sum_csv_rows(csv_outputs),
            "files_written": _count_files(run_dir),
        },
    )


def _config_check(params: dict[str, Any]) -> CommandResult:
    config_path = _load_validated_config_from_params(params)
    cfg = load_config(config_path)

    sections = [key for key, value in cfg.items() if isinstance(value, dict)]

    return CommandResult(
        status="success",
        outputs=[str(config_path)],
        metrics={
            "check_type": "config",
            "config_file": str(config_path),
            "input_size_mb": _file_size_mb(config_path),
            "sections_checked": len(sections),
            "sections": sections,
        },
    )


def _ingest_flowtracker(params: dict[str, Any]) -> CommandResult:
    return _ingest_result(params, instrument="flowtracker", run_callable=run_flowtracker)


def _ingest_molinete(params: dict[str, Any]) -> CommandResult:
    return _ingest_result(params, instrument="molinete", run_callable=run_molinete)


def _ingest_nivus(params: dict[str, Any]) -> CommandResult:
    return _ingest_result(params, instrument="nivus", run_callable=run_nivus)


def _ingest_m9(params: dict[str, Any]) -> CommandResult:
    return _ingest_result(params, instrument="m9", run_callable=run_m9)


def _build_groups(params: dict[str, Any]) -> CommandResult:
    config_path = _load_validated_config_from_params(params)
    cfg = load_config(config_path)
    build_cfg = cfg.get("build_groups", {}) or {}
    paths_cfg = cfg.get("paths", {}) or {}

    input_dir = Path(build_cfg.get("input_runs_root") or paths_cfg.get("runs_root") or "runs")
    output_dir = Path(build_cfg.get("output_dir", "database/raw_canonical"))

    input_size_mb = _directory_size_mb(input_dir)
    run_dir = run_build_groups(config_path)

    output_files = _list_output_files(output_dir)
    run_files = _list_output_files(run_dir)
    csv_outputs = [path for path in output_files if str(path).lower().endswith(".csv")]

    return CommandResult(
        status="success",
        outputs=[str(run_dir), str(output_dir), *output_files, *run_files],
        metrics={
            "build_type": "raw_canonical_groups",
            "input_dir": str(input_dir),
            "output_dir": str(output_dir),
            "input_size_mb": input_size_mb,
            "output_size_mb": _directory_size_mb(output_dir),
            "run_output_size_mb": _directory_size_mb(run_dir),
            "rows_processed": _sum_csv_rows(csv_outputs),
            "files_written": _count_files(output_dir),
            "run_files_written": _count_files(run_dir),
        },
    )


def _normalize_run(params: dict[str, Any]) -> CommandResult:
    config_path = _load_validated_config_from_params(params)
    cfg = load_config(config_path)
    normalize_cfg = cfg.get("normalize", {}) or {}
    input_dir = Path(normalize_cfg.get("input_dir", "database/raw_canonical"))
    output_dir = Path(normalize_cfg.get("output_dir", "database/normalized"))

    input_size_mb = _directory_size_mb(input_dir)
    run_dir = normalize_database(config_path)

    output_files = _list_output_files(output_dir)
    run_files = _list_output_files(run_dir)
    csv_outputs = [path for path in output_files if str(path).lower().endswith(".csv")]

    return CommandResult(
        status="success",
        outputs=[str(run_dir), str(output_dir), *output_files, *run_files],
        metrics={
            "normalize_type": "database",
            "input_dir": str(input_dir),
            "output_dir": str(output_dir),
            "input_size_mb": input_size_mb,
            "output_size_mb": _directory_size_mb(output_dir),
            "run_output_size_mb": _directory_size_mb(run_dir),
            "rows_processed": _sum_csv_rows(csv_outputs),
            "files_written": _count_files(output_dir),
            "run_files_written": _count_files(run_dir),
        },
    )


def _validate_run(params: dict[str, Any]) -> CommandResult:
    config_path = _load_validated_config_from_params(params)
    cfg = load_config(config_path)
    validation_cfg = cfg.get("validation", {}) or {}
    input_dir = Path(validation_cfg.get("input_dir", "database/normalized"))

    output_dir = run_validation(config_path)
    output_files = _list_output_files(output_dir)
    summary_path = output_dir / "validation_summary.csv"

    return CommandResult(
        status="success",
        outputs=[str(output_dir), *output_files],
        metrics={
            "validation_type": "normalized",
            "input_size_mb": _directory_size_mb(input_dir),
            "output_size_mb": _directory_size_mb(output_dir),
            "rows_processed": _validation_issue_rows(summary_path),
            "files_written": _count_files(output_dir),
            "checks_run": _count_csv_rows(summary_path),
        },
    )


def _export_tables(params: dict[str, Any]) -> CommandResult:
    config_path = _load_validated_config_from_params(params)

    if params.get("interactive"):
        raise ValueError("export.tables interactive mode is not supported inside batch run")

    table = params.get("table")
    if not table:
        raise ValueError("Missing required parameter for export.tables: table")

    export_config = load_export_tables_config(str(config_path))
    grouping = params.get("grouping", "monthly")
    fmt = params.get("format", "xlsx")
    flat = bool(params.get("flat", False))

    request = ExportRequest(
        table=str(table),
        instrument=str(params.get("instrument", "all")),
        points=_as_tuple(params.get("points")),
        parameters=_as_tuple(params.get("parameters")),
        early_date=params.get("early_date"),
        late_date=params.get("late_date"),
        grouping=str(grouping),
        fmt=str(fmt),
        pivot=False if flat else grouping in {"monthly", "daily"},
        aggregation=str(params.get("aggregation", "mean")),
    )

    input_file = get_normalized_root(export_config) / f"{request.table}.csv"
    input_size_mb = _file_size_mb(input_file)

    result = run_export_tables(export_config, request)
    output_paths = [str(result.output_file), str(result.metadata_file)]
    output_size_mb = _paths_size_mb(output_paths)

    return CommandResult(
        status="success",
        outputs=output_paths,
        metrics={
            "rows_processed": result.row_count,
            "rows_exported": result.row_count,
            "files_written": 2,
            "input_file": str(input_file),
            "input_size_mb": input_size_mb,
            "output_size_mb": output_size_mb,
            "table": str(table),
            "instrument": request.instrument,
            "grouping": request.grouping,
            "format": request.fmt,
            "aggregation": request.aggregation,
        },
    )


def _export_sih(params: dict[str, Any]) -> CommandResult:
    _load_validated_config_from_params(params)
    sih_config_path = Path(params.get("sih_config", "configs/sih/sih.yaml"))
    sih_config = load_sih_config(sih_config_path)

    if bool(params.get("interactive", False)):
        raise ValueError("export.sih interactive mode is not supported inside batch run")

    selection_file = (
        Path(params["selection_file"])
        if params.get("selection_file")
        else get_default_selection_file(sih_config)
    )

    input_paths: list[Path] = [selection_file]
    input_paths.append(get_normalized_input_dir(sih_config))
    input_paths.append(get_raw_canonical_input_dir(sih_config))
    input_paths.extend(get_lookup_file_paths(sih_config).values())

    result = run_sih_export(
        SihExportRequest(
            sih_config_path=sih_config_path,
            selection_file=selection_file,
            interactive=False,
        )
    )

    output_paths = [str(path) for path in result.exported_files]
    metadata_path = result.output_dir / "sih_export_metadata.csv"
    metadata_rows = _count_csv_rows(metadata_path)

    return CommandResult(
        status="success",
        outputs=[str(result.output_dir), *output_paths],
        metrics={
            "export_type": "sih",
            "selection_file": str(selection_file),
            "input_size_mb": round(sum(_file_size_mb(p) or _directory_size_mb(p) or 0 for p in input_paths), 4),
            "output_size_mb": _directory_size_mb(result.output_dir),
            "rows_processed": metadata_rows,
            "rows_exported": metadata_rows,
            "files_written": len(result.exported_files),
        },
    )


def _analysis_correlation(params: dict[str, Any]) -> CommandResult:
    config_path = _load_validated_config_from_params(params)
    cfg = load_correlation_config(config_path)
    paths = resolve_correlation_paths(config_path)
    instruments = load_instruments(cfg)

    correlation_type = params.get("type")
    if not correlation_type:
        raise ValueError("Missing required parameter for analysis.correlation: type")

    ranking = params.get("ranking")
    ranking_codes = [x.upper() for x in str(ranking).split()] if ranking else default_ranking(cfg, instruments)
    all_pairs = bool(params.get("all_pairs", False))
    pairs = params.get("pairs")
    validate_pair_selection(str(correlation_type), pairs, all_pairs)
    parsed_pairs = parse_pairs(pairs, correlation_type=str(correlation_type))
    points = _parse_points(params.get("points"))
    timestep = params.get("timestep", "daily")

    input_size_mb = round(
        sum(
            value or 0
            for value in (
                _directory_size_mb(paths.normalized_root),
                _directory_size_mb(paths.external_model_dir),
                _directory_size_mb(paths.external_stations_dir),
            )
        ),
        4,
    )

    if correlation_type == "gauges_vs_model":
        output_dir = run_gauges_vs_model(
            normalized_root=paths.normalized_root,
            model_dir=paths.external_model_dir,
            output_dir=paths.output_root,
            instruments=instruments,
            ranking_codes=ranking_codes,
            start_date=params.get("start_date"),
            end_date=params.get("end_date"),
            points=points,
            variable_roles=get_variable_roles(cfg, "gauges_vs_model"),
        )
    elif correlation_type == "gauges_vs_stations":
        output_dir = run_gauges_vs_stations(
            normalized_root=paths.normalized_root,
            stations_dir=paths.external_stations_dir,
            output_dir=paths.output_root,
            instruments=instruments,
            ranking_codes=ranking_codes,
            timestep=str(timestep),
            match_mode=params.get("match_mode", "exact"),
            window_days=int(params.get("window_days", 0)),
            pairs=parsed_pairs,
            variable_roles=get_variable_roles(cfg, "gauges_vs_stations"),
        )
    elif correlation_type == "model_vs_stations":
        output_dir = run_model_vs_stations(
            stations_dir=paths.external_stations_dir,
            model_dir=paths.external_model_dir,
            output_dir=paths.output_root,
            pairs=parsed_pairs,
            timestep=str(timestep),
            all_pairs=all_pairs,
            variable_roles=get_variable_roles(cfg, "model_vs_stations"),
        )
    else:
        raise ValueError(f"Unknown correlation type: {correlation_type}")

    output_files = _list_output_files(output_dir)
    csv_outputs = [path for path in output_files if str(path).lower().endswith(".csv")]
    files_written = _count_files(output_dir)
    warnings: list[str] = []

    if not files_written:
        warnings.append(
            "Correlation completed but no output files were written. "
            "Check point selection, date range, and overlap between input datasets."
        )

    return CommandResult(
        status="success",
        outputs=[str(output_dir), *output_files],
        warnings=warnings,
        metrics={
            "analysis_type": "correlation",
            "correlation_type": str(correlation_type),
            "input_size_mb": input_size_mb,
            "output_size_mb": _directory_size_mb(output_dir),
            "rows_processed": _sum_csv_rows(csv_outputs),
            "files_written": files_written,
            "ranking": ranking_codes,
            "timestep": str(timestep),
            "points": points or "all",
            "pairs": parsed_pairs if parsed_pairs else ("all" if all_pairs else None),
            "all_pairs": all_pairs,
        },
    )


def _analysis_quality(params: dict[str, Any]) -> CommandResult:
    config_path = _load_validated_config_from_params(params)
    qc = load_quality_config(config_path)

    if bool(params.get("interactive", False)):
        raise ValueError("analysis.quality interactive mode is not supported inside batch run")

    aggregation = params.get("aggregation", "daily")
    selected_points = _as_csv_list(params.get("points"))
    selected_months = _as_csv_list(params.get("yyyymm"))
    all_months = bool(params.get("all_months", False))

    input_size_mb = round(
        sum(
            value or 0
            for value in (
                _directory_size_mb(qc.nivus.normalized_points),
                _directory_size_mb(qc.nivus.raw_points),
            )
        ),
        4,
    )

    output_dir = run_quality_metrics(
        config_path,
        aggregation=aggregation,
        points=selected_points,
        months=selected_months,
        all_months=all_months,
    )

    output_paths = [str(path) for path in sorted(output_dir.glob("*")) if path.is_file()]
    output_size_mb = _directory_size_mb(output_dir)
    rows_processed = _count_csv_rows(output_dir / "cg_measurements.csv")

    return CommandResult(
        status="success",
        outputs=[str(output_dir), *output_paths],
        metrics={
            "analysis_type": "quality",
            "aggregation": aggregation,
            "points": selected_points or "all",
            "months": selected_months or ("all" if all_months else None),
            "input_size_mb": input_size_mb,
            "output_size_mb": output_size_mb,
            "rows_processed": rows_processed,
            "files_written": _count_files(output_dir),
        },
    )


def _analysis_stage_discharge(params: dict[str, Any]) -> CommandResult:
    config_path = _load_validated_config_from_params(params)
    cfg = copy.deepcopy(load_stage_discharge_config(config_path))

    _apply_cli_overrides(
        cfg,
        points=params.get("points"),
        start_date=params.get("start_date"),
        end_date=params.get("end_date"),
        instruments=params.get("instruments"),
        ranking=params.get("ranking"),
        depth_mode=params.get("depth_mode"),
        instrument_stage_mode=params.get("instrument_stage_mode"),
        plots=params.get("plots"),
        excel=params.get("excel"),
        max_plots=params.get("max_plots"),
    )

    normalized_root = Path(cfg.get("input_dirs", {}).get("normalized_root", "database/normalized"))
    manual_root = Path(cfg.get("input_dirs", {}).get("manual_stage_root", "database/external/normalized/manual_stage"))
    input_size_mb = round(
        sum(
            value or 0
            for value in (
                _directory_size_mb(normalized_root),
                _directory_size_mb(manual_root),
            )
        ),
        4,
    )

    output_dir = run_stage_discharge(config_path, override_config=cfg)
    output_files = _list_output_files(output_dir)

    rows_processed = _count_csv_rows(output_dir / "stage_discharge_matched_pairs.csv")
    if rows_processed is None:
        rows_processed = _count_csv_rows(output_dir / "stage_discharge_matched.csv")
    if rows_processed is None:
        rows_processed = _count_csv_rows(output_dir / "matched_stage_discharge.csv")

    selection = cfg.get("selection", {}) or {}

    return CommandResult(
        status="success",
        outputs=[str(output_dir), *output_files],
        metrics={
            "analysis_type": "stage-discharge",
            "input_size_mb": input_size_mb,
            "output_size_mb": _directory_size_mb(output_dir),
            "rows_processed": rows_processed,
            "files_written": _count_files(output_dir),
            "points": selection.get("points", "all"),
            "depth_mode": selection.get("depth_mode", cfg.get("depth_mode", "both")),
            "instrument_stage_mode": selection.get("instrument_stage_mode", cfg.get("instrument_stage_mode", "both")),
        },
    )


def _analysis_section_profiles(params: dict[str, Any]) -> CommandResult:
    config_path = _load_validated_config_from_params(params)
    cfg = copy.deepcopy(load_section_profiles_config(config_path))

    if bool(params.get("interactive", False)):
        raise ValueError("analysis.section-profiles interactive mode is not supported inside batch run")

    apply_section_profiles_overrides(
        cfg,
        instruments=params.get("instruments"),
        points=params.get("points"),
        start_date=params.get("start_date"),
        end_date=params.get("end_date"),
        x_axis=params.get("x_axis"),
        y_axis=params.get("y_axis"),
        chart_type=params.get("chart_type"),
    )

    normalized_root = Path(cfg.get("input_dirs", {}).get("normalized_root", "database/normalized"))
    input_size_mb = _directory_size_mb(normalized_root)

    output_dir = run_section_profiles(config_path, override_config=cfg)
    output_files = _list_output_files(output_dir)
    files_written = _count_files(output_dir)
    warnings: list[str] = []

    if not files_written:
        warnings.append(
            "Section profiles analysis completed but no output files were written. "
            "Check point selection, instrument selection, and available section/profile data."
        )

    selection = cfg.get("selection", {}) or {}
    defaults = cfg.get("defaults", {}) or {}

    return CommandResult(
        status="success",
        outputs=[str(output_dir), *output_files],
        warnings=warnings,
        metrics={
            "analysis_type": "section-profiles",
            "input_size_mb": input_size_mb,
            "output_size_mb": _directory_size_mb(output_dir),
            "rows_processed": None,
            "files_written": files_written,
            "points": selection.get("points", "all"),
            "instruments": selection.get("instruments", "all"),
            "x_axis": defaults.get("x_axis", "distance_m"),
            "y_axis": defaults.get("y_axis", "depth_m"),
            "chart_type": defaults.get("chart_type", "scatter"),
        },
    )


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
        RegisteredCommand("analysis.correlation", _analysis_correlation, "Run correlation analysis", "analysis"),
        RegisteredCommand("analysis.quality", _analysis_quality, "Run quality metrics analysis", "analysis"),
        RegisteredCommand("analysis.stage-discharge", _analysis_stage_discharge, "Run stage-discharge analysis", "analysis"),
        RegisteredCommand("analysis.section-profiles", _analysis_section_profiles, "Run section profiles analysis", "analysis"),
    ]

    for command in commands:
        registry.register(command)

    return registry
