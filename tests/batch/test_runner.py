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


def failing_command(params):
    raise RuntimeError("intentional failure")


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
        steps=[BatchStep(id="normalize", command="normalize.run")],
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
        steps=[BatchStep(id="normalize", command="normalize.run")],
    )

    runner = BatchRunner(registry=registry)

    manifest = runner.run(batch, dry_run=True)

    assert manifest.status == "success"


def test_runner_stops_on_error_without_duplicate_failed_step(tmp_path: Path) -> None:
    registry = CommandRegistry()

    registry.register(RegisteredCommand(name="fail", callable=failing_command))
    registry.register(RegisteredCommand(name="success", callable=success_command))

    batch = BatchDefinition(
        version=1,
        batch_id="failure_batch",
        name="Failure",
        description="",
        main_config="configs/examples/main.yaml",
        execution=ExecutionOptions(output_dir=str(tmp_path), stop_on_error=True),
        steps=[
            BatchStep(id="fail_step", command="fail"),
            BatchStep(id="success_step", command="success"),
        ],
    )

    runner = BatchRunner(registry=registry)
    manifest = runner.run(batch)

    assert manifest.status == "failed"
    assert len(manifest.steps) == 1
    assert manifest.steps[0].id == "fail_step"
    assert manifest.steps[0].errors == ["intentional failure"]


def test_runner_continues_on_error_when_stop_on_error_false(tmp_path: Path) -> None:
    registry = CommandRegistry()

    registry.register(RegisteredCommand(name="fail", callable=failing_command))
    registry.register(RegisteredCommand(name="success", callable=success_command))

    batch = BatchDefinition(
        version=1,
        batch_id="continue_batch",
        name="Continue",
        description="",
        main_config="configs/examples/main.yaml",
        execution=ExecutionOptions(output_dir=str(tmp_path), stop_on_error=False),
        steps=[
            BatchStep(id="fail_step", command="fail"),
            BatchStep(id="success_step", command="success"),
        ],
    )

    runner = BatchRunner(registry=registry)
    manifest = runner.run(batch)

    assert manifest.status == "failed"
    assert len(manifest.steps) == 2
    assert manifest.steps[0].status == "failed"
    assert manifest.steps[1].status == "success"
