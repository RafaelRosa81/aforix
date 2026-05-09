from pathlib import Path

import typer

from aforix.batch.config import load_batch_yaml
from aforix.batch.factory import batch_definition_from_dict
from aforix.batch.planner import BatchPlanner
from aforix.batch.registry import CommandRegistry, RegisteredCommand
from aforix.batch.runner import BatchRunner
from aforix.batch.schema import BatchSchemaValidator
from aforix.batch.validators import RegistryValidator


app = typer.Typer(help="Batch orchestration commands.")


def build_default_registry() -> CommandRegistry:
    registry = CommandRegistry()

    placeholder = lambda: None

    commands = [
        "config-check",
        "ingest.flowtracker",
        "ingest.molinete",
        "ingest.nivus",
        "ingest.m9",
        "build-groups",
        "normalize.run",
        "validate.run",
        "export.tables",
        "export.sih",
        "analysis.correlation",
        "analysis.quality",
        "analysis.stage-discharge",
        "analysis.section-profiles",
    ]

    for command_name in commands:
        registry.register(
            RegisteredCommand(
                name=command_name,
                callable=placeholder,
            )
        )

    return registry


@app.command("check")
def batch_check(
    batch: str = typer.Option(..., "--batch", "-b", help="Path to batch YAML"),
):
    """Validate a batch YAML definition."""

    data = load_batch_yaml(batch)

    schema = BatchSchemaValidator()
    schema.validate(data)

    registry = build_default_registry()

    registry_validator = RegistryValidator()
    registry_validator.validate_commands(data["steps"], registry)

    typer.echo("Batch validation successful")
    typer.echo(f"Batch file: {Path(batch).resolve()}")


@app.command("plan")
def batch_plan(
    batch: str = typer.Option(..., "--batch", "-b", help="Path to batch YAML"),
    from_step: str | None = typer.Option(None, "--from-step", help="Start execution from step id"),
    only_step: str | None = typer.Option(None, "--only-step", help="Execute only one step id"),
    skip_step: list[str] = typer.Option([], "--skip-step", help="Skip step ids"),
):
    """Display resolved execution plan."""

    data = load_batch_yaml(batch)

    schema = BatchSchemaValidator()
    schema.validate(data)

    batch_definition = batch_definition_from_dict(data)

    planner = BatchPlanner()

    plan = planner.build_execution_plan(
        batch_definition,
        from_step=from_step,
        only_step=only_step,
        skip_steps=set(skip_step),
    )

    typer.echo(f"Batch: {batch_definition.batch_id}")
    typer.echo("Execution plan:")

    for index, step in enumerate(plan, start=1):
        typer.echo(f"  {index}. {step.id} -> {step.command}")

        if step.params:
            typer.echo(f"     params: {step.params}")


@app.command("run")
def batch_run(
    batch: str = typer.Option(..., "--batch", "-b", help="Path to batch YAML"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Do not execute commands"),
):
    """Execute a batch pipeline."""

    data = load_batch_yaml(batch)

    schema = BatchSchemaValidator()
    schema.validate(data)

    registry = build_default_registry()

    registry_validator = RegistryValidator()
    registry_validator.validate_commands(data["steps"], registry)

    batch_definition = batch_definition_from_dict(data)

    runner = BatchRunner(registry=registry)

    manifest = runner.run(
        batch_definition,
        dry_run=dry_run,
    )

    typer.echo(f"Batch completed with status: {manifest.status}")
    typer.echo(f"Batch run id: {manifest.batch_run_id}")
    typer.echo(f"Duration: {manifest.duration_sec} sec")


@app.command("list-commands")
def list_commands() -> None:
    """List available batch commands."""

    registry = build_default_registry()

    typer.echo("Registered batch commands:")

    for command in registry.list_commands():
        typer.echo(f" - {command}")
