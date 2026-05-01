from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import pandas as pd

from aforix.config.loader import load_config
from aforix.runs.manager import create_run


DEFAULT_GROUPS = ["Summary", "Points", "Sections", "Gates"]
DEFAULT_CONCAT_GROUPS = ["Summary"]

TRACEABILITY_COLUMNS = [
    "station_id",
    "station_name",
    "measurement_date",
    "measurement_time",
    "instrument",
    "source_file",
    "source_run_dir",
    "run_id",
]


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


def _get_enabled_instruments(cfg: dict[str, Any]) -> list[str]:
    ingest_cfg = cfg.get("ingest", {})

    if not isinstance(ingest_cfg, dict):
        raise ValueError("Config section 'ingest' must be a dictionary.")

    instruments: list[str] = []

    for instrument, instrument_cfg in ingest_cfg.items():
        if not isinstance(instrument_cfg, dict):
            continue

        if instrument_cfg.get("enabled") is False:
            continue

        instruments.append(str(instrument))

    return sorted(instruments)


def _get_build_sources(cfg: dict[str, Any]) -> list[str]:
    build_cfg = cfg.get("build_groups", {})
    configured_sources = build_cfg.get("sources")
    enabled_instruments = _get_enabled_instruments(cfg)

    if configured_sources is None:
        return enabled_instruments

    if not isinstance(configured_sources, list):
        raise ValueError("'build_groups.sources' must be a list.")

    sources = [str(item) for item in configured_sources]

    unknown = sorted(set(sources) - set(enabled_instruments))
    if unknown:
        raise ValueError(
            "build_groups.sources contains instruments that are not enabled "
            f"in ingest config: {unknown}"
        )

    return sorted(sources)


def _get_build_groups(cfg: dict[str, Any]) -> list[str]:
    build_cfg = cfg.get("build_groups", {})
    groups = build_cfg.get("groups", DEFAULT_GROUPS)

    if not isinstance(groups, list):
        raise ValueError("'build_groups.groups' must be a list.")

    groups = [str(group).strip() for group in groups if str(group).strip()]

    if not groups:
        raise ValueError("'build_groups.groups' cannot be empty.")

    return groups


def _get_concat_groups(cfg: dict[str, Any]) -> set[str]:
    build_cfg = cfg.get("build_groups", {})
    concat_groups = build_cfg.get("concat_groups", DEFAULT_CONCAT_GROUPS)

    if not isinstance(concat_groups, list):
        raise ValueError("'build_groups.concat_groups' must be a list.")

    return {str(group).strip() for group in concat_groups if str(group).strip()}


def _get_column_aliases(cfg: dict[str, Any]) -> dict[str, Any]:
    build_cfg = cfg.get("build_groups", {})
    aliases = build_cfg.get("column_aliases", {})

    if aliases is None:
        return {}

    if not isinstance(aliases, dict):
        raise ValueError("'build_groups.column_aliases' must be a mapping/dictionary.")

    return aliases


def _get_runs_root(cfg: dict[str, Any], *, config_path: Path) -> Path:
    project_root = _get_project_root(config_path)

    build_cfg = cfg.get("build_groups", {})

    runs_root_value = (
        build_cfg.get("input_runs_root")
        or cfg.get("paths", {}).get("runs_root")
        or "runs"
    )

    return _resolve_config_path(runs_root_value, project_root=project_root)


def _get_output_dir(cfg: dict[str, Any], *, config_path: Path) -> Path:
    project_root = _get_project_root(config_path)

    output_dir_value = (
        cfg.get("build_groups", {}).get("output_dir")
        or "database/raw_canonical"
    )

    return _resolve_config_path(output_dir_value, project_root=project_root)


def _parse_run_timestamp(run_dir: Path) -> str:
    if re.match(r"^\d{8}_\d{6}$", run_dir.name):
        return run_dir.name

    return ""


