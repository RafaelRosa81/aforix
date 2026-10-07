from pathlib import Path
from types import SimpleNamespace

from aforix.batch import default_registry
from aforix.export.tables.cli import parse_args
from aforix.export.tables.runner import DEFAULT_EXPORT_GROUPING, ExportRequest


def test_export_tables_cli_defaults_to_flat_grouping():
    args = parse_args(["-c", "configs/examples/main.yaml", "--table", "Summary"])
    assert args.grouping == "none"


def test_export_request_uses_central_flat_default():
    assert DEFAULT_EXPORT_GROUPING == "none"
    assert ExportRequest(table="Summary").grouping == DEFAULT_EXPORT_GROUPING


def test_export_tables_batch_defaults_to_flat_grouping(monkeypatch, tmp_path):
    config_path = tmp_path / "main.yaml"
    config_path.write_text("project: {}\npaths: {}\n", encoding="utf-8")

    captured = {}

    monkeypatch.setattr(
        default_registry,
        "_load_validated_config_from_params",
        lambda params: config_path,
    )
    monkeypatch.setattr(
        default_registry,
        "load_export_tables_config",
        lambda path: {},
    )
    monkeypatch.setattr(
        default_registry,
        "get_normalized_root",
        lambda config: tmp_path / "database" / "normalized",
    )

    def fake_run_export_tables(config, request):
        captured["request"] = request
        return SimpleNamespace(
            output_file=tmp_path / "out.csv",
            metadata_file=tmp_path / "out_metadata.txt",
            row_count=1,
            effective_grouping="none",
            effective_pivot=False,
        )

    monkeypatch.setattr(
        default_registry,
        "run_export_tables",
        fake_run_export_tables,
    )

    result = default_registry._export_tables(
        {
            "config": str(config_path),
            "table": "Summary",
            "format": "csv",
        }
    )

    request = captured["request"]
    assert request.grouping == DEFAULT_EXPORT_GROUPING
    assert request.pivot is False
    assert result.metrics["grouping"] == "none"
    assert result.metrics["pivot"] is False


def test_export_tables_batch_reports_effective_flat_override(monkeypatch, tmp_path):
    config_path = tmp_path / "main.yaml"
    config_path.write_text("project: {}\npaths: {}\n", encoding="utf-8")

    captured = {}

    monkeypatch.setattr(
        default_registry,
        "_load_validated_config_from_params",
        lambda params: config_path,
    )
    monkeypatch.setattr(default_registry, "load_export_tables_config", lambda path: {})
    monkeypatch.setattr(
        default_registry,
        "get_normalized_root",
        lambda config: tmp_path / "database" / "normalized",
    )

    def fake_run_export_tables(config, request):
        captured["request"] = request
        return SimpleNamespace(
            output_file=tmp_path / "out.csv",
            metadata_file=tmp_path / "out_metadata.txt",
            row_count=2,
            effective_grouping="none",
            effective_pivot=False,
        )

    monkeypatch.setattr(default_registry, "run_export_tables", fake_run_export_tables)

    result = default_registry._export_tables(
        {
            "config": str(config_path),
            "table": "Summary",
            "format": "csv",
            "grouping": "daily",
            "flat": True,
        }
    )

    request = captured["request"]
    assert request.grouping == "daily"
    assert request.pivot is False
    assert result.metrics["grouping"] == "none"
    assert result.metrics["pivot"] is False

