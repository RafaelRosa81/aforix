from pathlib import Path
from typing import Any

import yaml

from aforix.batch.errors import BatchValidationError


def load_batch_yaml(path: str | Path) -> dict[str, Any]:
    """Load a batch YAML file as a raw dictionary."""

    batch_path = Path(path)
    if not batch_path.exists():
        raise BatchValidationError(f"Batch file does not exist: {batch_path}")

    with batch_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if data is None:
        raise BatchValidationError(f"Batch file is empty: {batch_path}")

    if not isinstance(data, dict):
        raise BatchValidationError("Batch file root must be a mapping/dictionary.")

    return data
