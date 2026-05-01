from pathlib import Path
from typing import Any

import yaml

from aforix.config.validate import validate_config


def load_config(config_path: Path) -> dict[str, Any]:
    """Load and validate YAML configuration file."""

    config_path = Path(config_path).resolve()

    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    if not config_path.is_file():
        raise ValueError(f"Config path is not a file: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if config is None:
        raise ValueError(f"Config file is empty: {config_path}")

    validate_config(config, config_path=config_path)

    return config