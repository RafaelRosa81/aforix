from pathlib import Path

from aforix.batch.manifest import BatchManifest, StepManifest
from aforix.batch.report import BatchReportGenerator


report_generator = BatchReportGenerator()


def _manifest() -> BatchManifest:
    return BatchManifest(
        batch_id="test_batch",
        batch_run_id="20260101_000000",
        status="success",
        started_at="2026-01-01T00:00:00",
        duration_sec=1.5,
        steps=[
            StepManifest(
                id="normalize",
                command="normalize.run",
                status="success",
                duration_sec=1.0,
                metrics={"metrics_available": True},
            )
        ],
    )


def test_generate_markdown_contains_batch_id() -> None:
    markdown = report_generator.generate_markdown(_manifest())

    assert "test_batch" in markdown


def test_write_reports_creates_files(tmp_path: Path) -> None:
    report_generator.write_reports(_manifest(), tmp_path)

    reports_dir = tmp_path / "reports"

    assert (reports_dir / "batch_report.md").exists()
    assert (reports_dir / "batch_report.json").exists()
    assert (reports_dir / "batch_report.csv").exists()
