"""Apply the saved prospective H-C rule; never launch a follow-up experiment."""
from pathlib import Path
import hashlib,json,math,statistics,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.hv_cases import save,digest

def main()->None:
    d=ROOT/'results/hc';mf=json.loads((d/'manifest.json').read_text());rule=json.loads((d/'prospective_threshold_rule.json').read_text())
    assert digest(d/'prospective_threshold_rule.json')==mf['prospective_threshold_rule_sha256']
    state=json.loads((d/'progress.json').read_text());assert state['state']=='default_complete'
    s=json.loads((d/'summary.json').read_text());medians=[]
    files=sorted((d/'null_control').glob('*.json'));assert len(files)==9
    for path in files:
        x=json.loads(path.read_text());a,b=x['records'];assert a['variant']==b['variant']=='H-C'
        assert x['correctness'] and len(a['samples_us'])==len(b['samples_us'])==30
        medians.append(statistics.median(u/v for u,v in zip(a['samples_us'],b['samples_us'])))
    guard=max([1.]+medians+[1./v for v in medians]);dev=s['development_hv_over_hc_per_process']
    switch=all(v>guard for v in dev)
    # A default configuration only consistently beats its strongest controls if
    # it beats both V0 and V2 in all independent processes, for every full-output point.
    strongest_all=all(all(v>1 for v in row[key]) for row in s['rows'] for key in ['v0_over_hc_per_process','v2_over_hc_per_process'])
    trigger=switch and not strongest_all
    decision={'version':'H-C','resolved':not trigger,'grid_required':trigger,'grid_complete':False,
              'default_retained':True,'selected_public_configuration':{'tau_nnz':4,'tau_inc':2},
              'rule_sha256':digest(d/'prospective_threshold_rule.json'),
              'null_process_median_ratios':medians,'null_process_noise_guard':guard,
              'development_hv_over_hc_per_process':dev,'development_all_three_faster':all(v>1 for v in dev),
              'development_strategy_switch_above_null_guard':switch,
              'default_consistently_beats_strongest_control_at_all_points':strongest_all,
              'historical_hv_threshold_decision_sha256':digest(ROOT/'results/hv/threshold_decision.json'),
              'historical_hv_threshold_result':'default4/2 retained;8/4 exploratory; old iteration guard unchanged',
              'reason':'H-C did not pass the prospectively declared strategy-switch guard; reuse completed H-V grid decision and keep frozen4/2' if not switch else ('H-C passed strategy-switch guard and needs its own separate threshold grid' if trigger else 'H-C exceeds both controlled baselines throughout; no new grid needed'),
              'limits':'Descriptive process-level noise check; not statistical significance. Small differences remain exploratory. H-V/H-C compares complete call scheduling, not pure tail arithmetic.',
              'stop_before':'H-Skip'}
    save(d/'threshold_decision.json',decision);print(json.dumps(decision,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
