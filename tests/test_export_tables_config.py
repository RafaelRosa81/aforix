from __future__ import annotations

from pathlib import Path

from aforix.export.tables.config import (
    get_export_root,
    get_normalized_root,
    load_config,
)


def test_export_tables_honors_main_config_acceptance_paths():
    repo_root = Path(__file__).resolve().parents[1]
    config_path = repo_root / "configs" / "examples" / "acceptance_real.yaml"

    config = load_config(config_path)

    assert get_normalized_root(config) == (
        repo_root / "database_acceptance" / "normalized"
    ).resolve()

    assert get_export_root(config) == (
        repo_root / "outputs_acceptance" / "tables"
    ).resolve()
