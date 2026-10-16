"""M9 metadata policy compatibility and observable ingestion behavior."""
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest
import yaml

from aforix.ingest import m9


def example_config():
    return yaml.safe_load(Path('configs/examples/main.yaml').read_text(encoding='utf-8'))


def summary(station='133.0'):
    return dict(station_id=station, station_name='  Pasarela  ',
                measurement_start=datetime.fromisoformat('2026-07-03T23:59:58-03:00'),
                measurement_end=datetime.fromisoformat('2026-07-04T00:01:00-03:00'),
                q_total_m3s=4.5, area_total_m2=8., hydraulic_radius_m=.8)


@pytest.mark.parametrize('station', ['133.0', '00133', 'p71', 'P71.TXT.WAD', 'a/b', '', None])
def test_example_policy_preserves_legacy_metadata(station):
    data = summary(station)
    path = Path('raw/P7071/transect.mat')
    configured = m9._extract_m9_metadata(data, path, example_config()['ingest']['m9'])
    legacy = m9._extract_m9_metadata(data, path, {})
    assert configured == legacy
    assert configured['measurement_date'] == '20260703'
    assert configured['measurement_time'] == '235958'
    if not station:
        assert configured['station_id'] == 'P7071'


def test_unknown_station_and_partial_policy_keep_defaults():
    data = summary(None)
    got = m9._extract_m9_metadata(data, Path('raw/transect.mat'), {'metadata_policy': {
        'station_name': {'sources': [{'type': 'constant', 'value': 'Nuevo nombre'}]}}})
    assert got == dict(station_id='UNKNOWN', station_name='Nuevo nombre',
                       measurement_date='20260703', measurement_time='235958')


def test_policy_priority_transforms_and_timezone_aware_start():
    policy = example_config()['ingest']['m9']
    policy['metadata_policy']['station_id'] = {
        'sources': [{'type': 'raw_field', 'key': 'absent'},
                    {'type': 'filename_regex', 'pattern': r'P(\d+)'},
                    {'type': 'raw_field', 'key': 'station_id'}],
        'normalize': {'zero_pad': 5}}
    for field, output in [('measurement_date', '%Y%m%d'), ('measurement_time', '%H%M%S')]:
        policy['metadata_policy'][field] = {
            'sources': [{'type': 'raw_field', 'key': 'measurement_start'}],
            'normalize': {'input_formats': ['%Y-%m-%dT%H:%M:%S%z'], 'output_format': output}}
    got = m9._extract_m9_metadata(summary(), Path('P42_test.mat'), policy)
    assert got['station_id'] == '00042'
    assert got['measurement_date'] == '20260703'  # No conversion to next-day UTC.
    assert got['measurement_time'] == '235958'


def test_yaml_override_reaches_summary_points_and_filenames(tmp_path, monkeypatch):
    cfg = example_config()
    cfg['paths']['raw_data_dir'] = str(tmp_path / 'raw')
    (tmp_path / 'runs').mkdir()
    cfg['ingest']['flowtracker']['spec_path'] = str(Path('configs/specs/flowtracker.yaml').resolve())
    cfg['normalize']['registry_dir'] = str(Path('configs/normalization').resolve())
    raw = tmp_path / 'raw/M9'; raw.mkdir(parents=True)
    source = raw / 'transect.mat'; source.touch()
    parsed = {'summary': summary(), 'points': [{'sample_number': 1, 'depth_m': .7, 'distance_m': 1.}]}
    original = deepcopy(parsed)
    run_dir = tmp_path / 'run'; run_dir.mkdir()
    monkeypatch.setattr(m9, 'parse_m9_mat', lambda *args, **kwargs: deepcopy(parsed))
    monkeypatch.setattr(m9, 'create_run', lambda *args: run_dir)
    desired = dict(station_id='0099', station_name='Sitio nuevo',
                   measurement_date='20260702', measurement_time='120001')
    for key, value in desired.items():
        cfg['ingest']['m9']['metadata_policy'][key] = {'sources': [{'type': 'constant', 'value': value}]}
    config = tmp_path / 'main.yaml'
    config.write_text(yaml.safe_dump(cfg), encoding='utf-8')
    m9.run(config)
    for group in ('Summary', 'Points'):
        path = run_dir / f'outputs/raw_canonical/m9/{group}/0099_20260702_120001_transect_{group}.csv'
        row = pd.read_csv(path, dtype=str, keep_default_na=False).iloc[0]
        for key, value in desired.items():
            assert row[key] == value
        if group == 'Summary':
            assert float(row.q_total_m3s) == 4.5
            assert float(row.hydraulic_radius_m) == .8
            assert row.measurement_end_date == '20260704'
            assert row.manufacturer == 'SonTek'
            assert row.model == 'M9'
        else:
            assert float(row.depth_m) == .7
    assert parsed == original


def test_invalid_policy_is_not_silently_ignored():
    with pytest.raises(ValueError, match='Unsupported metadata extraction strategy'):
        m9._extract_m9_metadata(summary(), Path('a.mat'), {'metadata_policy': {
            'station_id': {'strategy': 'unsupported'}}})
