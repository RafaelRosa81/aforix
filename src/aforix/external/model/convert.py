from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


def _extract_point_id(name: str) -> str | None:
    m = re.search(r"(\d+)", name)
    return m.group(1) if m else None


def run_model_conversion(input_dir: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    for file in input_dir.glob("*.csv"):
        try:
            df = pd.read_csv(file)
        except Exception:
            continue

        cols = {c.lower(): c for c in df.columns}
        date_col = cols.get("fecha") or cols.get("date")
        flow_col = cols.get("caudal") or cols.get("q") or cols.get("flow")

        if not date_col or not flow_col:
            continue

        point = _extract_point_id(file.name)
        if not point:
            continue

        out = pd.DataFrame()
        out["date"] = pd.to_datetime(df[date_col], errors="coerce")
        out["time"] = out["date"].dt.strftime("%H:%M:%S")
        out["date"] = out["date"].dt.strftime("%Y-%m-%d")
        out["q(m3/s)"] = pd.to_numeric(df[flow_col], errors="coerce")

        out = out.dropna()
        out.to_csv(output_dir / f"P{point}_model_data.csv", index=False)

    return output_dir
