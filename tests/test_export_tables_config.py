from __future__ import annotations

from pathlib import Path

from aforix.export.tables.config import (
    get_export_root,
    get_normalized_root,
    load_config,
)


def test_export_tables_honors_main_config_paths():
    repo_root = Path(__file__).resolve().parents[1]
    config_path = repo_root / "configs" / "examples" / "main.yaml"

    config = load_config(config_path)

    assert get_normalized_root(config) == (
        repo_root / "database" / "normalized"
    ).resolve()

    assert get_export_root(config) == (
        repo_root / "outputs" / "tables"
    ).resolve()



def test_export_tables_legacy_config_still_resolves(tmp_path):
    config_path = tmp_path / "main.yaml"
    config_path.write_text(
        """
project:
  database_root: db_legacy
  runs_root: runs_legacy
export_tables:
  normalized_root: db_legacy/normalized_custom
  output_dir: out_legacy/tables
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert get_normalized_root(config) == (
        tmp_path / "db_legacy" / "normalized_custom"
    ).resolve()
    assert get_export_root(config) == (
        tmp_path / "out_legacy" / "tables"
    ).resolve()

def test_export_tables_standalone_examples_layout_uses_project_root(tmp_path):
    project_root = tmp_path / "project"
    config_dir = project_root / "configs" / "examples"
    config_dir.mkdir(parents=True)

    config_path = config_dir / "main.yaml"
    config_path.write_text(
        """
paths:
  database_root: database
  runs_root: runs
export:
  tables:
    input_dir: database/normalized
    output_dir: outputs/tables
""".lstrip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert get_normalized_root(config) == (
        project_root / "database" / "normalized"
    ).resolve()
    assert get_export_root(config) == (
        project_root / "outputs" / "tables"
    ).resolve()
