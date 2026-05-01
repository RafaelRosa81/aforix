from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from aforix.config.loader import load_config
from aforix.runs.manager import create_run
from aforix.ingest.adapters.nivus_xml import (
    parse_nivus_metadata,
    parse_nivus_xml,
    parse_datetime_from_filename,
)
from aforix.ingest.discovery import (
    fallback_station_id_from_parents,
    find_files_recursive,
)
from aforix.ingest.metadata import clean_station_id, clean_station_name


INSTRUMENT_NAME = "nivus"
GROUPS = ["Summary", "Points", "Sections", "Gates"]


def _resolve_config_path(path_value: str | Path, *, project_root: Path) -> Path:
    path = Path(path_value)

    if not path.is_absolute():
        path = project_root / path

    return path.resolve()


def _get_project_root(config_path: Path) -> Path:
    resolved = config_path.resolve()

    if len(resolved.parents) >= 3:
        return resolved.parents[2]

    return Path.cwd().resolve()


def _get_nivus_config(cfg: dict[str, Any]) -> dict[str, Any]:
    try:
        return cfg["ingest"][INSTRUMENT_NAME]
    except KeyError as exc:
        raise ValueError("Missing Nivus configuration section: 'ingest.nivus'.") from exc


def _get_raw_data_root(
    cfg: dict[str, Any],
    *,
    config_path: Path,
) -> Path:
    project_root = _get_project_root(config_path)

    try:
        raw_data_dir = cfg["paths"]["raw_data_dir"]
    except KeyError as exc:
        raise ValueError("Missing required config key: 'paths.raw_data_dir'.") from exc

    return _resolve_config_path(raw_data_dir, project_root=project_root)


def _get_nivus_raw_root(
    cfg: dict[str, Any],
    *,
    config_path: Path,
) -> Path:
    raw_data_root = _get_raw_data_root(cfg, config_path=config_path)
    nivus_cfg = _get_nivus_config(cfg)

    raw_subdir = nivus_cfg.get("raw_subdir")

    if not raw_subdir:
        raise ValueError("Missing required config key: 'ingest.nivus.raw_subdir'.")

    nivus_root = raw_data_root / str(raw_subdir)

    if not nivus_root.exists():
        raise ValueError(f"Nivus raw data directory does not exist: {nivus_root}")

    if not nivus_root.is_dir():
        raise ValueError(f"Nivus raw data path is not a directory: {nivus_root}")

    return nivus_root.resolve()


def _get_timezone(cfg: dict[str, Any]) -> str:
    return str(cfg.get("project", {}).get("timezone", "America/Montevideo"))


def _find_nivus_xml_files(
    cfg: dict[str, Any],
    *,
    config_path: Path,
) -> list[dict[str, str]]:
    nivus_root = _get_nivus_raw_root(cfg, config_path=config_path)

    candidates: list[dict[str, str]] = []

    for xml_path in find_files_recursive(nivus_root, {".xml"}):
        candidates.append(
            {
                "xml_file": xml_path.name,
                "xml_path": str(xml_path),
                "fallback_station_id": fallback_station_id_from_parents(xml_path) or "",
            }
        )

    return candidates


