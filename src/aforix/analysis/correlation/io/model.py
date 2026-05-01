from __future__ import annotations

import re
from pathlib import Path
from typing import Dict

import pandas as pd


def load_model_data(model_dir: Path) -> Dict[str, pd.DataFrame]:
    """Load normalized model CSVs (P{point}_model_data.csv)."""

    out: Dict[str, pd.DataFrame] = {}
    pattern = re.compile(r"P?(\d+)_model_data\.csv$")

    for file in model_dir.glob("*_model_data.csv"):
        m = pattern.match(file.name)
        if not m:
            continue

        point = m.group(1)
        df = pd.read_csv(file)

        if "date" not in df.columns or "q(m3/s)" not in df.columns:
            continue

        d = df.copy()
        d["date"] = pd.to_datetime(d["date"], errors="coerce")
        d["q_model_l/s"] = pd.to_numeric(d["q(m3/s)"], errors="coerce") * 1000.0

        d = d.dropna(subset=["date", "q_model_l/s"]) \
             [["date", "q_model_l/s"]]

        out[point] = d

    return out
