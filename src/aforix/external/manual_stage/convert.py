from pathlib import Path

import pandas as pd


def run_manual_stage_conversion(input_dir: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(input_dir.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No manual stage CSV found in: {input_dir}")

    dfs = []
    diagnostics = []

    for f in files:
        df = pd.read_csv(f)
        if "ID_punto" not in df.columns:
            diagnostics.append({"source_file": f.name, "status": "skipped", "reason": "missing_ID_punto"})
            continue

        date_cols = [c for c in df.columns if c != "ID_punto"]
        df_long = df.melt(id_vars=["ID_punto"], value_vars=date_cols, var_name="measurement_date", value_name="manual_stage_m")
        df_long["station_id"] = df_long["ID_punto"].map(_normalize_station_id)
        df_long["measurement_date"] = pd.to_datetime(df_long["measurement_date"], errors="coerce", dayfirst=False).dt.strftime("%Y-%m-%d")
        df_long["manual_stage_m"] = pd.to_numeric(df_long["manual_stage_m"], errors="coerce")
        df_long["measurement_time"] = None
        df_long["source_file"] = f.name

        before = len(df_long)
        df_long = df_long.dropna(subset=["station_id", "measurement_date", "manual_stage_m"])
        after = len(df_long)
        diagnostics.append({"source_file": f.name, "status": "ok", "rows_input": before, "rows_output": after})

        dfs.append(df_long[["station_id", "measurement_date", "measurement_time", "manual_stage_m", "source_file"]])

    diag_path = output_dir / "manual_stage_diagnostics.csv"
    pd.DataFrame(diagnostics).to_csv(diag_path, index=False)

    if not dfs:
        raise ValueError("No valid manual stage data found")

    out = pd.concat(dfs, ignore_index=True)
    out = out.sort_values(["station_id", "measurement_date"]).reset_index(drop=True)

    out_path = output_dir / "manual_stage.csv"
    out.to_csv(out_path, index=False)

    return out_path


def _normalize_station_id(value) -> str | None:
    if pd.isna(value):
        return None
    s = str(value).strip().upper()
    if not s:
        return None
    if s.startswith("P"):
        digits = "".join(ch for ch in s[1:] if ch.isdigit())
    else:
        digits = "".join(ch for ch in s if ch.isdigit())
    if not digits:
        return s
    return f"P{int(digits)}"
