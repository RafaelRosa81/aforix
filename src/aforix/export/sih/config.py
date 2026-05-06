from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_sih_config(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"SIH config file not found: {p}")

    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        raise ValueError(f"SIH config must contain a YAML mapping: {p}")

    return data
