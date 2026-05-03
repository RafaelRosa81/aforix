from __future__ import annotations

from pathlib import Path
from datetime import datetime
import pandas as pd

from aforix.analysis.quality.metrics import compute_cg_nivus


def run_quality_metrics(config: dict) -> Path:
    input_dir = Path(config["analysis"]["quality_metrics"]["input_dir"])
    output_root = Path(config["analysis"]["quality_metrics"]["output_root"])

    output_root.mkdir(parents=True, exist_ok=True)

    rows = []

    for p in input_dir.rglob("*Points*.csv"):
        sec = Path(str(p).replace("Points", "Sections"))
        if not sec.exists():
            continue

        pts_df = pd.read_csv(p)
        sec_df = pd.read_csv(sec)

        try:
            cg = compute_cg_nivus(pts_df, sec_df)
            rows.append({"file": p.name, "cg": cg})
        except Exception:
            continue

    df = pd.DataFrame(rows)

    out_dir = output_root / datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / "cg_results.csv"
    df.to_csv(out_path, index=False)

    return out_dir