def _find_ingest_run_dirs(runs_root: Path) -> list[Path]:
    if not runs_root.exists():
        raise ValueError(f"Runs root does not exist: {runs_root}")

    if not runs_root.is_dir():
        raise ValueError(f"Runs root is not a directory: {runs_root}")

    run_dirs: list[Path] = []

    for ingest_root in sorted(runs_root.glob("ingest_*")):
        if not ingest_root.is_dir():
            continue

        for run_dir in sorted(ingest_root.iterdir()):
            if not run_dir.is_dir():
                continue

            if (run_dir / "outputs" / "raw_canonical").exists():
                run_dirs.append(run_dir)

    return run_dirs


def _find_group_csvs(
    run_dirs: list[Path],
    *,
    instrument: str,
    group: str,
) -> list[Path]:
    csvs: list[Path] = []

    for run_dir in run_dirs:
        group_dir = run_dir / "outputs" / "raw_canonical" / instrument / group

        if not group_dir.exists():
            continue

        csvs.extend(sorted(group_dir.glob("*.csv")))

    return csvs


def _run_dir_from_group_csv(csv_path: Path) -> Path:
    parts = csv_path.resolve().parts

    for idx, part in enumerate(parts):
        if part == "outputs" and idx >= 1:
            return Path(*parts[:idx])

    return csv_path.parent


def _deduplicate_by_filename_keep_latest(csv_paths: list[Path]) -> list[Path]:
    selected: dict[str, Path] = {}

    for csv_path in csv_paths:
        filename = csv_path.name

        if filename not in selected:
            selected[filename] = csv_path
            continue

        current = selected[filename]

        current_run = _run_dir_from_group_csv(current)
        candidate_run = _run_dir_from_group_csv(csv_path)

        current_ts = _parse_run_timestamp(current_run)
        candidate_ts = _parse_run_timestamp(candidate_run)

        if candidate_ts >= current_ts:
            selected[filename] = csv_path

    return [selected[name] for name in sorted(selected)]


def _infer_metadata_from_filename(
    csv_path: Path,
    *,
    group: str,
) -> dict[str, str]:
    stem = csv_path.stem

    pattern = (
        rf"^(?P<station_id>.+)_"
        rf"{re.escape(group)}_"
        rf"(?P<date>\d{{8}})_"
        rf"(?P<time>\d{{6}})$"
    )

    match = re.match(pattern, stem)

    if not match:
        return {
            "station_id": "",
            "measurement_date": "",
            "measurement_time": "",
        }

    return {
        "station_id": match.group("station_id"),
        "measurement_date": match.group("date"),
        "measurement_time": match.group("time"),
    }


def _first_existing_value(
    df: pd.DataFrame,
    columns: list[str],
    default: str = "",
) -> str:
    for col in columns:
        if col not in df.columns:
            continue

        values = df[col].dropna().astype(str).str.strip()
        values = values[values != ""]

        if not values.empty:
            return str(values.iloc[0])

    return str(default)


def _normalize_alias_mapping(raw_mapping: Any) -> dict[str, str]:
    """
    Normalize one alias mapping into {old_column: canonical_column}.

    Supports:
      old_col: new_col

    Example:
      caudal_total_m3_s: total_discharge_m3_s
    """

    if raw_mapping is None:
        return {}

    if not isinstance(raw_mapping, dict):
        raise ValueError("Column alias mapping must be a dictionary.")

    normalized: dict[str, str] = {}

    for old_col, new_col in raw_mapping.items():
        old = str(old_col).strip()
        new = str(new_col).strip()

        if not old or not new:
            raise ValueError("Column aliases must map non-empty strings.")

        normalized[old] = new

    return normalized


