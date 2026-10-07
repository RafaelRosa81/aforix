from __future__ import annotations

from pathlib import Path

import pytest

from aforix.config.paths import config_root_from_path
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
