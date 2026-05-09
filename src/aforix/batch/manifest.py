from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class StepManifest:
    id: str
    command: str
    status: str
    duration_sec: float | None = None
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
    steps: list[StepManifest] = field(default_factory=list)
