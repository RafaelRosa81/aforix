from pathlib import Path
import pandas as pd


GROUPS = {
    "Summary": "flowtracker_summary.csv",
    "Points": "flowtracker_points.csv",
    "Sections": "flowtracker_sections.csv",
    "Gates": "flowtracker_gates.csv",
}


def consolidate_flowtracker_run(
    run_dir: Path,
    database_root: Path = Path("database"),
) -> Path:
    """Consolidate one FlowTracker ingest run into unified group CSVs."""

    run_dir = run_dir.resolve()

    source_root = run_dir / "outputs" / "raw_canonical" / "flowtracker"
    target_root = database_root / "raw_canonical" / "flowtracker"
    target_root.mkdir(parents=True, exist_ok=True)

    if not source_root.exists():
        raise FileNotFoundError(f"FlowTracker output folder not found: {source_root}")

    for group, target_name in GROUPS.items():
        group_dir = source_root / group
        target_file = target_root / target_name

        if not group_dir.exists():
            continue

        new_files = sorted(group_dir.glob("*.csv"))

        if not new_files:
            continue

        new_df = pd.concat(
            [pd.read_csv(f) for f in new_files],
            ignore_index=True,
        )

        if target_file.exists():
            old_df = pd.read_csv(target_file)
            combined = pd.concat([old_df, new_df], ignore_index=True)
        else:
            combined = new_df

        combined = combined.drop_duplicates()

        combined.to_csv(target_file, index=False)

    return target_root