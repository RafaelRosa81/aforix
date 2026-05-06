from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SihExportRequest:
    selection_file: Path | None = None
    interactive: bool = False


@dataclass(frozen=True)
class SihExportResult:
    output_dir: Path
    exported_files: tuple[Path, ...]


def run_sih_export(request: SihExportRequest) -> SihExportResult:
    raise NotImplementedError("SIH export implementation pending")
