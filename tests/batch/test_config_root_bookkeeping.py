from __future__ import annotations

from pathlib import Path

from aforix.batch import default_registry


def test_raw_input_dir_uses_config_root(tmp_path):
    config_dir = tmp_path / "job"
    config_dir.mkdir()
    config_path = config_dir / "main.yaml"
    cfg = {
        "paths": {"raw_data_dir": "data/raw"},
        "ingest": {"flowtracker": {"raw_subdir": "flowtracker"}},
    }

    assert default_registry._raw_input_dir(
        config_path,
        cfg,
        "flowtracker",
    ) == (config_dir / "data" / "raw" / "flowtracker").resolve()


def test_normalize_bookkeeping_uses_config_root(tmp_path, monkeypatch):
    config_dir = tmp_path / "job"
    config_dir.mkdir()
    config_path = config_dir / "main.yaml"
    input_dir = config_dir / "database" / "raw_canonical"
    output_dir = config_dir / "database" / "normalized"
    run_dir = config_dir / "runs" / "normalize" / "run1"
    input_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)
    run_dir.mkdir(parents=True)
    (input_dir / "input.csv").write_text("a\n1\n", encoding="utf-8")
    (output_dir / "Summary.csv").write_text("a\n1\n", encoding="utf-8")
    (run_dir / "manifest.txt").write_text("ok", encoding="utf-8")

    cfg = {
        "normalize": {
            "input_dir": "database/raw_canonical",
            "output_dir": "database/normalized",
        }
    }

    monkeypatch.setattr(
        default_registry,
        "_load_validated_config_from_params",
        lambda params: config_path,
    )
    monkeypatch.setattr(default_registry, "load_config", lambda path: cfg)
    monkeypatch.setattr(default_registry, "normalize_database", lambda path: run_dir)

    result = default_registry._normalize_run({"config": str(config_path)})

    assert str(output_dir.resolve()) in result.outputs
    assert str((output_dir / "Summary.csv").resolve()) in result.outputs
    assert result.metrics["files_written"] == 1
