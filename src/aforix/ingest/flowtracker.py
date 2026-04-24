from pathlib import Path
from aforix.config.loader import load_config
from aforix.runs.manager import create_run


def run(config_path: Path) -> Path:
    """Run FlowTracker ingest pipeline."""

    cfg = load_config(config_path)
    run_dir = create_run("ingest_flowtracker", config_path)

    print("Config loaded")
    print("Running FlowTracker ingest")
    print(f"Config keys: {list(cfg.keys())}")
    print(f"Run created: {run_dir}")

    return run_dir