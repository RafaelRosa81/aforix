from pathlib import Path
import argparse
import pandas as pd


GROUPS = ["Summary", "Points", "Sections", "Gates"]


def check_ingest_run(run_dir: Path, instrument: str) -> None:
    base = run_dir / "outputs" / "raw_canonical" / instrument

    print(f"\nChecking: {instrument}")
    print(f"Run dir: {run_dir}")
    print(f"Expected base: {base}")

    if not base.exists():
        print("ERROR: raw_canonical folder not found.")
        return

    for group in GROUPS:
        group_dir = base / group

        if not group_dir.exists():
            print(f"{group}: MISSING folder")
            continue

        files = sorted(group_dir.glob("*.csv"))

        if not files:
            print(f"{group}: 0 CSV files")
            continue

        empty_files = []
        bad_files = []

        total_rows = 0

        for f in files:
            try:
                df = pd.read_csv(f)
                total_rows += len(df)

                if df.empty:
                    empty_files.append(f.name)

            except Exception as e:
                bad_files.append((f.name, str(e)))

        print(f"{group}: {len(files)} files | {total_rows} rows")

        if empty_files:
            print(f"  Empty files: {empty_files}")

        if bad_files:
            print(f"  Bad files:")
            for name, err in bad_files:
                print(f"    {name}: {err}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--instrument", required=True, choices=["flowtracker", "molinete", "nivus", "m9"])

    args = parser.parse_args()

    check_ingest_run(
        run_dir=Path(args.run_dir),
        instrument=args.instrument,
    )


if __name__ == "__main__":
    main()