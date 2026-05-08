from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from aforix.config.loader import load_config
from aforix.runs.manager import create_run
from aforix.ingest.adapters.flowtracker_dis import parse_flowtracker_dis
from aforix.ingest.discovery import (
    fallback_station_id_from_parents,
    find_files_recursive,
)
from aforix.ingest.metadata import clean_station_id, clean_station_name
from aforix.ingest.metadata_policy import (
    MetadataExtractionContext,
    extract_metadata,
)


INSTRUMENT_NAME = "flowtracker"

TABLES_BY_INSTRUMENT = {
    INSTRUMENT_NAME: ["Summary", "Points"],
}


def _resolve_config_path(path_value: str | Path, *, project_root: Path) -> Path:
    path = Path(path_value)

    if not path.is_absolute():
        path = project_root / path

    return path.resolve()


def _get_project_root(config_path: Path) -> Path:
    resolved = config_path.resolve()

    # Expected layout:
    # project_root/configs/examples/main.yaml
    if len(resolved.parents) >= 3:
        return resolved.parents[2]

    return Path.cwd().resolve()


def _get_flowtracker_config(cfg: dict[str, Any]) -> dict[str, Any]:
    try:
        return cfg["ingest"][INSTRUMENT_NAME]
    except KeyError as exc:
        raise ValueError(
            "Missing FlowTracker configuration section: "
            "'ingest.flowtracker'."
        ) from exc


def _get_raw_data_root(
    cfg: dict[str, Any],
    *,
    config_path: Path,
) -> Path:
    project_root = _get_project_root(config_path)

    try:
        raw_data_dir = cfg["paths"]["raw_data_dir"]
    except KeyError as exc:
        raise ValueError(
            "Missing required config key: 'paths.raw_data_dir'."
        ) from exc

    return _resolve_config_path(raw_data_dir, project_root=project_root)


def _get_flowtracker_raw_root(
    cfg: dict[str, Any],
    *,
    config_path: Path,
) -> Path:
    raw_data_root = _get_raw_data_root(cfg, config_path=config_path)
    flowtracker_cfg = _get_flowtracker_config(cfg)

    raw_subdir = flowtracker_cfg.get("raw_subdir")

    if not raw_subdir:
        raise ValueError(
            "Missing required config key: 'ingest.flowtracker.raw_subdir'."
        )

    flowtracker_root = raw_data_root / str(raw_subdir)

    if not flowtracker_root.exists():
        raise ValueError(
            "FlowTracker raw data directory does not exist: "
            f"{flowtracker_root}"
        )

    if not flowtracker_root.is_dir():
        raise ValueError(
            "FlowTracker raw data path is not a directory: "
            f"{flowtracker_root}"
        )

    return flowtracker_root.resolve()


def _find_dis_files_flowtracker(
    cfg: dict[str, Any],
    *,
    config_path: Path,
) -> list[Path]:
    flowtracker_root = _get_flowtracker_raw_root(cfg, config_path=config_path)
    return find_files_recursive(flowtracker_root, {".dis"})


def _prepare_output_dirs(run_dir: Path) -> dict[str, Path]:
    outdir_root = run_dir / "outputs" / "raw_canonical" / INSTRUMENT_NAME

    group_dirs = {
        group: outdir_root / group
        for group in TABLES_BY_INSTRUMENT[INSTRUMENT_NAME]
    }

    for group_dir in group_dirs.values():
        group_dir.mkdir(parents=True, exist_ok=True)

    return group_dirs


