from __future__ import annotations

from pathlib import Path

import pytest

from aforix.config.paths import config_root_from_path, resolve_config_path
from aforix.normalize.run import _get_project_root as normalize_root
from aforix.validation.common import project_root_from_config as validation_root
from aforix.ingest.flowtracker import _get_project_root as flowtracker_root
from aforix.ingest.molinete import _get_project_root as molinete_root
from aforix.ingest.nivus import _get_project_root as nivus_root
from aforix.groups.build import _get_project_root as groups_root
from aforix.analysis.quality.config import _project_root_from_config as quality_root
from aforix.analysis.correlation.config import _project_root_from_config as correlation_root
from aforix.export.sih.config import _infer_repo_root as sih_root
from aforix.export.tables.config import _infer_repo_root as tables_root
from aforix.analysis.section_profiles.runner import _resolve_paths as section_profile_paths
from aforix.analysis.stage_discharge.runner import _resolve_paths as stage_discharge_paths


ROOT_RESOLVERS = [
    config_root_from_path,
    normalize_root,
    validation_root,
    flowtracker_root,
    molinete_root,
    nivus_root,
    groups_root,
    quality_root,
    correlation_root,
    sih_root,
    tables_root,
]


@pytest.mark.parametrize('resolver', ROOT_RESOLVERS)
def test_config_root_consumers_anchor_standalone_config_beside_file(tmp_path, resolver):
    config_dir = tmp_path / 'job'
    config_dir.mkdir()
    config_path = config_dir / 'main.yaml'
    config_path.write_text('project: {}\npaths: {}\n', encoding='utf-8')

    assert resolver(config_path) == config_dir.resolve()


@pytest.mark.parametrize('resolver', ROOT_RESOLVERS)
def test_config_root_consumers_honor_documented_examples_layout(tmp_path, resolver):
    project_root = tmp_path / 'project'
    config_dir = project_root / 'configs' / 'examples'
    config_dir.mkdir(parents=True)
    config_path = config_dir / 'main.yaml'
    config_path.write_text('project: {}\npaths: {}\n', encoding='utf-8')

    assert resolver(config_path) == project_root.resolve()

@pytest.mark.parametrize("module_name", ["sih", "normalization"])
def test_config_root_consumers_honor_module_config_layout(tmp_path, module_name):
    project_root = tmp_path / "project"
    config_dir = project_root / "configs" / module_name
    config_dir.mkdir(parents=True)
    config_path = config_dir / "module.yaml"
    config_path.write_text("project: {}\npaths: {}\n", encoding="utf-8")

    assert config_root_from_path(config_path) == project_root.resolve()


def test_sih_root_honors_documented_sih_layout(tmp_path):
    project_root = tmp_path / "project"
    config_dir = project_root / "configs" / "sih"
    config_dir.mkdir(parents=True)
    config_path = config_dir / "sih.yaml"
    config_path.write_text("sih: {}\n", encoding="utf-8")

    assert sih_root(config_path) == project_root.resolve()


def test_resolve_config_path_anchors_standalone_paths_beside_config(tmp_path, monkeypatch):
    config_dir = tmp_path / "job"
    config_dir.mkdir()
    config_path = config_dir / "main.yaml"
    config_path.write_text("project: {}\npaths: {}\n", encoding="utf-8")
    unrelated = tmp_path / "elsewhere"
    unrelated.mkdir()
    monkeypatch.chdir(unrelated)

    assert resolve_config_path(config_path, "database/normalized") == (
        config_dir / "database" / "normalized"
    ).resolve()


def test_section_profiles_paths_use_config_root(tmp_path, monkeypatch):
    config_dir = tmp_path / "job"
    config_dir.mkdir()
    config_path = config_dir / "main.yaml"
    config_path.write_text("project: {}\npaths: {}\n", encoding="utf-8")
    unrelated = tmp_path / "elsewhere"
    unrelated.mkdir()
    monkeypatch.chdir(unrelated)

    normalized_root, output_root = section_profile_paths(
        config_path,
        {
            "input_dirs": {"normalized_root": "database/normalized"},
            "output": {"run_output_root": "runs/analysis_section_profiles"},
        },
    )

    assert normalized_root == (config_dir / "database" / "normalized").resolve()
    assert output_root == (config_dir / "runs" / "analysis_section_profiles").resolve()


def test_stage_discharge_paths_use_config_root(tmp_path, monkeypatch):
    config_dir = tmp_path / "job"
    config_dir.mkdir()
    config_path = config_dir / "main.yaml"
    config_path.write_text("project: {}\npaths: {}\n", encoding="utf-8")
    unrelated = tmp_path / "elsewhere"
    unrelated.mkdir()
    monkeypatch.chdir(unrelated)

    normalized_root, manual_root, output_root = stage_discharge_paths(
        config_path,
        {
            "input_dirs": {
                "normalized_root": "database/normalized",
                "manual_stage_root": "database/external/normalized/manual_stage",
            },
            "output": {"run_output_root": "runs/analysis_stage_discharge"},
        },
    )

    assert normalized_root == (config_dir / "database" / "normalized").resolve()
    assert manual_root == (
        config_dir / "database" / "external" / "normalized" / "manual_stage"
    ).resolve()
    assert output_root == (config_dir / "runs" / "analysis_stage_discharge").resolve()