def _get_alias_mapping_for(
    column_aliases: dict[str, Any],
    *,
    instrument: str,
    group: str,
) -> dict[str, str]:
    """
    Get aliases for a specific instrument/group.

    Supported YAML shape:
      build_groups:
        column_aliases:
          flowtracker:
            Summary:
              old_col: new_col
            Points:
              old_col: new_col

    Optional generic aliases:
      build_groups:
        column_aliases:
          "*":
            Summary:
              old_col: new_col
    """

    combined: dict[str, str] = {}

    for instrument_key in ("*", instrument):
        instrument_aliases = column_aliases.get(instrument_key, {})

        if instrument_aliases is None:
            continue

        if not isinstance(instrument_aliases, dict):
            raise ValueError(
                f"'build_groups.column_aliases.{instrument_key}' must be a dictionary."
            )

        generic_group_aliases = _normalize_alias_mapping(
            instrument_aliases.get("*", {})
        )
        group_aliases = _normalize_alias_mapping(
            instrument_aliases.get(group, {})
        )

        combined.update(generic_group_aliases)
        combined.update(group_aliases)

    return combined


def _apply_column_aliases(
    df: pd.DataFrame,
    *,
    instrument: str,
    group: str,
    column_aliases: dict[str, Any],
) -> pd.DataFrame:
    aliases = _get_alias_mapping_for(
        column_aliases,
        instrument=instrument,
        group=group,
    )

    if not aliases:
        return df.copy()

    df = df.copy()

    for old_col, new_col in aliases.items():
        if old_col not in df.columns:
            continue

        if new_col not in df.columns:
            df[new_col] = df[old_col]
        else:
            current = df[new_col].replace("", pd.NA)
            incoming = df[old_col].replace("", pd.NA)
            df[new_col] = current.combine_first(incoming)

        if old_col != new_col:
            df = df.drop(columns=[old_col])

    return df


def _ensure_traceability_columns(
    df: pd.DataFrame,
    *,
    csv_path: Path,
    instrument: str,
    group: str,
) -> pd.DataFrame:
    df = df.copy()

    run_dir = _run_dir_from_group_csv(csv_path)
    inferred = _infer_metadata_from_filename(csv_path, group=group)

    defaults = {
        "station_id": _first_existing_value(
            df,
            ["station_id", "estacion_num", "ref", "ref val"],
            inferred["station_id"],
        ),
        "station_name": _first_existing_value(
            df,
            ["station_name", "nombre", "name", "name val", "site_name"],
            "",
        ),
        "measurement_date": _first_existing_value(
            df,
            ["measurement_date", "fecha"],
            inferred["measurement_date"],
        ),
        "measurement_time": _first_existing_value(
            df,
            ["measurement_time", "hora_ini", "start_time", "timestamp_time"],
            inferred["measurement_time"],
        ),
        "instrument": instrument,
        "source_file": _first_existing_value(
            df,
            ["source_file", "source_csv", "input_path", "raw_source_file"],
            str(csv_path.resolve()),
        ),
        "source_run_dir": _first_existing_value(
            df,
            ["source_run_dir"],
            str(run_dir),
        ),
        "run_id": _first_existing_value(
            df,
            ["run_id"],
            run_dir.name,
        ),
    }

    for col in TRACEABILITY_COLUMNS:
        value = str(defaults.get(col, ""))

        if col not in df.columns:
            df[col] = value
        else:
            df[col] = df[col].fillna("").astype(str)
            empty_mask = df[col].str.strip() == ""
            df.loc[empty_mask, col] = value

    remaining_columns = [col for col in df.columns if col not in TRACEABILITY_COLUMNS]
    return df[TRACEABILITY_COLUMNS + remaining_columns]


def _read_csv_with_traceability(
    csv_path: Path,
    *,
    instrument: str,
    group: str,
    column_aliases: dict[str, Any],
) -> pd.DataFrame:
    df = pd.read_csv(csv_path, dtype=str)

    if df.empty:
        return df

    df = _apply_column_aliases(
        df,
        instrument=instrument,
        group=group,
        column_aliases=column_aliases,
    )

    return _ensure_traceability_columns(
        df,
        csv_path=csv_path,
        instrument=instrument,
        group=group,
    )


