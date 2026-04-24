from pathlib import Path
from aforix.config.loader import load_config
from aforix.runs.manager import create_run


def run(config_path: Path) -> Path:
    cfg = load_config(config_path)
    run_dir = create_run("ingest_nivus", config_path)

    print("Config loaded")
    print("Running Nivus ingest")
    print(f"Config keys: {list(cfg.keys())}")
    print(f"Run created: {run_dir}")

    return run_dir