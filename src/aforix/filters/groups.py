from pathlib import Path
from aforix.config.loader import load_config
from aforix.runs.manager import create_run


def run(config_path: Path) -> Path:
    cfg = load_config(config_path)
    run_dir = create_run("filter_groups", config_path)

    print("Running group filtering")
    print(f"Config keys: {list(cfg.keys())}")
    print(f"Run created: {run_dir}")

    return run_dir