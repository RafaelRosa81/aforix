from pathlib import Path
import re
import yaml

from aforix.config.loader import load_config
from aforix.runs.manager import create_run
from aforix.ingest.adapters.nivus_xml import (
    parse_nivus_xml,
    parse_datetime_from_filename,
)
from aforix.canonical.normalizer import Normalizer, SourceMeta


def _find_nivus_xml_files(config: dict) -> list[dict]:
    raw_data_root = Path(config["raw_data_path_dir"])
    stage1_keyword = config["subfolder_raw_data_word_dir"]
    stage2_foldername = config["subsubfolder_raw_data_word_dir_NIV"]

    candidates = []

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


def run(config_path: Path) -> Path:
    """Run Nivus XML ingest pipeline."""

    cfg = load_config(config_path)
    run_dir = create_run("ingest_nivus", config_path)

    registry_path = Path(cfg["registry_path"])

    outdir_root = run_dir / "outputs" / "raw_canonical" / "nivus"

    group_dirs = {
        group: outdir_root / group
        for group in ["Summary", "Points", "Sections", "Gates"]
    }

    for group_dir in group_dirs.values():
        group_dir.mkdir(parents=True, exist_ok=True)

    with open(registry_path, "r", encoding="utf-8") as f:
        registry = yaml.safe_load(f) or {}

    normalizer = Normalizer(registry)

    candidates = _find_nivus_xml_files(cfg)

    print(f"Found Nivus XML files: {len(candidates)}")

    if not candidates:
        print("No Nivus XML files found with current config search settings.")
        print(f"Run created: {run_dir}")
        return run_dir

    processed = 0
    failed = []

    for item in candidates:
        xml_path = item["xml_path"]
        station_id = item["point_folder"].upper()

        try:
            raw_groups = parse_nivus_xml(xml_path)
            measurement_date, measurement_time = parse_datetime_from_filename(
                Path(xml_path).name
            )

            meta = SourceMeta(
                source="nivus",
                station_id=station_id,
                measurement_date=measurement_date,
                measurement_time=measurement_time,
                timezone=cfg.get("timezone", "America/Montevideo"),
                input_file=Path(xml_path).name,
                input_path=str(Path(xml_path).resolve()),
                run_id=run_dir.name,
            )

            dfs = normalizer.normalize_measurement(raw_groups, meta)

            for group, df in dfs.items():
                outpath = (
                    group_dirs[group]
                    / f"{meta.station_id}_{group}_{meta.measurement_date}_{meta.measurement_time}.csv"
                )
                df.to_csv(outpath, index=False)
                print(f"Saved: {outpath}")

            processed += 1

        except Exception as e:
            print(f"ERROR processing {xml_path}: {e}")
            failed.append(xml_path)

    print(f"Processed OK: {processed}/{len(candidates)}")

    if failed:
        print("Failed Nivus XML files:")
        for f in failed:
            print(f" - {f}")

    print(f"Run created: {run_dir}")

    return run_dir