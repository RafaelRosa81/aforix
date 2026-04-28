from pathlib import Path
import re
import yaml

from aforix.config.loader import load_config
from aforix.runs.manager import create_run
from aforix.ingest.adapters.molinete_excel import MolineteExcelAdapter


def _find_molinete_excels(config: dict) -> list[dict]:
    raw_data_root = Path(config["raw_data_path_dir"])
    stage1_keyword = config["subfolder_raw_data_word_dir"]
    stage2_foldername = config["subsubfolder_raw_data_word_dir_ML"]

    exts = {".xls", ".xlsx", ".xlsm"}
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

            for file_path in point_path.iterdir():
                if file_path.suffix.lower() in exts and file_path.is_file():
                    candidates.append(
                        {
                            "campaign_folder": folder.name,
                            "point_folder": point_path.name,
                            "point_path": str(point_path),
                            "xls_file": file_path.name,
                            "xls_path": str(file_path),
                        }
                    )

    return candidates


def _format_date_yyyymmdd(value: str) -> str:
    if not value:
        return "00000000"
    return str(value).replace("-", "").replace("/", "")


def _format_time_hhmmss(value: str) -> str:
    if not value:
        return "000000"
    return str(value).replace(":", "")


def run(config_path: Path) -> Path:
    """Run Molinete ingest pipeline (RAW EXPORT, no normalizer)."""

    cfg = load_config(config_path)
    run_dir = create_run("ingest_molinete", config_path)

    outdir_root = run_dir / "outputs" / "raw_canonical" / "molinete"

    group_dirs = {
        group: outdir_root / group
        for group in ["Summary", "Points"]
    }

    for group_dir in group_dirs.values():
        group_dir.mkdir(parents=True, exist_ok=True)

    adapter = MolineteExcelAdapter()
    candidates = _find_molinete_excels(cfg)

    print(f"Found Molinete Excel files: {len(candidates)}")

    if not candidates:
        print("No Molinete Excel files found.")
        print(f"Run created: {run_dir}")
        return run_dir

    processed = 0
    failed = []

    sheet_name = cfg.get("molinete_sheet_name", "CALCULO")

    for item in candidates:
        xls_path = item["xls_path"]

        try:
            res = adapter.parse_file_strict(
                xls_path,
                sheet_name=sheet_name,
            )

            station_id = res.extracted_meta["station_id"]
            measurement_date = _format_date_yyyymmdd(
                res.extracted_meta.get("measurement_date", "")
            )
            measurement_time = _format_time_hhmmss(
                res.extracted_meta.get("measurement_time", "")
            )

            # ------------------------------------------------------------------
            # Summary
            # ------------------------------------------------------------------
            summary_df = res.raw_groups.get("Summary")
            if summary_df is not None:
                summary_df = summary_df.drop(columns=["extras_json"], errors="ignore")

                outpath = (
                    group_dirs["Summary"]
                    / f"{station_id}_Summary_{measurement_date}_{measurement_time}.csv"
                )

                summary_df.to_csv(outpath, index=False)
                print(f"Saved: {outpath}")

            # ------------------------------------------------------------------
            # Points
            # ------------------------------------------------------------------
            points_df = res.raw_groups.get("Points")
            if points_df is not None:
                points_df = points_df.drop(columns=["extras_json"], errors="ignore")

                outpath = (
                    group_dirs["Points"]
                    / f"{station_id}_Points_{measurement_date}_{measurement_time}.csv"
                )

                points_df.to_csv(outpath, index=False)
                print(f"Saved: {outpath}")

            processed += 1

        except Exception as e:
            print(f"ERROR processing {xls_path}: {e}")
            failed.append(xls_path)

    print(f"Processed OK: {processed}/{len(candidates)}")

    if failed:
        print("Failed Molinete files:")
        for f in failed:
            print(f" - {f}")

    print(f"Run created: {run_dir}")

    return run_dir