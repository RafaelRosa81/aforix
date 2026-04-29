from pathlib import Path
import re
import pandas as pd
from datetime import datetime

from aforix.config.loader import load_config
from aforix.runs.manager import create_run
from aforix.ingest.adapters.flowtracker_dis import parse_flowtracker_dis


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

    outdir_root = run_dir / "outputs" / "raw_canonical" / "flowtracker"

    group_dirs = {
        group: outdir_root / group
        for group in ["Summary", "Points", "Sections", "Gates"]
    }

    for group_dir in group_dirs.values():
        group_dir.mkdir(parents=True, exist_ok=True)

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
            summary, points = parse_flowtracker_dis(dis_path)

            start_dt = summary.get("start_date_time")

            if not start_dt:
                raise ValueError(f"Missing start_date_time in FlowTracker summary: {dis_path}")

            dt = datetime.strptime(start_dt, "%Y/%m/%d %H:%M:%S")

            measurement_date = dt.strftime("%Y%m%d")
            measurement_time = dt.strftime("%H%M%S")

            # --------------------------------------------------
            # SUMMARY
            # --------------------------------------------------
            summary["station_id"] = station_id
            summary["measurement_date"] = measurement_date
            summary["measurement_time"] = measurement_time
            summary["instrument"] = "flowtracker"
            summary["source_csv"] = str(dis_path)
            summary["source_run_dir"] = str(run_dir)

            summary_df = pd.DataFrame([summary])

            summary_outpath = (
                group_dirs["Summary"]
                / f"{station_id}_Summary_{measurement_date}_{measurement_time}.csv"
            )

            summary_df.to_csv(summary_outpath, index=False)
            print(f"Saved: {summary_outpath}")

            # --------------------------------------------------
            # POINTS (FIX CLAVE)
            # --------------------------------------------------
            if isinstance(points, pd.DataFrame):
                points_df = points.copy()
            else:
                points_df = pd.DataFrame(points)

            if not points_df.empty:
                points_df["station_id"] = station_id
                points_df["measurement_date"] = measurement_date
                points_df["measurement_time"] = measurement_time
                points_df["instrument"] = "flowtracker"
                points_df["source_csv"] = str(dis_path)
                points_df["source_run_dir"] = str(run_dir)

                points_outpath = (
                    group_dirs["Points"]
                    / f"{station_id}_Points_{measurement_date}_{measurement_time}.csv"
                )

                points_df.to_csv(points_outpath, index=False)
                print(f"Saved: {points_outpath}")

            # --------------------------------------------------
            # SECTIONS / GATES (vacíos)
            # --------------------------------------------------
            for group in ["Sections", "Gates"]:
                outpath = (
                    group_dirs[group]
                    / f"{station_id}_{group}_{measurement_date}_{measurement_time}.csv"
                )

                pd.DataFrame().to_csv(outpath, index=False)

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