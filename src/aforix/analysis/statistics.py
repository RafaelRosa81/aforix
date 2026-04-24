from pathlib import Path

from aforix.config.loader import load_config
from aforix.runs.manager import create_run


def run(config_path: Path) -> Path:
    """Run statistical analysis pipeline."""

    cfg = load_config(config_path)
    run_dir = create_run("analysis_statistics", config_path)

    print("Config loaded")
    print("Running statistical analysis")
    print(f"Config keys: {list(cfg.keys())}")
    print(f"Run created: {run_dir}")

    return run_dir