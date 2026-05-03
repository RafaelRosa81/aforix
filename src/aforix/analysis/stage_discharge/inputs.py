from pathlib import Path
import pandas as pd


def load_manual_stage(manual_dir: Path) -> pd.DataFrame:
    f = manual_dir / "manual_stage.csv"
    if not f.exists():
        return pd.DataFrame()
    return pd.read_csv(f)


def load_summary_tables(normalized_root: Path, instruments_cfg: dict) -> pd.DataFrame:
    dfs = []
    for inst, cfg in instruments_cfg.items():
        if not cfg.get("enabled", False):
            continue

        subdir = cfg.get("summary_table")
        path = normalized_root / subdir
        if not path.exists():
            continue

        for f in path.glob("*.csv"):
            df = pd.read_csv(f)
            df["instrument"] = inst
            df["source_file"] = f.name
            dfs.append(df)

    if not dfs:
        return pd.DataFrame()

    return pd.concat(dfs, ignore_index=True)