def _build_concat_group(
    csv_paths: list[Path],
    *,
    instrument: str,
    group: str,
    output_root: Path,
    column_aliases: dict[str, Any],
) -> None:
    frames: list[pd.DataFrame] = []

    for csv_path in csv_paths:
        try:
            df = _read_csv_with_traceability(
                csv_path,
                instrument=instrument,
                group=group,
                column_aliases=column_aliases,
            )

            if not df.empty:
                frames.append(df)

        except Exception as exc:
            print(f"WARNING: could not read {csv_path}: {exc}")

    if not frames:
        print(f"{instrument}/{group}: no data")
        return

    outdir = output_root / instrument
    outdir.mkdir(parents=True, exist_ok=True)

    outpath = outdir / f"{group}.csv"

    merged = pd.concat(frames, ignore_index=True, sort=False)

    remaining_columns = [col for col in merged.columns if col not in TRACEABILITY_COLUMNS]
    merged = merged[TRACEABILITY_COLUMNS + remaining_columns]

    merged.to_csv(outpath, index=False)

    print(f"{instrument}/{group}: {len(merged)} rows -> {outpath}")


def _build_file_group(
    csv_paths: list[Path],
    *,
    instrument: str,
    group: str,
    output_root: Path,
    column_aliases: dict[str, Any],
) -> None:
    outdir = output_root / instrument / group
    outdir.mkdir(parents=True, exist_ok=True)

    saved = 0

    for csv_path in csv_paths:
        try:
            df = _read_csv_with_traceability(
                csv_path,
                instrument=instrument,
                group=group,
                column_aliases=column_aliases,
            )

            if df.empty:
                continue

            outpath = outdir / csv_path.name
            df.to_csv(outpath, index=False)
            saved += 1

        except Exception as exc:
            print(f"WARNING: could not process {csv_path}: {exc}")

    print(f"{instrument}/{group}: {saved} files -> {outdir}")


def run(config_path: Path) -> Path:
    """Build grouped datasets from ingest raw_canonical outputs."""

    config_path = Path(config_path).resolve()
    cfg = load_config(config_path)

    build_cfg = cfg.get("build_groups", {})

    if build_cfg.get("enabled") is False:
        print("build-groups is disabled in config.")
        return create_run("build_groups", config_path)

    run_dir = create_run("build_groups", config_path)

    runs_root = _get_runs_root(cfg, config_path=config_path)
    output_root = _get_output_dir(cfg, config_path=config_path)
    instruments = _get_build_sources(cfg)
    groups = _get_build_groups(cfg)
    concat_groups = _get_concat_groups(cfg)
    column_aliases = _get_column_aliases(cfg)

    output_root.mkdir(parents=True, exist_ok=True)

    print("Building raw_canonical grouped database")
    print(f"Runs root: {runs_root}")
    print(f"Output root: {output_root}")
    print(f"Instruments: {instruments}")
    print(f"Groups: {groups}")
    print(f"Concat groups: {sorted(concat_groups)}")
    print(f"Column aliases configured: {bool(column_aliases)}")

    ingest_run_dirs = _find_ingest_run_dirs(runs_root)

    if not ingest_run_dirs:
        print("No ingest runs found.")
        print(f"Run created: {run_dir}")
        return run_dir

    for instrument in instruments:
        for group in groups:
            csv_paths = _find_group_csvs(
                ingest_run_dirs,
                instrument=instrument,
                group=group,
            )

            unique_csvs = _deduplicate_by_filename_keep_latest(csv_paths)

            if not unique_csvs:
                print(f"{instrument}/{group}: no CSV files")
                continue

            if group in concat_groups:
                _build_concat_group(
                    unique_csvs,
                    instrument=instrument,
                    group=group,
                    output_root=output_root,
                    column_aliases=column_aliases,
                )
            else:
                _build_file_group(
                    unique_csvs,
                    instrument=instrument,
                    group=group,
                    output_root=output_root,
                    column_aliases=column_aliases,
                )

    print(f"Run created: {run_dir}")

    return run_dir