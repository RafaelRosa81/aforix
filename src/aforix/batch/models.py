from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ExecutionOptions:
    stop_on_error: bool = True
    continue_on_error: bool = False
    create_manifest: bool = True
    output_dir: str = "runs/batch"


@dataclass(slots=True)
class BatchStep:
    id: str
    command: str
    enabled: bool = True
    params: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class BatchDefinition:
    version: int
    batch_id: str
    name: str
    description: str
    main_config: str
    execution: ExecutionOptions
    variables: dict[str, Any] = field(default_factory=dict)
    steps: list[BatchStep] = field(default_factory=list)


@dataclass(slots=True)
class CommandResult:
    """Standard result returned by batch-registered commands."""

    status: str = "success"
    outputs: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
