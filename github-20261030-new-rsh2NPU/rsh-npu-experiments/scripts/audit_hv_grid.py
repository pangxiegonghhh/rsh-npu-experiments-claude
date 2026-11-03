"""Independently recompute the conditional grid evidence and public selection."""
from pathlib import Path
import json,math,statistics,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.hv_cases import digest,save,check_split
from rsh.planner import Matrix

def audit_grid()->dict:
    dest=ROOT/'results/hv';grid=dest/'grid';mf=json.loads((grid/'manifest.json').read_text());state=json.loads((grid/'progress.json').read_text());assert state['state']=='complete' and len(state['completed'])==len(set(state['completed']))==72
    assert digest(dest/'source_snapshot/scripts/run_hv_grid.py')==mf['controller_sha256']
    for name,h in mf['source_hashes'].items():assert digest(dest/'source_snapshot'/name)==h
    result=json.loads((grid/'summary.json').read_text());assert result['new_configurations']==24 and result['reused_default_configurations']==3 and result['correctness'];assert len(result['options'])==9
    names=mf['development_matrices'];n=mf['n'];records=[]
    for option in result['options']:
        tau=(option['tau_nnz'],option['tau_inc']);td=f't{tau[0]}_{tau[1]}';aggs=[];gains=[]
        for rep in range(3):
            lat=[];rr=[]
            for name in names:
                if tau==(4,2):
                    x=json.loads((dest/'measurements'/name/f'N{n}'/f'run{rep}.json').read_text());ts=x['records'][2]['samples_us'];gain=1.
                else:
                    x=json.loads((grid/'measurements'/td/name/f'run{rep}.json').read_text());assert x['correctness'] and x['warmups']==10 and x['repeats']==30 and x['interleaving']=='randomized_per_call'
                    assert [r['variant'] for r in x['records']]==['V0','V2','H-V-base','H-V']
                    for r in x['records']:assert r['valid_rows']==r['m'] and len(r['samples_us'])==30 and all(math.isfinite(t) and t>0 for t in r['samples_us'])
                    ts=x['records'][3]['samples_us'];gain=statistics.median(a/b for a,b in zip(x['records'][2]['samples_us'],ts))
                lat.append(statistics.median(ts));rr.append(gain)
            aggs.append(math.exp(statistics.mean(math.log(t) for t in lat)));gains.append(math.exp(statistics.mean(math.log(t) for t in rr)))
        np.testing.assert_allclose(aggs,option['aggregate_latency_per_process_us'],rtol=1e-12);np.testing.assert_allclose(gains,option['paired_default_over_candidate_per_process'],rtol=1e-12);assert statistics.median(aggs)==option['aggregate_latency_us']
        if tau!=(4,2):
            for name in names:
                a=Matrix.load(str(ROOT/'inputs'/f'{name}.npz'));pd=grid/'plans'/td/name;route=json.loads((pd/'routing.json').read_text());check_split(a,route['split'])
                target=ROOT/'cases_hv_grid'/td/name/f'N{n}/H-V';meta=json.loads((target/'metadata.json').read_text());base=json.loads((ROOT/'cases_hv'/name/f'N{n}/H-V/metadata.json').read_text());assert meta['coverage']=='full' and digest(pd/'routing.json')==meta['routing_sha256']
                for key in ['ptr','cols','values','rhs','golden']:assert meta['files_sha256'][key]==base['files_sha256'][key]
                records.append({'tau':tau,'matrix':name,'coverage':'full'})
    best=min(result['options'],key=lambda x:(x['aggregate_latency_us'],mf['grid'].index([x['tau_nnz'],x['tau_inc']])));assert best==result['lowest_measured_latency']
    selected=best if all(t>result['selection_noise_limit'] for t in best['paired_default_over_candidate_per_process']) else result['options'][0];assert selected==result['selected_public_configuration']
    decision=json.loads((dest/'threshold_decision.json').read_text());assert decision['resolved'] and decision['grid_complete'] and (decision['selected_tau_nnz'],decision['selected_tau_inc'])==(selected['tau_nnz'],selected['tau_inc'])
    if not result['default_retained']:assert decision.get('holdout_complete'), 'Selected new public configuration requires holdout evaluation'
    report={'passed':True,'new_configurations':24,'reused_default_configurations':3,'new_processes':72,'four_variants_samples_each':2160,'default_retained':result['default_retained'],'selection':selected,'lowest_measured_latency':best,'descriptive_noise_limit':result['selection_noise_limit'],'routing_checks':records};save(grid/'local_audit.json',report);return report
if __name__=='__main__':print(json.dumps(audit_grid(),ensure_ascii=False))
