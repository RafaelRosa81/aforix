from pathlib import Path
import pandas as pd

from aforix.normalize.registry import NormalizationRegistry
from aforix.normalize.normalizer import normalize_table


def normalize_run(
    run_dir: Path,
    registry_dir: Path = Path("configs/normalization"),
) -> Path:
    """
    Normalize raw_canonical CSV outputs for a given run directory.

    Expected input:
        run_dir/outputs/raw_canonical/<instrument>/<Table>/*.csv

    Output:
        run_dir/outputs/normalized/<instrument>/<Table>/*.csv
    """

    run_dir = Path(run_dir)
    registry_dir = Path(registry_dir)

    raw_root = run_dir / "outputs" / "raw_canonical"
    normalized_root = run_dir / "outputs" / "normalized"

    if not raw_root.exists():
        raise FileNotFoundError(f"raw_canonical directory not found: {raw_root}")

    registry = NormalizationRegistry(registry_dir)

    normalized_count = 0
    failed = []

    for instrument_dir in raw_root.iterdir():
        if not instrument_dir.is_dir():
            continue

        instrument = instrument_dir.name

        for table_dir in instrument_dir.iterdir():
            if not table_dir.is_dir():
                continue

            table_name = table_dir.name

            try:
                spec = registry.get(instrument, table_name)
            except KeyError:
                print(f"Skipping: no registry spec for {instrument}/{table_name}")
                continue

            out_table_dir = normalized_root / instrument / table_name
            out_table_dir.mkdir(parents=True, exist_ok=True)

            for csv_path in sorted(table_dir.glob("*.csv")):
                try:
                    df_raw = pd.read_csv(csv_path)
                    df_norm = normalize_table(df_raw, spec)

                    out_path = out_table_dir / csv_path.name
                    df_norm.to_csv(out_path, index=False)

                    print(f"Normalized: {csv_path} -> {out_path}")
                    normalized_count += 1

                except Exception as e:
                    print(f"ERROR normalizing {csv_path}: {e}")
                    failed.append(str(csv_path))

    print(f"\nNormalized files: {normalized_count}")

    if failed:
        print("\nFailed files:")
        for path in failed:
            print(f" - {path}")

    return normalized_root