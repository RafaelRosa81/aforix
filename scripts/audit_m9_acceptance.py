from pathlib import Path
import shutil, tempfile, subprocess, yaml, pandas as pd
import argparse, sys
parser = argparse.ArgumentParser(description="Run the M9 pipeline in an isolated temporary project")
parser.add_argument("--raw-dir", type=Path, required=True)
args = parser.parse_args()
repo = Path(__file__).resolve().parents[1]
root = Path(tempfile.mkdtemp(prefix='aforix-m9-acceptance-'))
shutil.copytree(repo/'configs',root/'configs')
raw=root/'data/raw/M9'; raw.mkdir(parents=True); (root/'runs').mkdir()
for p in args.raw_dir.glob('*.mat'): shutil.copy2(p,raw/p.name)
cfg=root/'configs/examples/main.yaml'; c=yaml.safe_load(cfg.read_text()); c['build_groups']['sources']=['m9']; c['normalize']['sources']=['m9']; cfg.write_text(yaml.safe_dump(c,sort_keys=False))
def run(args):
 r=subprocess.run([sys.executable, '-c', 'from aforix.cli.main import app; app()', *args],cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 print(r.stdout); r.check_returncode()
for args in [['ingest','m9'],['build-groups'],['normalize','run']]: run([*args,'-c',str(cfg)])
from aforix.validation.run import run_validation
validation_dir = run_validation(cfg)
validation_status = pd.read_csv(validation_dir / "validation_summary.csv")
assert not validation_status.empty and validation_status["status"].eq("ok").all(), (
    f"Validation requires review: {validation_dir}"
)
print("PASS: M9 normalized validation")
s=pd.read_csv(root/'database/normalized/m9/Summary.csv',dtype=str)
sel=s[['station_id','measurement_date','measurement_time','instrument']].copy(); sel['export_id']=[f'M9_AUDIT_{i}' for i in range(len(sel))]; sel.to_csv(root/'selection.csv',index=False)
run(['export','sih','-c',str(cfg),'--sih-config',str(root/'configs/sih/sih.yaml'),'--selection-file',str(root/'selection.csv'),'--yes'])
print('ACCEPTANCE_ROOT',root)
assert len(s) == len(list(raw.glob('*.mat'))) > 0
metadata = pd.read_csv(root/'outputs/sih/sih_export_metadata.csv')
assert metadata['status'].eq('success').all()
assert metadata['ive_status'].eq('calculated').all()
from aforix.ingest.adapters.m9_mat import parse_m9_mat
from aforix.export.sih.ive_integration import prepare_sih_ive
from aforix.analysis.uncertainty.calculator import IVEParameters
import numpy as np
for _, row in s.iterrows():
    original = parse_m9_mat(Path(row['source_file']))
    selected, ive = prepare_sih_ive(root/'database/normalized', 'm9', row,
        IVEParameters(left_bank_mode='zero', right_bank_mode='zero'))
    assert len(selected) == len(original['points'])
    assert np.isclose(float(row['q_total_m3s']), original['summary']['q_total_m3s'])
    assert np.isclose(float(row['hydraulic_radius_m']), float(row['area_total_m2']) / float(row['wetted_perimeter_m']))
    files = list((root/'outputs/sih').glob(f"*_aforo_*_{row['measurement_time']}.csv"))
    assert len(files) == 1
    exported = pd.read_csv(files[0]).iloc[0]
    assert exported['id_instrumento'] == 503
    assert np.isclose(exported['caudal'], float(row['q_total_m3s']))
    assert np.isclose(exported['radio_hidraulico'], float(row['hydraulic_radius_m']))
    assert np.isclose(exported['error_IVE'], ive.absolute_uncertainty_m3s)
    assert np.isclose(exported['incertidumbre_IVE'], ive.relative_uncertainty_pct)
    assert np.isclose(float(row['uncertainty_ive_absolute_m3s']), ive.absolute_uncertainty_m3s)
    print(row['measurement_time'], len(selected), exported['caudal'], exported['radio_hidraulico'], exported['incertidumbre_IVE'], exported['error_IVE'])
print('PASS: traceability, samples, discharge, radius and common IVE engine')
