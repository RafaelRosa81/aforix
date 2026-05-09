from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from aforix.batch.manifest import BatchManifest, StepManifest, write_manifest
from aforix.batch.models import BatchDefinition
from aforix.batch.planner import BatchPlanner
from aforix.batch.registry import CommandRegistry


class BatchRunner:
    """Coordinates batch execution.

    The runner must never implement domain processing logic directly.
    """

    def __init__(
        self,
        registry: CommandRegistry,
        planner: BatchPlanner | None = None,
    ) -> None:
        self.registry = registry
        self.planner = planner or BatchPlanner()

    def run(
        self,
        batch: BatchDefinition,
        *,
        dry_run: bool = False,
    ) -> BatchManifest:
        started_at = datetime.now(UTC)
        batch_run_id = started_at.strftime("%Y%m%d_%H%M%S")

        manifest = BatchManifest(
            batch_id=batch.batch_id,
            batch_run_id=batch_run_id,
            status="running",
            started_at=started_at.isoformat(),
        )

        output_dir = (
            Path(batch.execution.output_dir)
            / batch_run_id
        )

        output_dir.mkdir(parents=True, exist_ok=True)

        plan = self.planner.build_execution_plan(batch)

        total_start = perf_counter()

        for step in plan:
            command = self.registry.get(step.command)

            step_started = perf_counter()

            step_manifest = StepManifest(
                id=step.id,
                command=step.command,
                status="running",
            )

            try:
                if dry_run:
                    print(f"[DRY-RUN] {step.id} -> {step.command}")
                else:
                    print(f"[RUN] {step.id} -> {step.command}")
                    command.callable()

                step_manifest.status = "success"

            except Exception as exc:
                step_manifest.status = "failed"
                step_manifest.errors.append(str(exc))

                if batch.execution.stop_on_error:
                    manifest.steps.append(step_manifest)
                    manifest.status = "failed"
                    break

            finally:
                step_finished = perf_counter()
                step_manifest.duration_sec = round(
                    step_finished - step_started,
                    4,
                )

                manifest.steps.append(step_manifest)

        total_finished = perf_counter()

        manifest.duration_sec = round(
            total_finished - total_start,
            4,
        )

        if manifest.status != "failed":
            manifest.status = "success"

        manifest.finished_at = datetime.now(UTC).isoformat()

        if batch.execution.create_manifest:
            write_manifest(
                manifest,
                output_dir / "manifest.json",
            )

        return manifest
