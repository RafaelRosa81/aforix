from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd


def _normalize_name(value: object) -> str:
    text = str(value)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def _parse_filename(name: str) -> tuple[str, str]:
    # Expected: {station}_{name}_{timestep}.xls/.xlsx
    stem = Path(name).stem
    parts = stem.split("_")
    if len(parts) >= 3:
        return parts[0], parts[-1]
    if len(parts) >= 1:
        return parts[0], "daily"
    return "unknown", "daily"


def _find_column(df: pd.DataFrame, candidates: set[str]) -> str | None:
    normalized = {_normalize_name(c): c for c in df.columns}
    for candidate in candidates:
        if candidate in normalized:
            return normalized[candidate]
    for norm, original in normalized.items():
        if any(candidate in norm for candidate in candidates):
            return original
    return None


def _coerce_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", ".", regex=False), errors="coerce")


def run_dinagua_conversion(input_dir: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(list(input_dir.glob("*.xls")) + list(input_dir.glob("*.xlsx")))
    print(f"DINAGUA converter input: {input_dir}")
    print(f"DINAGUA converter output: {output_dir}")
    print(f"Found {len(files)} Excel file(s).")

    converted = 0
    skipped = 0

    for file in files:
        try:
            df = pd.read_excel(file)
        except Exception as exc:
            skipped += 1
            print(f"SKIP {file.name}: cannot read Excel ({exc})")
            continue

        date_col = _find_column(df, {"fecha", "date"})
        flow_col = _find_column(df, {"q", "caudal", "flow", "valor", "gasto"})

        if not date_col or not flow_col:
            skipped += 1
            print(f"SKIP {file.name}: missing date/flow column. Columns={list(df.columns)}")
            continue

        station, timestep = _parse_filename(file.name)

        dt = pd.to_datetime(df[date_col], dayfirst=True, errors="coerce")
        q = _coerce_numeric(df[flow_col])

        out = pd.DataFrame()
        out["date"] = dt.dt.strftime("%Y-%m-%d")
        out["time"] = dt.dt.strftime("%H:%M:%S")
        out["q(m3/s)"] = q
        out = out.dropna(subset=["date", "q(m3/s)"]).reset_index(drop=True)

        if out.empty:
            skipped += 1
            print(f"SKIP {file.name}: no valid date/flow rows after parsing")
            continue

        out_path = output_dir / f"{station}_{timestep}_station_data.csv"
        out.to_csv(out_path, index=False)
        converted += 1
        print(f"OK {file.name} -> {out_path.name} ({len(out)} rows; date={date_col}; flow={flow_col})")

    print(f"DINAGUA conversion finished. Converted={converted}, skipped={skipped}.")
    return output_dir
