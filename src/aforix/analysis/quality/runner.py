from __future__ import annotations

from pathlib import Path
from datetime import datetime
import pandas as pd

from aforix.analysis.quality.config import load_quality_config
from aforix.analysis.quality.metrics import compute_cg_from_weights, find_column


def run_quality_metrics(config_path: str | Path) -> Path:
    qc = load_quality_config(config_path)

    if not qc.enabled:
        raise RuntimeError("quality_metrics disabled in config")

    norm_dir = qc.nivus.normalized_points
    raw_dir = qc.nivus.raw_points

    if not norm_dir.exists():
        raise FileNotFoundError(f"Normalized Points dir not found: {norm_dir}")
    if not raw_dir.exists():
        raise FileNotFoundError(f"Raw Points dir not found: {raw_dir}")

    results = []

    for norm_file in sorted(norm_dir.glob("*.csv")):
        raw_file = raw_dir / norm_file.name
        if not raw_file.exists():
            continue

        df_norm = pd.read_csv(norm_file)
        df_raw = pd.read_csv(raw_file)

        try:
            w_col = qc.nivus.weight_column
            if w_col not in df_norm.columns:
                raise ValueError(f"Missing weight column '{w_col}' in {norm_file.name}")

            tq_col = find_column(df_raw, qc.nivus.tq_candidates)

            if len(df_norm) != len(df_raw):
                raise ValueError("Normalized and raw Points length mismatch")

            cg = compute_cg_from_weights(df_norm[w_col], df_raw[tq_col])

            results.append({
                "file": norm_file.name,
                "cg": cg,
            })
        except Exception as e:
            results.append({
                "file": norm_file.name,
                "cg": None,
                "error": str(e),
            })

    df = pd.DataFrame(results)

    out_dir = qc.paths.output_root / datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)

    df.to_csv(out_dir / "cg_measurements.csv", index=False)

    return out_dir