def _rows_to_dataframe(rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Create a DataFrame while preserving first-seen column order."""

    if not rows:
        return pd.DataFrame()

    columns: list[str] = []
    seen: set[str] = set()

    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                columns.append(key)

    return pd.DataFrame(rows, columns=columns)


def _add_ingest_metadata(
    df: pd.DataFrame,
    *,
    source: str,
    station_id: str,
    station_name: str | None,
    measurement_date: str,
    measurement_time: str,
    timezone: str,
    input_file: str,
    input_path: str,
    run_id: str,
) -> pd.DataFrame:
    """Add minimal ingest metadata to every output table."""

    df = df.copy()

    metadata = {
        "source": source,
        "station_id": station_id,
        "station_name": station_name,
        "measurement_date": measurement_date,
        "measurement_time": measurement_time,
        "timezone": timezone,
        "input_file": input_file,
        "input_path": input_path,
        "run_id": run_id,
    }

    for key, value in reversed(metadata.items()):
        df.insert(0, key, value)

    return df


def _prepare_output_dirs(run_dir: Path) -> dict[str, Path]:
    outdir_root = run_dir / "outputs" / "raw_canonical" / INSTRUMENT_NAME

    group_dirs = {
        group: outdir_root / group
        for group in GROUPS
    }

    for group_dir in group_dirs.values():
        group_dir.mkdir(parents=True, exist_ok=True)

    return group_dirs


def _write_group_csv(
    rows: list[dict[str, Any]],
    *,
    group: str,
    output_dir: Path,
    station_id: str,
    station_name: str | None,
    measurement_date: str,
    measurement_time: str,
    timezone: str,
    input_file: str,
    input_path: str,
    run_id: str,
) -> Path:
    df = _rows_to_dataframe(rows)

    df = _add_ingest_metadata(
        df,
        source=INSTRUMENT_NAME,
        station_id=station_id,
        station_name=station_name,
        measurement_date=measurement_date,
        measurement_time=measurement_time,
        timezone=timezone,
        input_file=input_file,
        input_path=input_path,
        run_id=run_id,
    )

    outpath = output_dir / f"{station_id}_{group}_{measurement_date}_{measurement_time}.csv"

    df.to_csv(outpath, index=False, encoding="utf-8-sig")
    return outpath


def _process_xml_file(
    item: dict[str, str],
    *,
    group_dirs: dict[str, Path],
    timezone: str,
    run_dir: Path,
) -> None:
    xml_path = Path(item["xml_path"])

    raw_groups = parse_nivus_xml(xml_path)
    meta = parse_nivus_metadata(xml_path)

    station_id = clean_station_id(
        meta.get("station_id"),
        fallback=item.get("fallback_station_id"),
    )

    station_name = clean_station_name(
        meta.get("station_name")
    )

    measurement_date = meta.get("measurement_date")
    measurement_time = meta.get("measurement_time")

    if not measurement_date or measurement_date == "unknown_date":
        measurement_date, measurement_time = parse_datetime_from_filename(xml_path.name)

    for group in GROUPS:
        rows = raw_groups.get(group, [])

        outpath = _write_group_csv(
            rows,
            group=group,
            output_dir=group_dirs[group],
            station_id=station_id,
            station_name=station_name,
            measurement_date=measurement_date,
            measurement_time=measurement_time,
            timezone=timezone,
            input_file=xml_path.name,
            input_path=str(xml_path.resolve()),
            run_id=run_dir.name,
        )

        print(f"Saved: {outpath}")


def run(config_path: Path) -> Path:
    """Run clean raw Nivus XML ingest pipeline."""

    config_path = Path(config_path).resolve()
    cfg = load_config(config_path)

    nivus_cfg = _get_nivus_config(cfg)

    if nivus_cfg.get("enabled") is False:
        print("Nivus ingest is disabled in config.")
        return create_run("ingest_nivus", config_path)

    run_dir = create_run("ingest_nivus", config_path)
    group_dirs = _prepare_output_dirs(run_dir)

    candidates = _find_nivus_xml_files(
        cfg,
        config_path=config_path,
    )

    print(f"Found Nivus XML files: {len(candidates)}")

    if not candidates:
        print("No Nivus XML files found with current config search settings.")
        print(
            "Expected Nivus raw directory: "
            f"{_get_nivus_raw_root(cfg, config_path=config_path)}"
        )
        print(f"Run created: {run_dir}")
        return run_dir

    timezone = _get_timezone(cfg)

    processed = 0
    failed: list[tuple[str, str]] = []

    for item in candidates:
        xml_path = item["xml_path"]

        try:
            _process_xml_file(
                item,
                group_dirs=group_dirs,
                timezone=timezone,
                run_dir=run_dir,
            )
            processed += 1

        except Exception as exc:
            print(f"ERROR processing {xml_path}: {exc}")
            failed.append((xml_path, str(exc)))

    print(f"Processed OK: {processed}/{len(candidates)}")

    if failed:
        print("Failed Nivus XML files:")
        for path, error in failed:
            print(f" - {path}: {error}")

    print(f"Run created: {run_dir}")
    return run_dir