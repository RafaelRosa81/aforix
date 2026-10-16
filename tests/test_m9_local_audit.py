"""Exercise the actual CLI pipeline and serialized reports, using synthetic MATs."""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.io import savemat


def audit_module():
    path = Path(__file__).resolve().parents[1] / 'scripts/audit_m9_local.py'
    spec = importlib.util.spec_from_file_location('audit_m9_local', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_mat(path, seconds=836393424., n=12):
    savemat(path, {
        'SiteInfo': {'Station_Number': '133', 'Site_Name': 'test'},
        'SystemHW': {'SerialNumber': '4980', 'FirmwareVersion': 4},
        'System': {'Time': seconds + np.arange(n)},
        'Setup': {'coordinateSystem': 2, 'startEdge': 0,
                  'Edges_0__DistanceToBank': 1., 'Edges_1__DistanceToBank': 1.5},
        'Summary': {'Total_Q': np.linspace(0, 2.4, n), 'Area': 12.,
                    'Depth': np.ones(n), 'Track': np.column_stack([np.arange(n), np.zeros(n)]),
                    'Mean_Vel': np.column_stack([np.zeros(n), np.full(n, .2)]),
                    'Boat_Vel': np.zeros((n, 2))},
    })


def test_local_audit_exports_good_file_and_reports_failure_and_exclusion(tmp_path):
    (tmp_path / 'pyproject.toml').write_text('[project]\nname = \"outer-repo\"\n')
    raw = tmp_path / 'raw'; raw.mkdir()
    write_mat(raw / 'good.mat')
    write_mat(raw / 'short.mat', seconds=836394424., n=8)
    (raw / 'bad.mat').write_bytes(b'not a MAT')
    (raw / 'excluded.mat').write_bytes(b'excluded')
    audit = audit_module()
    code = audit.main(['--raw-dir', str(raw), '--output-root', str(tmp_path / 'results'),
                       '--exclude', 'excluded.mat'])
    root = next((tmp_path / 'results').iterdir())
    manifest = pd.read_csv(root / 'audit_manifest.csv', keep_default_na=False)
    statuses = {Path(row.source_file).name: row.status for row in manifest.itertuples()}
    assert not (tmp_path / 'runs').exists()
    assert not (tmp_path / 'database').exists()
    assert not (tmp_path / 'outputs').exists()
    assert code == 1
    assert statuses == {'good.mat': 'OK', 'short.mat': 'REVISAR', 'bad.mat': 'ERROR', 'excluded.mat': 'EXCLUIDO'}
    assert json.loads((root / 'audit_summary.json').read_text())['actual_sih_import_tested'] is False
    short = manifest[manifest.ive == 'not_applicable'].iloc[0]
    short_aforo = pd.read_csv(short.aforo_file, keep_default_na=False)
    assert short_aforo.loc[0, 'error_IVE'] == short_aforo.loc[0, 'incertidumbre_IVE'] == ''
    good = manifest[manifest.status == 'OK'].iloc[0]
    # Verify the checker catches tampering of the delivered CSV, not just successful exit codes.
    aforo = pd.read_csv(good.aforo_file)
    aforo.loc[0, 'error_IVE'] = 99
    aforo.to_csv(good.aforo_file, index=False)
    import yaml
    from aforix.analysis.uncertainty.calculator import IVEParameters
    summary = pd.read_csv(root / 'database/normalized/m9/Summary.csv', dtype=str).iloc[0]
    meta = pd.read_csv(root / 'outputs/sih/sih_export_metadata.csv', dtype=str, keep_default_na=False).iloc[0]
    config = yaml.safe_load((root / 'configs/sih/sih.yaml').read_text(encoding='utf-8'))
    errors = audit.check_export(root, summary, meta, IVEParameters(left_bank_mode='zero', right_bank_mode='zero'), config)
    assert 'Error IVE' in errors
    assert 'IVE absoluto XLSX/CSV' in errors


def test_local_audit_flags_ambiguous_keys_without_averaging(tmp_path):
    raw = tmp_path / 'raw'; raw.mkdir()
    write_mat(raw / 'original.mat')
    write_mat(raw / 'processed.mat')
    audit = audit_module()
    assert audit.main(['--raw-dir', str(raw), '--output-root', str(tmp_path / 'results')]) == 1
    root = next((tmp_path / 'results').iterdir())
    manifest = pd.read_csv(root / 'audit_manifest.csv')
    assert manifest.status.tolist() == ['REVISAR', 'REVISAR']
    assert not (root / 'selection.csv').exists()
    assert len(pd.read_csv(root / 'database/normalized/m9/Summary.csv')) == 2


def test_isolation_overrides_operational_absolute_paths():
    audit = audit_module()
    cfg = dict(paths={}, ingest={'m9': {}}, build_groups={}, normalize={}, validation={})
    sih = {'sih': {'inputs': {}, 'output': {'output_dir': '/production',
                                         'output_names': {'aforos': '/production/aforo.csv'}}}}
    audit.isolate_paths(cfg, sih)
    assert cfg['paths']['runs_root'] == 'runs'
    assert cfg['normalize']['output_dir'] == 'database/normalized'
    assert cfg['validation']['output_dir'] == 'database/validation'
    assert sih['sih']['output']['output_dir'] == 'outputs/sih'
    assert '/' not in sih['sih']['output']['output_names']['aforos']


def test_missing_summary_values_are_reviewed_without_hiding_export_changes(tmp_path):
    from scipy.io import loadmat
    import yaml
    from aforix.analysis.uncertainty.calculator import IVEParameters
    raw = tmp_path / 'raw'; raw.mkdir()
    source = raw / 'missing_area.mat'
    write_mat(source)
    data = loadmat(source, simplify_cells=True)
    data['Summary']['Area'] = np.nan
    savemat(source, {k: v for k, v in data.items() if not k.startswith('__')})
    audit = audit_module()
    assert audit.main(['--raw-dir', str(raw), '--output-root', str(tmp_path / 'results')]) == 1
    root = next((tmp_path / 'results').iterdir())
    record = pd.read_csv(root / 'audit_manifest.csv', keep_default_na=False).iloc[0]
    assert record.status == 'REVISAR'
    assert 'area_total_m2: dato normalizado ausente' in record.message
    assert record.ive == 'calculated'
    summary = pd.read_csv(root / 'database/normalized/m9/Summary.csv', dtype=str, keep_default_na=False).iloc[0]
    meta = pd.read_csv(root / 'outputs/sih/sih_export_metadata.csv', dtype=str, keep_default_na=False).iloc[0]
    config = yaml.safe_load((root / 'configs/sih/sih.yaml').read_text(encoding='utf-8'))
    aforo = pd.read_csv(record.aforo_file, dtype=str, keep_default_na=False)
    assert aforo.loc[0, 'seccion'] == ''
    aforo.loc[0, 'seccion'] = '0'
    aforo.to_csv(record.aforo_file, index=False)
    errors = audit.check_export(root, summary, meta, IVEParameters(left_bank_mode='zero', right_bank_mode='zero'), config)
    assert 'seccion: valor exportado sin dato normalizado' in errors
