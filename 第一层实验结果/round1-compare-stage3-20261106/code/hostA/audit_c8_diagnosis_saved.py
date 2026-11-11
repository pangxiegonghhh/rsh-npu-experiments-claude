"""Read-only audit of the saved Reddit C8-METIS diagnostic evidence."""
import hashlib
import json
import math
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
KEY = 'stage3-reddit__C8-METIS__W16__seed0'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(path):
    return json.loads(path.read_text())

def main():
    root = BASE/'work/stage3-diagnostics'/KEY
    command_path = BASE/'logs'/('stage3-diag-'+KEY+'.command.json')
    catalog_path = BASE/'work/stage3-eval-catalog'/(KEY+'.json')
    own_path = BASE/'work/stage3-evaluations'/KEY/'rows.json'
    paths = [root/name for name in ['status.json', 'diag.json', 'phases.json', 'groups.json', 'candidate-diagnostics.json']]
    paths += [command_path, catalog_path, own_path]
    before = {str(p.relative_to(BASE)):digest(p) for p in paths}
    command, catalog, own = load(command_path), load(catalog_path), load(own_path)
    status, diag, phases = [load(root/name) for name in ['status.json','diag.json','phases.json']]
    assert command['status'] == 'FINISHED' and command['exitcode'] == 0
    assert command['pid'] == 38738 and command['method_limit_seconds'] == 7200
    assert 0 < command['actual_method_seconds'] < 7200
    assert abs(command['ended_at']-command['method_started_at']-command['actual_method_seconds']) < 0.001
    assert command['queue_seconds'] > 6600
    assert status['status'] == diag['status'] == 'OK'
    assert 0 < status['seconds'] <= command['actual_method_seconds']
    assert 0 < diag['diagnostic_seconds'] <= status['seconds']
    assert (diag['matrix'],diag['member'],diag['W'],diag['diag'],diag['tau']) == ('reddit','C8-METIS',16,'A0',153)
    assert len(phases) == 15 and [p['offset'] for p in phases] == diag['offsets_used'] == list(range(1,16))
    average = sum(p['T'] for p in phases)/15
    assert math.isclose(average,diag['T_full_phase'],rel_tol=0,abs_tol=1e-8)
    assert math.isclose(average-diag['T_full'],diag['align_premium'],rel_tol=0,abs_tol=1e-8)
    full = [r for r in own if r['diag']=='A0' and r['tau']=='none' and r['source']=='own' and r['status']=='OK']
    assert len(full) == 2 and {r['d_rule'] for r in full} == {'own','D-greedy'}
    assert all(r['T']==diag['T_full']==4466045 for r in full)
    assert all(r['sumU']==71347415 for r in full)
    assert load(root/'candidate-diagnostics.json') == catalog['diagnostics']
    assert load(root/'groups.json') == []
    # C8 exact-capacity repair records target_sizes; evaluation_group_sizes
    # belongs to the C2/C3 schema. Match the producer's group_stats fallback.
    sizes = catalog['diagnostics']['target_sizes']
    assert len(sizes)==14561 and sorted(sizes)==[5]+[16]*14560
    assert diag['groups_after']==14561 and diag['short_after']==1 and diag['groups_cut_by_windows']==0
    pi_path = Path(catalog['runtime_path'])
    assert digest(pi_path)==catalog['sha256']=='92d13079c5e096bd2b861ad745e1b55d7a3e7da0201e0c1f4b2fd7aa05c79ee7'
    backend_paths=list((BASE/'logs/layout-context-backends').glob('38738-*.json'))
    assert len(backend_paths)==1
    backend=load(backend_paths[0])
    assert backend['pid']==command['pid'] and backend['matrix']=='reddit'
    assert backend['library_sha256']=='772c9c3425fda920badf5f97c8bd1888ca029e4547431383647a3249fe4b07c9'
    assert command['source_sha256']['scripts/diagnose_t23.py']==digest(BASE/'scripts/diagnose_t23.py')
    assert before=={str(p.relative_to(BASE)):digest(p) for p in paths}
    receipt=dict(passed=True,scope='Saved diagnosis metadata/15 actual phases/T_full versus original own A0 full rows/source and actual process backend/unchanged original Pi. No CSR metrics regenerated; no physical guard-rescan claim.',case_id=KEY,status='OK',actual_method_seconds=command['actual_method_seconds'],queue_seconds=command['queue_seconds'],diagnostic_status_seconds=status['seconds'],T_full=diag['T_full'],T_full_phase=average,align_premium=diag['align_premium'],backend_evidence={str(backend_paths[0].relative_to(BASE)):digest(backend_paths[0])},files=before,no_scientific_rerun=True,whole_case_complete=False,posts_still_required=[53,153])
    out=BASE/'logs/stage3-C8METIS-diagnosis-audit.json'
    assert not out.exists()
    out.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:receipt[k] for k in ['passed','case_id','actual_method_seconds','T_full','T_full_phase','align_premium','whole_case_complete']}))

if __name__=='__main__':
    main()
