from pathlib import Path
import yaml


def load_config(config_path: Path) -> dict:
    """Load YAML configuration file."""

    config_path = config_path.resolve()

    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if config is None:
        raise ValueError("Config file is empty")

    return config