def _parse_measurement_datetime(summary: dict[str, Any], *, dis_path: Path) -> datetime:
    start_dt = (
        summary.get("start_date_time")
        or summary.get("start_date_and_time")
        or summary.get("fecha_y_hora_de_inicio")
    )

    if not start_dt:
        raise ValueError(
            f"Missing start_date_time in FlowTracker summary: {dis_path}"
        )

    text = str(start_dt).strip()

    for fmt in ("%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue

    raise ValueError(
        "Invalid FlowTracker start_date_time format. "
        f"Expected 'YYYY/MM/DD HH:MM:SS' or 'YYYY-MM-DD HH:MM:SS', got: {text}"
    )


def _extract_station_id(summary: dict[str, Any], *, dis_path: Path) -> str:
    raw_station_id = (
        summary.get("file_name")
        or summary.get("nombre_del_fichero")
        or summary.get("input_file")
    )

    return clean_station_id(
        raw_station_id,
        fallback=fallback_station_id_from_parents(dis_path),
    )


def _extract_station_name(summary: dict[str, Any]) -> str | None:
    return clean_station_name(
        summary.get("site_name")
        or summary.get("station_name")
        or summary.get("nom_del_punto_de_aforo")
    )


def _extract_flowtracker_metadata(
    *,
    flowtracker_cfg: dict[str, Any],
    summary: dict[str, Any],
    dis_path: Path,
) -> dict[str, str | None]:
    """Resolve FlowTracker metadata using config policy with legacy fallbacks."""

    raw_fields = dict(summary)
    raw_fields["fallback_station_id"] = fallback_station_id_from_parents(dis_path) or ""
    raw_fields["filename"] = dis_path.name
    raw_fields["stem"] = dis_path.stem

    context = MetadataExtractionContext(
        raw_fields=raw_fields,
        source_path=dis_path,
    )

    policy = flowtracker_cfg.get("metadata_policy", {}) or {}
    resolved = extract_metadata(policy, context=context)

    station_id = resolved.get("station_id") or _extract_station_id(summary, dis_path=dis_path)
    station_name = resolved.get("station_name") or _extract_station_name(summary)

    measurement_dt = _parse_measurement_datetime(summary, dis_path=dis_path)
    measurement_date = resolved.get("measurement_date") or measurement_dt.strftime("%Y%m%d")
    measurement_time = resolved.get("measurement_time") or measurement_dt.strftime("%H%M%S")

    return {
        "station_id": station_id,
        "station_name": station_name,
        "measurement_date": measurement_date,
        "measurement_time": measurement_time,
    }


def _add_common_metadata(
    df: pd.DataFrame,
    *,
    station_id: str,
    station_name: str | None,
    measurement_date: str,
    measurement_time: str,
    source_path: Path,
    run_dir: Path,
) -> pd.DataFrame:
    df = df.copy()

    df["station_id"] = station_id
    df["station_name"] = station_name
    df["measurement_date"] = measurement_date
    df["measurement_time"] = measurement_time
    df["instrument"] = INSTRUMENT_NAME
    df["source_file"] = str(source_path)
    df["source_run_dir"] = str(run_dir)

    return df


def _write_summary(
    summary: dict[str, Any],
    *,
    output_dir: Path,
    station_id: str,
    station_name: str | None,
    measurement_date: str,
    measurement_time: str,
    source_path: Path,
    run_dir: Path,
) -> Path:
    summary_df = pd.DataFrame([summary])

    summary_df = _add_common_metadata(
        summary_df,
        station_id=station_id,
        station_name=station_name,
        measurement_date=measurement_date,
        measurement_time=measurement_time,
        source_path=source_path,
        run_dir=run_dir,
    )

    output_path = (
        output_dir
        / f"{station_id}_Summary_{measurement_date}_{measurement_time}.csv"
    )

    summary_df.to_csv(output_path, index=False)
    return output_path


def _write_points(
    points: pd.DataFrame | list[dict[str, Any]] | dict[str, Any],
    *,
    output_dir: Path,
    station_id: str,
    station_name: str | None,
    measurement_date: str,
    measurement_time: str,
    source_path: Path,
    run_dir: Path,
) -> Path | None:
    if isinstance(points, pd.DataFrame):
        points_df = points.copy()
    else:
        points_df = pd.DataFrame(points)

    if points_df.empty:
        return None

    points_df = _add_common_metadata(
        points_df,
        station_id=station_id,
        station_name=station_name,
        measurement_date=measurement_date,
        measurement_time=measurement_time,
        source_path=source_path,
        run_dir=run_dir,
    )

    output_path = (
        output_dir
        / f"{station_id}_Points_{measurement_date}_{measurement_time}.csv"
    )

    points_df.to_csv(output_path, index=False)
    return output_path


def _process_dis_file(
    dis_path: Path,
    *,
    flowtracker_cfg: dict[str, Any],
    group_dirs: dict[str, Path],
    run_dir: Path,
) -> None:
    summary, points = parse_flowtracker_dis(dis_path)

    meta = _extract_flowtracker_metadata(
        flowtracker_cfg=flowtracker_cfg,
        summary=summary,
        dis_path=dis_path,
    )

    station_id = str(meta["station_id"])
    station_name = meta["station_name"]
    measurement_date = str(meta["measurement_date"])
    measurement_time = str(meta["measurement_time"])

    summary_outpath = _write_summary(
        summary,
        output_dir=group_dirs["Summary"],
        station_id=station_id,
        station_name=station_name,
        measurement_date=measurement_date,
        measurement_time=measurement_time,
        source_path=dis_path,
        run_dir=run_dir,
    )

    print(f"Saved: {summary_outpath}")

    points_outpath = _write_points(
        points,
        output_dir=group_dirs["Points"],
        station_id=station_id,
        station_name=station_name,
        measurement_date=measurement_date,
        measurement_time=measurement_time,
        source_path=dis_path,
        run_dir=run_dir,
    )

    if points_outpath is not None:
        print(f"Saved: {points_outpath}")


def run(config_path: Path) -> Path:
    """Run FlowTracker ingest pipeline."""

    config_path = Path(config_path).resolve()
    cfg = load_config(config_path)

    flowtracker_cfg = _get_flowtracker_config(cfg)

    if flowtracker_cfg.get("enabled") is False:
        print("FlowTracker ingest is disabled in config.")
        return create_run("ingest_flowtracker", config_path)

    run_dir = create_run("ingest_flowtracker", config_path)
    group_dirs = _prepare_output_dirs(run_dir)

    candidates = _find_dis_files_flowtracker(
        cfg,
        config_path=config_path,
    )

    print(f"Found .dis files: {len(candidates)}")

    if not candidates:
        print("No .dis files found with current config search settings.")
        print(
            "Expected FlowTracker raw directory: "
            f"{_get_flowtracker_raw_root(cfg, config_path=config_path)}"
        )
        print(f"Run created: {run_dir}")
        return run_dir

    processed = 0
    failed: list[tuple[str, str]] = []

    for dis_path in candidates:
        try:
            _process_dis_file(
                dis_path,
                flowtracker_cfg=flowtracker_cfg,
                group_dirs=group_dirs,
                run_dir=run_dir,
            )
            processed += 1

        except Exception as exc:
            print(f"ERROR processing {dis_path}: {exc}")
            failed.append((str(dis_path), str(exc)))

    print(f"Processed OK: {processed}/{len(candidates)}")

    if failed:
        print("Failed .dis files:")
        for path, error in failed:
            print(f" - {path}: {error}")

    print(f"Run created: {run_dir}")

    return run_dir
