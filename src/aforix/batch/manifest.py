import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class StepManifest:
    id: str
    command: str
    status: str
    duration_sec: float | None = None
    outputs: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class BatchManifest:
    batch_id: str
    batch_run_id: str
    status: str
    started_at: str
    finished_at: str | None = None
    duration_sec: float | None = None
    timezone: str | None = None
    started_at_utc: str | None = None
    finished_at_utc: str | None = None
    steps: list[StepManifest] = field(default_factory=list)


def manifest_to_dict(manifest: BatchManifest) -> dict[str, Any]:
    return asdict(manifest)


def write_manifest(manifest: BatchManifest, path: str | Path) -> None:
    manifest_path = Path(path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    with manifest_path.open("w", encoding="utf-8") as file:
        json.dump(manifest_to_dict(manifest), file, indent=2, ensure_ascii=False)
        file.write("\n")
