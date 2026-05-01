from __future__ import annotations

from pathlib import Path
import re


def find_files_recursive(root: Path, extensions: set[str]) -> list[Path]:
    """Find files recursively under root by extension."""

    root = Path(root).resolve()

    if not root.exists():
        raise ValueError(f"Raw data directory does not exist: {root}")

    if not root.is_dir():
        raise ValueError(f"Raw data path is not a directory: {root}")

    normalized_extensions = {ext.lower() for ext in extensions}

    files: list[Path] = []

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue

        if path.suffix.lower() in normalized_extensions:
            files.append(path)

    return files


def fallback_station_id_from_parents(path: Path) -> str | None:
    """Return nearest parent folder matching P<number>, if present."""

    path = Path(path)

    for parent in path.parents:
        if re.match(r"^P\d{1,4}$", parent.name, flags=re.IGNORECASE):
            return parent.name.upper()

    return None