from pathlib import Path
import re
import pandas as pd

from aforix.config.loader import load_config
from aforix.runs.manager import create_run
from aforix.ingest.adapters.nivus_xml import (
    parse_nivus_xml,
    parse_datetime_from_filename,
)


GROUPS = ["Summary", "Points", "Sections", "Gates"]


def _find_nivus_xml_files(config: dict) -> list[dict]:
    raw_data_root = Path(config["raw_data_path_dir"])
    stage1_keyword = config["subfolder_raw_data_word_dir"]
    stage2_foldername = config["subsubfolder_raw_data_word_dir_NIV"]

    candidates: list[dict] = []

    for folder in raw_data_root.iterdir():
        if not folder.is_dir():
            continue

        if not re.match(rf"\d{{8}}_{re.escape(stage1_keyword)}_\d+", folder.name):
            continue

        stage2_path = folder / stage2_foldername
        if not stage2_path.is_dir():
            continue

        for point_path in stage2_path.iterdir():
            if not point_path.is_dir():
                continue

            if not re.match(r"P\d+", point_path.name, flags=re.IGNORECASE):
                continue

            xml_files = sorted(point_path.glob("*.xml"))

            if len(xml_files) != 1:
                print(
                    f"WARNING: {point_path}: expected 1 XML file, "
                    f"found {len(xml_files)}. Skipping."
                )
                continue

            xml_path = xml_files[0]

            candidates.append(
                {
                    "campaign_folder": folder.name,
                    "point_folder": point_path.name,
                    "point_path": str(point_path),
                    "xml_file": xml_path.name,
                    "xml_path": str(xml_path),
                }
            )

    return candidates


def _rows_to_dataframe(rows: list[dict]) -> pd.DataFrame:
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
    measurement_date: str,
    measurement_time: str,
    timezone: str,
    input_file: str,
    input_path: str,
    run_id: str,
) -> pd.DataFrame:
    """Add minimal ingest metadata to every output table."""
    metadata = {
        "source": source,
        "station_id": station_id,
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


def run(config_path: Path) -> Path:
    """Run clean raw Nivus XML ingest pipeline.

    This stage does NOT call the Aforix Normalizer and does NOT use registry.
    It only extracts all available XML data into clean CSV tables.
    """
    cfg = load_config(config_path)
    run_dir = create_run("ingest_nivus", config_path)

    # Keep the existing output convention if the rest of the project expects it.
    # If you prefer a more explicit name, change raw_canonical -> raw_clean here.
    outdir_root = run_dir / "outputs" / "raw_canonical" / "nivus"

    group_dirs = {group: outdir_root / group for group in GROUPS}

    for group_dir in group_dirs.values():
        group_dir.mkdir(parents=True, exist_ok=True)

    candidates = _find_nivus_xml_files(cfg)

    print(f"Found Nivus XML files: {len(candidates)}")

    if not candidates:
        print("No Nivus XML files found with current config search settings.")
        print(f"Run created: {run_dir}")
        return run_dir

    processed = 0
    failed: list[str] = []

    for item in candidates:
        xml_path = Path(item["xml_path"])
        station_id = item["point_folder"].upper()

        try:
            raw_groups = parse_nivus_xml(xml_path)
            measurement_date, measurement_time = parse_datetime_from_filename(xml_path.name)

            for group in GROUPS:
                rows = raw_groups.get(group, [])
                df = _rows_to_dataframe(rows)

                df = _add_ingest_metadata(
                    df,
                    source="nivus",
                    station_id=station_id,
                    measurement_date=measurement_date,
                    measurement_time=measurement_time,
                    timezone=cfg.get("timezone", "America/Montevideo"),
                    input_file=xml_path.name,
                    input_path=str(xml_path.resolve()),
                    run_id=run_dir.name,
                )

                outpath = (
                    group_dirs[group]
                    / f"{station_id}_{group}_{measurement_date}_{measurement_time}.csv"
                )
                df.to_csv(outpath, index=False, encoding="utf-8-sig")
                print(f"Saved: {outpath}")

            processed += 1

        except Exception as e:
            print(f"ERROR processing {xml_path}: {e}")
            failed.append(str(xml_path))

    print(f"Processed OK: {processed}/{len(candidates)}")

    if failed:
        print("Failed Nivus XML files:")
        for f in failed:
            print(f" - {f}")

    print(f"Run created: {run_dir}")
    return run_dir
