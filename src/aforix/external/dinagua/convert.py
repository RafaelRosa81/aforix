from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


def _parse_filename(name: str) -> tuple[str, str]:
    parts = re.split(r"[_\.]", name)
    if len(parts) >= 3:
        return parts[0], parts[2]
    if len(parts) >= 2:
        return parts[0], "daily"
    return "unknown", "daily"


def run_dinagua_conversion(input_dir: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    for file in list(input_dir.glob("*.xls")) + list(input_dir.glob("*.xlsx")):
        try:
            df = pd.read_excel(file)
        except Exception:
            continue

        cols = {c.lower(): c for c in df.columns}
        date_col = cols.get("fecha") or cols.get("date")
        flow_col = cols.get("q") or cols.get("caudal") or cols.get("flow")

        if not date_col or not flow_col:
            continue

        station, timestep = _parse_filename(file.name)

        out = pd.DataFrame()
        out["date"] = pd.to_datetime(df[date_col], errors="coerce")
        out["time"] = out["date"].dt.strftime("%H:%M:%S")
        out["date"] = out["date"].dt.strftime("%Y-%m-%d")
        out["q(m3/s)"] = pd.to_numeric(df[flow_col], errors="coerce")

        out = out.dropna()
        out.to_csv(output_dir / f"{station}_{timestep}_station_data.csv", index=False)

    return output_dir
