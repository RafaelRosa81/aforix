from pathlib import Path

from aforix.normalize.run import normalize_run


run_dir = sorted(Path("runs").glob("ingest_flowtracker/*"))[-1]

print(f"Normalizing run: {run_dir}")

normalized_root = normalize_run(run_dir)

print(f"Normalized output: {normalized_root}")