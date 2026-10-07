from __future__ import annotations

from pathlib import Path

from aforix.runs.manager import create_run


def test_create_run_respects_configured_runs_root(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    config_dir = project_root / "configs" / "examples"
    config_dir.mkdir(parents=True)

    raw_dir = project_root / "data" / "raw"
    raw_dir.mkdir(parents=True)

    config_path = config_dir / "acceptance.yaml"
    config_path.write_text(
        """
project:
  name: acceptance
paths:
  raw_data_dir: data/raw
  runs_root: runs_acceptance
  database_root: database_acceptance
""".lstrip(),
        encoding="utf-8",
    )

    # Ensure the assertion is not accidentally satisfied by the process cwd.
    monkeypatch.chdir(project_root)

    run_dir = create_run("ingest_flowtracker", config_path)

    expected_root = (project_root / "runs_acceptance" / "ingest_flowtracker").resolve()
    assert run_dir.resolve().parent == expected_root
    assert (run_dir / "config_used.yaml").exists()
    assert (run_dir / "manifest.json").exists()

def test_create_run_standalone_config_anchors_runs_root_to_config_dir(tmp_path, monkeypatch):
    config_dir = tmp_path / "job"
    config_dir.mkdir()

    raw_dir = config_dir / "data" / "raw"
    raw_dir.mkdir(parents=True)

    config_path = config_dir / "main.yaml"
    config_path.write_text(
        """
project:
  name: standalone
paths:
  raw_data_dir: data/raw
  runs_root: runs
  database_root: database
""".lstrip(),
        encoding="utf-8",
    )

    unrelated_cwd = tmp_path / "elsewhere"
    unrelated_cwd.mkdir()
    monkeypatch.chdir(unrelated_cwd)

    run_dir = create_run("ingest_flowtracker", config_path)

    expected_root = (config_dir / "runs" / "ingest_flowtracker").resolve()
    assert run_dir.resolve().parent == expected_root

