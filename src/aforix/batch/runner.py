from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml

from aforix.batch.manifest import BatchManifest, StepManifest, write_manifest
from aforix.batch.metrics import MetricsCollector, metrics_to_dict
from aforix.batch.models import BatchDefinition, CommandResult
from aforix.batch.planner import BatchPlanner
from aforix.batch.registry import CommandRegistry
from aforix.batch.report import BatchReportGenerator


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
        self.report_generator = BatchReportGenerator()

    def run(
        self,
        batch: BatchDefinition,
        *,
        dry_run: bool = False,
    ) -> BatchManifest:
        timezone_name = self._resolve_timezone(batch)
        tzinfo = self._safe_zoneinfo(timezone_name)

        started_local = datetime.now(tzinfo)
        started_utc = started_local.astimezone(timezone.utc)

        batch_run_id = started_local.strftime("%Y%m%d_%H%M%S")

        manifest = BatchManifest(
            batch_id=batch.batch_id,
            batch_run_id=batch_run_id,
            status="running",
            started_at=started_local.isoformat(),
            timezone=timezone_name,
            started_at_utc=started_utc.isoformat(),
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
            result = CommandResult(status="success")

            metrics_collector = MetricsCollector()
            metrics_collector.start()

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
                    maybe_result = command.callable(step.params)

                    if maybe_result is not None:
                        result = maybe_result

                step_manifest.status = result.status
                step_manifest.outputs = result.outputs
                step_manifest.warnings.extend(result.warnings)

            except Exception as exc:
                step_manifest.status = "failed"
                step_manifest.errors.append(str(exc))
                manifest.status = "failed"

            finally:
                metrics = metrics_collector.stop()

                combined_metrics = metrics_to_dict(metrics)
                combined_metrics.update(result.metrics)

                step_manifest.duration_sec = metrics.duration_sec
                step_manifest.metrics = combined_metrics

                manifest.steps.append(step_manifest)

            if step_manifest.status == "failed" and batch.execution.stop_on_error:
                break

        total_finished = perf_counter()

        manifest.duration_sec = round(
            total_finished - total_start,
            4,
        )

        if manifest.status != "failed":
            manifest.status = "success"

        finished_local = datetime.now(tzinfo)
        finished_utc = finished_local.astimezone(timezone.utc)

        manifest.finished_at = finished_local.isoformat()
        manifest.finished_at_utc = finished_utc.isoformat()

        if batch.execution.create_manifest:
            write_manifest(
                manifest,
                output_dir / "manifest.json",
            )

        self.report_generator.write_reports(
            manifest,
            output_dir,
        )

        return manifest

    def _resolve_timezone(self, batch: BatchDefinition) -> str:
        config_path = Path(batch.main_config)

        if not config_path.exists():
            return "UTC"

        with config_path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}

        project = data.get("project", {})

        if isinstance(project, dict):
            timezone_name = project.get("timezone")
            if timezone_name:
                return str(timezone_name)

        return "UTC"

    def _safe_zoneinfo(self, timezone_name: str) -> ZoneInfo:
        try:
            return ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            return ZoneInfo("UTC")
