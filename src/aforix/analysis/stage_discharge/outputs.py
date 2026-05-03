from pathlib import Path
import pandas as pd
from datetime import datetime


def write_outputs(df: pd.DataFrame, output_root: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = output_root / ts
    out_dir.mkdir(parents=True, exist_ok=True)

    df.to_csv(out_dir / "stage_discharge_matched_pairs.csv", index=False)

    return out_dir
