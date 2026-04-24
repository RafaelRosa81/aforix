from pathlib import Path
import re
import yaml

from aforix.config.loader import load_config
from aforix.runs.manager import create_run
from aforix.ingest.adapters.flowtracker_dis import FlowTrackerDISAdapter
from aforix.canonical.normalizer import Normalizer, SourceMeta


def _station_id_from_point_folder(point_folder: str) -> str:
    m = re.match(r"^(P\d{1,3})$", point_folder.strip(), flags=re.IGNORECASE)
    return m.group(1).upper() if m else "UNKNOWN"


def _find_dis_files_flowtracker(config: dict) -> list[dict]:
    raw_data_root = Path(config["raw_data_path_dir"])
    stage1_keyword = config["subfolder_raw_data_word_dir"]
    stage2_foldername = config["subsubfolder_raw_data_word_dir_FT"]

    candidates = []

    for folder in raw_data_root.iterdir():
        if not folder.is_dir():
            continue

        if not re.match(rf"\d{{8}}_{re.escape(stage1_keyword)}_\d+", folder.name):
            continue

        stage1_path = folder / stage2_foldername
        if not stage1_path.is_dir():
            continue

        for point_path in stage1_path.iterdir():
            if not point_path.is_dir():
                continue

            if not re.match(r"P\d+", point_path.name, flags=re.IGNORECASE):
                continue

            for dis_path in point_path.glob("*.dis"):
                candidates.append(
                    {
                        "campaign_folder": folder.name,
                        "point_folder": point_path.name,
                        "point_path": str(point_path),
                        "dis_file": dis_path.name,
                        "dis_path": str(dis_path),
                    }
                )

    return candidates


def run(config_path: Path) -> Path:
    """Run FlowTracker ingest pipeline."""

    cfg = load_config(config_path)
    run_dir = create_run("ingest_flowtracker", config_path)

    spec_path = Path(cfg["flowtracker_spec_path"])
    registry_path = Path(cfg["registry_path"])

    outdir_root = run_dir / "outputs" / "raw_canonical" / "flowtracker"

    group_dirs = {
        group: outdir_root / group
        for group in ["Summary", "Points", "Sections", "Gates"]
    }

    for group_dir in group_dirs.values():
        group_dir.mkdir(parents=True, exist_ok=True)

    with open(registry_path, "r", encoding="utf-8") as f:
        registry = yaml.safe_load(f) or {}

    normalizer = Normalizer(registry)
    adapter = FlowTrackerDISAdapter()

    candidates = _find_dis_files_flowtracker(cfg)

    print(f"Found .dis files: {len(candidates)}")

    if not candidates:
        print("No .dis files found with current config search settings.")
        print(f"Run created: {run_dir}")
        return run_dir

    processed = 0
    failed = []

    for item in candidates:
        dis_path = item["dis_path"]
        station_id = _station_id_from_point_folder(item["point_folder"])

        try:
            res = adapter.parse_file_strict(dis_path, str(spec_path))

            meta = SourceMeta(
                source="flowtracker",
                station_id=station_id,
                measurement_date=res.extracted_meta["measurement_date"],
                measurement_time=res.extracted_meta.get("measurement_time") or "000000",
                timezone=cfg.get("timezone", "America/Montevideo"),
                input_file=Path(dis_path).name,
                input_path=str(Path(dis_path).resolve()),
                run_id=run_dir.name,
            )

            dfs = normalizer.normalize_measurement(res.raw_groups, meta)

            for group, df in dfs.items():
                outpath = (
                    group_dirs[group]
                    / f"{station_id}_{group}_{meta.measurement_date}_{meta.measurement_time}.csv"
                )
                df.to_csv(outpath, index=False)
                print(f"Saved: {outpath}")

            processed += 1

        except Exception as e:
            print(f"ERROR processing {dis_path}: {e}")
            failed.append(dis_path)

    print(f"Processed OK: {processed}/{len(candidates)}")

    if failed:
        print("Failed .dis files:")
        for f in failed:
            print(f" - {f}")

    print(f"Run created: {run_dir}")

    return run_dir