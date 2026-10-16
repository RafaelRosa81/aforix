from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from aforix.config.loader import load_config
from aforix.config.paths import config_root_from_path
from aforix.ingest.adapters.m9_mat import parse_m9_mat
from aforix.ingest.discovery import fallback_station_id_from_parents, find_files_recursive
from aforix.ingest.metadata import clean_station_id, clean_station_name
from aforix.runs.manager import create_run


INSTRUMENT_NAME = "m9"
GROUPS = ("Summary", "Points")


def _resolve_path(value: str | Path, *, project_root: Path) -> Path:
    path = Path(value)
    return (path if path.is_absolute() else project_root / path).resolve()


def _get_m9_raw_root(cfg: dict[str, Any], *, config_path: Path) -> Path:
    try:
        raw_root = _resolve_path(cfg["paths"]["raw_data_dir"], project_root=config_root_from_path(config_path))
        raw_subdir = cfg["ingest"][INSTRUMENT_NAME]["raw_subdir"]
    except KeyError as exc:
        raise ValueError(f"Missing M9 ingest configuration key: {exc}") from exc
    root = raw_root / str(raw_subdir)
    if not root.exists() or not root.is_dir():
        raise ValueError(f"M9 raw data directory does not exist or is not a directory: {root}")
    return root.resolve()


def _prepare_output_dirs(run_dir: Path) -> dict[str, Path]:
    root = run_dir / "outputs" / "raw_canonical" / INSTRUMENT_NAME
    result = {group: root / group for group in GROUPS}
    for directory in result.values():
        directory.mkdir(parents=True, exist_ok=True)
    return result


def _station_id(value: Any, fallback: str | None) -> str:
    text = str(value or "").strip()
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    return clean_station_id(text or None, fallback=fallback)


def _add_metadata(row: dict[str, Any], *, metadata: dict[str, Any]) -> dict[str, Any]:
    return {**metadata, **row}


def _write_rows(rows: list[dict[str, Any]], *, path: Path) -> None:
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def run(config_path: Path) -> Path:
    """Ingest RiverSurveyor Live Matlab exports (.mat) for the M9."""
    config_path = Path(config_path).resolve()
    cfg = load_config(config_path)
    try:
        m9_cfg = cfg["ingest"][INSTRUMENT_NAME]
    except KeyError as exc:
        raise ValueError("Missing M9 configuration section: 'ingest.m9'.") from exc

    run_dir = create_run("ingest_m9", config_path)
    if m9_cfg.get("enabled") is False:
        print("M9 ingest is disabled in config.")
        return run_dir

    raw_root = _get_m9_raw_root(cfg, config_path=config_path)
    candidates = find_files_recursive(raw_root, {".mat"})
    print(f"Found RiverSurveyor Live MAT files: {len(candidates)}")
    output_dirs = _prepare_output_dirs(run_dir)
    timezone = str(cfg.get("project", {}).get("timezone", "America/Montevideo"))
    succeeded = 0
    failed: list[tuple[Path, str]] = []
    used_output_names = {group: set() for group in GROUPS}

    for source_path in candidates:
        try:
            parsed = parse_m9_mat(source_path, timezone_name=timezone)
            summary = parsed["summary"]
            start_dt = summary["measurement_start"]
            end_dt = summary["measurement_end"]
            station_id = _station_id(
                summary.get("station_id"), fallback_station_id_from_parents(source_path)
            )
            station_name = clean_station_name(summary.get("station_name"))
            metadata = {
                "station_id": station_id,
                "station_name": station_name,
                "measurement_date": start_dt.strftime("%Y%m%d"),
                "measurement_time": start_dt.strftime("%H%M%S"),
                "instrument": INSTRUMENT_NAME,
                "source_file": str(source_path.resolve()),
                "input_file": source_path.name,
                "input_path": str(source_path.resolve()),
                "source_run_dir": str(run_dir),
                "run_id": run_dir.name,
                "timezone": timezone,
            }
            summary_row = _add_metadata(
                {
                    key: value
                    for key, value in summary.items()
                    if key not in {"measurement_start", "measurement_end", "station_id", "station_name"}
                },
                metadata=metadata,
            )
            summary_row["manufacturer"] = "SonTek"
            summary_row["model"] = "M9"
            summary_row["measurement_end_date"] = end_dt.strftime("%Y%m%d")
            summary_row["measurement_end_time"] = end_dt.strftime("%H%M%S")

            # The same station and timestamp can appear in paired .mat and r.mat
            # exports. Include the input stem so each transect gets its own
            # Summary and Points files rather than overwriting an earlier one.
            source_stem = source_path.stem
            name_stem = (
                f"{station_id}_{metadata['measurement_date']}_"
                f"{metadata['measurement_time']}_{source_stem}"
            )
            summary_name = f"{name_stem}_Summary.csv"
            points_name = f"{name_stem}_Points.csv"
            if (
                summary_name in used_output_names["Summary"]
                or points_name in used_output_names["Points"]
            ):
                source_hash = hashlib.sha256(
                    str(source_path.resolve()).encode("utf-8")
                ).hexdigest()[:10]
                name_stem = f"{name_stem}_{source_hash}"
                summary_name = f"{name_stem}_Summary.csv"
                points_name = f"{name_stem}_Points.csv"
            used_output_names["Summary"].add(summary_name)
            used_output_names["Points"].add(points_name)
            _write_rows([summary_row], path=output_dirs["Summary"] / summary_name)
            point_rows = [_add_metadata(row, metadata=metadata) for row in parsed["points"]]
            _write_rows(point_rows, path=output_dirs["Points"] / points_name)
            print(f"Saved M9 transect: {source_path.name} ({len(point_rows)} samples)")
            succeeded += 1
        except Exception as exc:
            print(f"ERROR processing {source_path}: {exc}")
            failed.append((source_path, str(exc)))

    print(f"Processed OK: {succeeded}/{len(candidates)}")
    if failed:
        print("Failed M9 MAT files:")
        for path, error in failed:
            print(f" - {path}: {error}")
    (run_dir / "ingest_status.json").write_text(
        json.dumps({"files_found": len(candidates), "succeeded": succeeded,
                    "failed": [{"file": str(path), "error": error} for path, error in failed]},
                   ensure_ascii=False, indent=2), encoding="utf-8",
    )
    if failed:
        raise RuntimeError(f"M9 ingestion incomplete: {len(failed)} file(s) failed; see {run_dir / 'ingest_status.json'}")
    print(f"Run created: {run_dir}")
    return run_dir
