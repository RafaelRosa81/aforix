from __future__ import annotations

from pathlib import Path
from typing import Any

from aforix.config.loader import load_config
from aforix.runs.manager import create_run
from aforix.ingest.adapters.molinete_excel import MolineteExcelAdapter
from aforix.ingest.discovery import (
    fallback_station_id_from_parents,
    find_files_recursive,
)
from aforix.ingest.metadata import clean_station_id, clean_station_name


INSTRUMENT_NAME = "molinete"
EXCEL_EXTENSIONS = {".xls", ".xlsx", ".xlsm"}


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


def _get_molinete_config(cfg: dict[str, Any]) -> dict[str, Any]:
    try:
        return cfg["ingest"][INSTRUMENT_NAME]
    except KeyError as exc:
        raise ValueError(
            "Missing Molinete configuration section: 'ingest.molinete'."
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
        raise ValueError("Missing required config key: 'paths.raw_data_dir'.") from exc

    return _resolve_config_path(raw_data_dir, project_root=project_root)


def _get_molinete_raw_root(
    cfg: dict[str, Any],
    *,
    config_path: Path,
) -> Path:
    raw_data_root = _get_raw_data_root(cfg, config_path=config_path)
    molinete_cfg = _get_molinete_config(cfg)

    raw_subdir = molinete_cfg.get("raw_subdir")

    if not raw_subdir:
        raise ValueError("Missing required config key: 'ingest.molinete.raw_subdir'.")

    molinete_root = raw_data_root / str(raw_subdir)

    if not molinete_root.exists():
        raise ValueError(f"Molinete raw data directory does not exist: {molinete_root}")

    if not molinete_root.is_dir():
        raise ValueError(f"Molinete raw data path is not a directory: {molinete_root}")

    return molinete_root.resolve()


def _find_molinete_excels(
    cfg: dict[str, Any],
    *,
    config_path: Path,
) -> list[dict[str, str]]:
    molinete_root = _get_molinete_raw_root(cfg, config_path=config_path)

    candidates: list[dict[str, str]] = []

    for file_path in find_files_recursive(molinete_root, EXCEL_EXTENSIONS):
        candidates.append(
            {
                "xls_file": file_path.name,
                "xls_path": str(file_path),
                "fallback_station_id": fallback_station_id_from_parents(file_path) or "",
            }
        )

    return candidates


def _format_date_yyyymmdd(value: Any) -> str:
    if value is None or value == "":
        return "00000000"

    return str(value).replace("-", "").replace("/", "").strip()


def _format_time_hhmmss(value: Any) -> str:
    if value is None or value == "":
        return "000000"

    return str(value).replace(":", "").strip()


def _prepare_output_dirs(run_dir: Path) -> dict[str, Path]:
    outdir_root = run_dir / "outputs" / "raw_canonical" / INSTRUMENT_NAME

    group_dirs = {
        group: outdir_root / group
        for group in ["Summary", "Points"]
    }

    for group_dir in group_dirs.values():
        group_dir.mkdir(parents=True, exist_ok=True)

    return group_dirs


def _get_sheet_name(cfg: dict[str, Any]) -> str:
    molinete_cfg = _get_molinete_config(cfg)
    sheet_name = molinete_cfg.get("sheet_name", "CALCULO")

    if not isinstance(sheet_name, str) or not sheet_name.strip():
        raise ValueError("'ingest.molinete.sheet_name' must be a non-empty string.")

    return sheet_name.strip()


def _add_ingest_metadata(
    df,
    *,
    station_id: str,
    station_name: str | None,
    source_path: Path,
    run_dir: Path,
):
    df = df.copy()

    df["station_id"] = station_id
    df["station_name"] = station_name
    df["instrument"] = INSTRUMENT_NAME
    df["source_file"] = str(source_path)
    df["source_run_dir"] = str(run_dir)

    return df


def _write_group_csv(
    df,
    *,
    group_name: str,
    output_dir: Path,
    station_id: str,
    station_name: str | None,
    measurement_date: str,
    measurement_time: str,
    source_path: Path,
    run_dir: Path,
) -> Path | None:
    if df is None:
        return None

    df = df.drop(columns=["extras_json"], errors="ignore")

    if df.empty:
        return None

    df = _add_ingest_metadata(
        df,
        station_id=station_id,
        station_name=station_name,
        source_path=source_path,
        run_dir=run_dir,
    )

    output_path = (
        output_dir
        / f"{station_id}_{group_name}_{measurement_date}_{measurement_time}.csv"
    )

    df.to_csv(output_path, index=False)
    return output_path


def _process_excel_file(
    item: dict[str, str],
    *,
    adapter: MolineteExcelAdapter,
    sheet_name: str,
    group_dirs: dict[str, Path],
    run_dir: Path,
) -> None:
    xls_path = Path(item["xls_path"])

    res = adapter.parse_file_strict(
        str(xls_path),
        sheet_name=sheet_name,
    )

    station_id = clean_station_id(
        res.extracted_meta.get("station_id"),
        fallback=item.get("fallback_station_id"),
    )

    station_name = clean_station_name(
        res.extracted_meta.get("station_name")
    )

    measurement_date = _format_date_yyyymmdd(
        res.extracted_meta.get("measurement_date", "")
    )
    measurement_time = _format_time_hhmmss(
        res.extracted_meta.get("measurement_time", "")
    )

    summary_outpath = _write_group_csv(
        res.raw_groups.get("Summary"),
        group_name="Summary",
        output_dir=group_dirs["Summary"],
        station_id=station_id,
        station_name=station_name,
        measurement_date=measurement_date,
        measurement_time=measurement_time,
        source_path=xls_path,
        run_dir=run_dir,
    )

    if summary_outpath is not None:
        print(f"Saved: {summary_outpath}")

    points_outpath = _write_group_csv(
        res.raw_groups.get("Points"),
        group_name="Points",
        output_dir=group_dirs["Points"],
        station_id=station_id,
        station_name=station_name,
        measurement_date=measurement_date,
        measurement_time=measurement_time,
        source_path=xls_path,
        run_dir=run_dir,
    )

    if points_outpath is not None:
        print(f"Saved: {points_outpath}")


def run(config_path: Path) -> Path:
    """Run Molinete ingest pipeline."""

    config_path = Path(config_path).resolve()
    cfg = load_config(config_path)

    molinete_cfg = _get_molinete_config(cfg)

    if molinete_cfg.get("enabled") is False:
        print("Molinete ingest is disabled in config.")
        return create_run("ingest_molinete", config_path)

    run_dir = create_run("ingest_molinete", config_path)
    group_dirs = _prepare_output_dirs(run_dir)

    adapter = MolineteExcelAdapter()
    sheet_name = _get_sheet_name(cfg)

    candidates = _find_molinete_excels(
        cfg,
        config_path=config_path,
    )

    print(f"Found Molinete Excel files: {len(candidates)}")

    if not candidates:
        print("No Molinete Excel files found.")
        print(
            "Expected Molinete raw directory: "
            f"{_get_molinete_raw_root(cfg, config_path=config_path)}"
        )
        print(f"Run created: {run_dir}")
        return run_dir

    processed = 0
    failed: list[tuple[str, str]] = []

    for item in candidates:
        xls_path = item["xls_path"]

        try:
            _process_excel_file(
                item,
                adapter=adapter,
                sheet_name=sheet_name,
                group_dirs=group_dirs,
                run_dir=run_dir,
            )
            processed += 1

        except Exception as exc:
            print(f"ERROR processing {xls_path}: {exc}")
            failed.append((xls_path, str(exc)))

    print(f"Processed OK: {processed}/{len(candidates)}")

    if failed:
        print("Failed Molinete files:")
        for path, error in failed:
            print(f" - {path}: {error}")

    print(f"Run created: {run_dir}")

    return run_dir