from pathlib import Path

from aforix.batch.models import (
    BatchDefinition,
    BatchStep,
    CommandResult,
    ExecutionOptions,
)
from aforix.batch.registry import CommandRegistry, RegisteredCommand
from aforix.batch.runner import BatchRunner



def success_command(params):
    return CommandResult(
        status="success",
        outputs=["output.csv"],
        warnings=[],
        metrics={"rows_processed": 10},
    )



def test_runner_executes_steps(tmp_path: Path) -> None:
    registry = CommandRegistry()

    registry.register(
        RegisteredCommand(
            name="normalize.run",
            callable=success_command,
        )
    )

    batch = BatchDefinition(
        version=1,
        batch_id="test_batch",
        name="Test",
        description="",
        main_config="configs/examples/main.yaml",
        execution=ExecutionOptions(output_dir=str(tmp_path)),
        steps=[
            BatchStep(id="normalize", command="normalize.run")
        ],
    )

    runner = BatchRunner(registry=registry)

    manifest = runner.run(batch)

    assert manifest.status == "success"
    assert manifest.steps[0].outputs == ["output.csv"]



def test_runner_dry_run(tmp_path: Path) -> None:
    registry = CommandRegistry()

    registry.register(
        RegisteredCommand(
            name="normalize.run",
            callable=success_command,
        )
    )

    batch = BatchDefinition(
        version=1,
        batch_id="dry_run_batch",
        name="DryRun",
        description="",
        main_config="configs/examples/main.yaml",
        execution=ExecutionOptions(output_dir=str(tmp_path)),
        steps=[
            BatchStep(id="normalize", command="normalize.run")
        ],
    )

    runner = BatchRunner(registry=registry)

    manifest = runner.run(batch, dry_run=True)

    assert manifest.status == "success"
