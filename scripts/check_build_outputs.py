from pathlib import Path
import pandas as pd

root = Path("database/raw_canonical")

required = [
    "station_id",
    "station_name",
    "measurement_date",
    "measurement_time",
    "instrument",
    "source_file",
    "source_run_dir",
    "run_id",
]

print("ROOT EXISTS:", root.exists())

files = list(root.rglob("*.csv"))
print("CSV files:", len(files))

bad = []

for p in files:
    df = pd.read_csv(p, dtype=str, nrows=5)
    missing = [c for c in required if c not in df.columns]

    if missing:
        bad.append((str(p), missing))

print("FILES MISSING TRACEABILITY:", len(bad))

for item in bad[:20]:
    print(item)