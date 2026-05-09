import json
from pathlib import Path

from aforix.batch.manifest import BatchManifest


class BatchReportGenerator:
    """Generates human-readable batch execution reports."""

    def generate_markdown(self, manifest: BatchManifest) -> str:
        lines: list[str] = []

        lines.append("# Batch Report")
        lines.append("")
        lines.append(f"- Batch ID: {manifest.batch_id}")
        lines.append(f"- Run ID: {manifest.batch_run_id}")
        lines.append(f"- Status: {manifest.status}")
        lines.append(f"- Duration (sec): {manifest.duration_sec}")
        lines.append("")
        lines.append("## Steps")
        lines.append("")

        for step in manifest.steps:
            lines.append(f"### {step.id}")
            lines.append(f"- Command: {step.command}")
            lines.append(f"- Status: {step.status}")
            lines.append(f"- Duration: {step.duration_sec}")

            if step.metrics:
                lines.append("- Metrics:")

                for key, value in step.metrics.items():
                    lines.append(f"  - {key}: {value}")

            if step.errors:
                lines.append("- Errors:")

                for error in step.errors:
                    lines.append(f"  - {error}")

            lines.append("")

        return "\n".join(lines)

    def generate_json(self, manifest: BatchManifest) -> dict:
        return {
            "batch_id": manifest.batch_id,
            "batch_run_id": manifest.batch_run_id,
            "status": manifest.status,
            "duration_sec": manifest.duration_sec,
            "steps": [
                {
                    "id": step.id,
                    "command": step.command,
                    "status": step.status,
                    "duration_sec": step.duration_sec,
                    "metrics": step.metrics,
                    "errors": step.errors,
                }
                for step in manifest.steps
            ],
        }

    def write_reports(
        self,
        manifest: BatchManifest,
        output_dir: str | Path,
    ) -> None:
        reports_dir = Path(output_dir) / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        markdown_path = reports_dir / "batch_report.md"
        json_path = reports_dir / "batch_report.json"

        markdown_path.write_text(
            self.generate_markdown(manifest),
            encoding="utf-8",
        )

        json_path.write_text(
            json.dumps(
                self.generate_json(manifest),
                indent=2,
                ensure_ascii=False,
            ) + "\n",
            encoding="utf-8",
        )
