from pathlib import Path
import pandas as pd


def run_manual_stage_conversion(input_dir: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    # Basic implementation: expects CSV in wide format
    files = list(input_dir.glob("*.csv"))
    if not files:
        raise FileNotFoundError("No manual stage CSV found")

    dfs = []
    for f in files:
        df = pd.read_csv(f)
        if "ID_punto" not in df.columns:
            continue

        df_long = df.melt(id_vars=["ID_punto"], var_name="measurement_date", value_name="manual_stage_m")
        df_long = df_long.dropna(subset=["manual_stage_m"])
        df_long["station_id"] = df_long["ID_punto"]
        df_long["measurement_time"] = None
        df_long["source_file"] = f.name

        dfs.append(df_long[["station_id","measurement_date","measurement_time","manual_stage_m","source_file"]])

    if not dfs:
        raise ValueError("No valid manual stage data found")

    out = pd.concat(dfs, ignore_index=True)

    out_path = output_dir / "manual_stage.csv"
    out.to_csv(out_path, index=False)

    return out_path
