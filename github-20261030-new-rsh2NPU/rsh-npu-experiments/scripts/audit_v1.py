"""Audit V1 raw evidence and describe paired effects without dropping samples."""
from pathlib import Path
import hashlib
import json
import math
import statistics

import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def audit() -> dict:
    dest=ROOT/'results/v1';state=json.loads((dest/'progress.json').read_text())
    assert state['state']=='complete' and state['stop_required']
    assert len(state['completed'])==len(set(state['completed']))==81
    manifest=json.loads((dest/'manifest.json').read_text());source=dest/'source_snapshot'
    for name,h in manifest['source_hashes'].items():
        assert hashlib.sha256((source/name).read_bytes()).hexdigest()==h,name
    assert hashlib.sha256((source/'scripts/run_v1.py').read_bytes()).hexdigest()==manifest['controller_sha256']
    assert hashlib.sha256((ROOT/'results/v0/device_binary/rsh_runner').read_bytes()).hexdigest()==manifest['executable_sha256']
    for name,h in manifest['inputs'].items():assert hashlib.sha256((ROOT/'inputs'/name).read_bytes()).hexdigest()==h
    smoke=list((dest/'smoke').glob('*.json'));assert len(smoke)==20
    for f in smoke:
        x=json.loads(f.read_text());assert x['correctness'] and x['records'][0]['variant']=='V1'
    null=list((dest/'null_control').glob('*.json'));assert len(null)==9
    paired=list((dest/'measurements').rglob('*.json'));assert len(paired)==72
    null_ratios=[];null_medians=[]
    for f in null:
        x=json.loads(f.read_text());assert x['correctness'] and x['warmups']==10 and x['repeats']==30
        a,b=x['records'];assert a['variant']==b['variant']=='V0'
        assert len(a['samples_us'])==len(b['samples_us'])==30
        ratios=np.asarray(a['samples_us'])/np.asarray(b['samples_us'])
        null_ratios.extend(ratios.tolist());null_medians.append(float(np.median(ratios)))
    # Exploratory envelope, not an inferential significance threshold.
    noise_low=float(np.quantile(null_ratios,.05));noise_high=float(np.quantile(null_ratios,.95))
    summary=json.loads((dest/'summary.json').read_text());assert len(summary['rows'])==24
    rows=[];max_error=0.;timing_flags=[]
    for row in summary['rows']:
        meds=[[],[]];samples=[[],[]];paired_medians=[]
        for rep in range(3):
            f=dest/'measurements'/row['matrix']/f'N{row["n"]}'/f'run{rep}.json'
            x=json.loads(f.read_text());assert x['correctness'] and x['warmups']==10 and x['repeats']==30
            assert x['interleaving']=='randomized_per_call' and x['mixed_dispatch']=='not_used'
            assert x['cores_aic']==24 and x['cores_aiv']==48
            assert [r['variant'] for r in x['records']]==['V0','V1']
            for i,r in enumerate(x['records']):
                assert r['valid_rows']==r['m'] and r['n']==row['n']
                assert len(r['samples_us'])==30 and all(math.isfinite(v) and v>0 for v in r['samples_us'])
                if i==0:assert r['cube_groups']==r['k16_tiles']==0 and r['aiv_rows']==r['m']
                else:
                    assert r['cube_groups']==(r['m']+15)//16 and r['aiv_rows']==0
                    max_error=max(max_error,r['max_abs_error'])
                meds[i].append(statistics.median(r['samples_us']));samples[i].extend(r['samples_us'])
            paired_medians.append(float(np.median(np.asarray(x['records'][0]['samples_us'])/np.asarray(x['records'][1]['samples_us']))))
        assert meds[0]==row['v0_process_medians_us'] and meds[1]==row['v1_process_medians_us']
        np.testing.assert_allclose(paired_medians,row['paired_speedup_per_process'],rtol=1e-12)
        marker=ROOT/'cases_v1'/row['matrix']/f'N{row["n"]}'/'V1'/'metadata.json'
        a=json.loads(marker.read_text());b=json.loads((ROOT/'cases_v0'/row['matrix']/f'N{row["n"]}'/'V0'/'metadata.json').read_text())
        for k in ['ptr','cols','values','rhs','golden']:assert a['files_sha256'][k]==b['files_sha256'][k]
        r=row|{'v0_iqr_us':float(np.quantile(samples[0],.75)-np.quantile(samples[0],.25)),
               'v1_iqr_us':float(np.quantile(samples[1],.75)-np.quantile(samples[1],.25)),
               'all_three_faster':all(v>1 for v in paired_medians),
               'all_three_slower':all(v<1 for v in paired_medians),
               'gain_above_null_envelope':all(v>noise_high for v in paired_medians),
               'loss_below_null_envelope':all(v<noise_low for v in paired_medians),
               'v0_process_max_min':max(meds[0])/min(meds[0]),'v1_process_max_min':max(meds[1])/min(meds[1])}
        if max(r['v0_process_max_min'],r['v1_process_max_min'])>1.10:timing_flags.append({'matrix':row['matrix'],'n':row['n'],'v0_ratio':r['v0_process_max_min'],'v1_ratio':r['v1_process_max_min']})
        rows.append(r)
    result={'passed':True,'version':'V1','configurations':24,'paired_processes':72,'null_processes':9,
            'v1_samples':2160,'paired_v0_samples':2160,'null_samples':540,'v1_max_abs_error':max_error,
            'null_paired_ratio_p05_p95':[noise_low,noise_high],'null_process_median_range':[min(null_medians),max(null_medians)],
            'median_speedup_gt_1':sum(r['paired_speedup']>1 for r in rows),
            'all_three_faster':sum(r['all_three_faster'] for r in rows),
            'gain_above_null_envelope':sum(r['gain_above_null_envelope'] for r in rows),
            'all_three_slower':sum(r['all_three_slower'] for r in rows),
            'geomean_paired_speedup':math.exp(statistics.mean(math.log(r['paired_speedup']) for r in rows)),
            'timing_flags':timing_flags,'rows':rows,
            'limits':'Exploratory controlled-backend results; null quantiles are descriptive, not a significance test. Three processes are not proof of generalization.',
            'stop_required':True,'next_version':'V2'}
    (dest/'local_audit.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},ensure_ascii=False))
    return result


if __name__=='__main__':audit()
