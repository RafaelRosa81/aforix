from pathlib import Path
from aforix.config.loader import load_config


def load_stage_discharge_config(config_path: Path) -> dict:
    cfg = load_config(config_path)
    return cfg.get("analysis", {}).get("stage_discharge", {})
