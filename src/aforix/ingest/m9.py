from pathlib import Path

from aforix.config.loader import load_config
from aforix.runs.manager import create_run


def run(config_path: Path) -> Path:
    """Run M9 ingest pipeline."""

    cfg = load_config(config_path)
    run_dir = create_run("ingest_m9", config_path)

    print("Config loaded")
    print("Running M9 ingest")
    print(f"Config keys: {list(cfg.keys())}")
    print(f"Run created: {run_dir}")

    return run_dir