import csv
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
        csv_path = reports_dir / "batch_report.csv"

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

        self._write_csv(manifest, csv_path)

    def _write_csv(self, manifest: BatchManifest, path: Path) -> None:
        fieldnames = [
            "batch_id",
            "batch_run_id",
            "step_id",
            "command",
            "status",
            "duration_sec",
            "metrics_available",
            "cpu_start_percent",
            "cpu_end_percent",
            "ram_start_mb",
            "ram_end_mb",
            "ram_peak_mb",
            "errors",
        ]

        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()

            for step in manifest.steps:
                metrics = step.metrics or {}
                writer.writerow(
                    {
                        "batch_id": manifest.batch_id,
                        "batch_run_id": manifest.batch_run_id,
                        "step_id": step.id,
                        "command": step.command,
                        "status": step.status,
                        "duration_sec": step.duration_sec,
                        "metrics_available": metrics.get("metrics_available"),
                        "cpu_start_percent": metrics.get("cpu_start_percent"),
                        "cpu_end_percent": metrics.get("cpu_end_percent"),
                        "ram_start_mb": metrics.get("ram_start_mb"),
                        "ram_end_mb": metrics.get("ram_end_mb"),
                        "ram_peak_mb": metrics.get("ram_peak_mb"),
                        "errors": " | ".join(step.errors),
                    }
                )
