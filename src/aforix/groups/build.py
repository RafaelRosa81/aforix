from pathlib import Path
import pandas as pd

from aforix.config.loader import load_config
from aforix.runs.manager import create_run


GROUPS = ["Summary", "Points", "Sections", "Gates"]


def _read_group_files(run_dir: Path, instrument: str, group: str) -> pd.DataFrame:
    group_dir = run_dir / "outputs" / "raw_canonical" / instrument / group

    if not group_dir.exists():
        return pd.DataFrame()

    rows = []

    for csv_path in sorted(group_dir.glob("*.csv")):
        try:
            df = pd.read_csv(csv_path)

            if df.empty:
                continue

            df["instrument"] = instrument
            df["source_csv"] = str(csv_path)
            df["source_run_dir"] = str(run_dir)

            rows.append(df)

        except Exception as e:
            print(f"WARNING: could not read {csv_path}: {e}")

    if not rows:
        return pd.DataFrame()

    return pd.concat(rows, ignore_index=True, sort=False)


def run(config_path: Path) -> Path:
    """Build grouped datasets from ingest outputs."""

    cfg = load_config(config_path)
    run_dir = create_run("build_groups", config_path)

    build_cfg = cfg.get("build_groups", {})
    output_dir = Path(build_cfg.get("output_dir", "database/data_groups"))
    sources = build_cfg.get("sources", {})

    if not sources:
        raise ValueError("Missing build_groups.sources in config")

    output_dir.mkdir(parents=True, exist_ok=True)

    print("Building data groups")
    print(f"Output dir: {output_dir}")

    for group in GROUPS:
        group_frames = []

        for instrument, source_run in sources.items():
            source_run_dir = Path(source_run)
            df = _read_group_files(source_run_dir, instrument, group)

            if not df.empty:
                group_frames.append(df)

        if not group_frames:
            print(f"{group}: no data")
            continue

        group_df = pd.concat(group_frames, ignore_index=True, sort=False)

        group_output_dir = output_dir / group
        group_output_dir.mkdir(parents=True, exist_ok=True)

        outpath = group_output_dir / f"{group.lower()}_all.csv"
        group_df.to_csv(outpath, index=False)

        print(f"{group}: {len(group_df)} rows -> {outpath}")

    print(f"Run created: {run_dir}")

    return run_dir