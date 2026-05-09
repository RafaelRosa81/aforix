from typing import Any

from aforix.batch.models import BatchDefinition, BatchStep, ExecutionOptions


def batch_definition_from_dict(data: dict[str, Any]) -> BatchDefinition:
    batch_info = data["batch"]
    project_info = data["project"]
    execution_info = data.get("execution", {})

    execution = ExecutionOptions(
        stop_on_error=execution_info.get("stop_on_error", True),
        continue_on_error=execution_info.get("continue_on_error", False),
        create_manifest=execution_info.get("create_manifest", True),
        output_dir=execution_info.get("output_dir", "runs/batch"),
    )

    steps = [
        BatchStep(
            id=step["id"],
            command=step["command"],
            enabled=step.get("enabled", True),
            params=step.get("params", {}),
            depends_on=step.get("depends_on", []),
            tags=step.get("tags", []),
        )
        for step in data.get("steps", [])
    ]

    return BatchDefinition(
        version=data["version"],
        batch_id=batch_info["id"],
        name=batch_info.get("name", batch_info["id"]),
        description=batch_info.get("description", ""),
        main_config=project_info["main_config"],
        execution=execution,
        variables=data.get("variables", {}),
        steps=steps,
    )
