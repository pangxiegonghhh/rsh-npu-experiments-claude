"""Validate the recovered V0 evidence before calling the version complete."""
from pathlib import Path
import hashlib
import json
import math
import statistics
import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def audit():
    dest=ROOT/'results/v0'
    state=json.loads((dest/'progress.json').read_text())
    assert state['state']=='complete' and state['stop_required']
    assert len(state['completed'])==len(set(state['completed']))==72
    provenance=json.loads((dest/'manifest.json').read_text())
    source=dest/'source_snapshot' if (dest/'source_snapshot').exists() else ROOT
    for name,h in provenance['sources'].items():
        assert hashlib.sha256((source/name).read_bytes()).hexdigest()==h,name
    assert hashlib.sha256((source/'scripts/run_v0.py').read_bytes()).hexdigest()==provenance['controller_sha256']
    for name,h in provenance['inputs'].items():
        candidate=ROOT/'inputs'/name
        if not candidate.exists():candidate=ROOT.parent/'spmm-k-slack/data/csr'/name
        assert hashlib.sha256(candidate.read_bytes()).hexdigest()==h,name
    smoke=list((dest/'smoke').glob('*.json'))
    assert len(smoke)==20
    for f in smoke:
        x=json.loads(f.read_text());assert x['correctness'] and x['records'][0]['variant']=='V0'
    measurements=list((dest/'measurements').rglob('*.json'))
    assert len(measurements)==72
    table=[];errors=[]
    summary=json.loads((dest/'summary.json').read_text())
    assert summary['correctness'] and summary['configurations']==24
    for row in summary['rows']:
        medians=[];samples=[]
        for run in range(3):
            f=dest/'measurements'/row['matrix']/f'N{row["n"]}'/f'run{run}.json'
            x=json.loads(f.read_text());assert x['correctness'] and x['warmups']==10 and x['repeats']==30
            assert x['cores_aic']==0 and x['cores_aiv']==48 and x['mixed_dispatch']=='not_used'
            assert x['interleaving']=='single_variant' and x['b_rotation']==2
            r=x['records'][0]
            assert r['variant']=='V0' and r['cube_groups']==r['k16_tiles']==0
            assert r['valid_rows']==r['aiv_rows']==r['m']
            assert len(r['samples_us'])==30 and all(math.isfinite(t) and t>0 for t in r['samples_us'])
            medians.append(statistics.median(r['samples_us']));samples.extend(r['samples_us']);errors.append(r['max_abs_error'])
        assert medians==row['process_medians_us']
        assert statistics.median(medians)==row['median_us']
        table.append({'matrix':row['matrix'],'n':row['n'],'median_us':row['median_us'],
                      'process_min_us':min(medians),'process_max_us':max(medians),
                      'pooled_iqr_us':float(np.quantile(samples,.75)-np.quantile(samples,.25))})
    result={'passed':True,'version':'V0','smoke_cases':20,'configurations':24,
            'processes':72,'timed_samples':2160,'max_abs_error':max(errors),'rows':table,
            'timing_review_required':[x for x in table if x['process_max_us']/x['process_min_us']>1.10],
            'timing_review_rule':'Post-measurement diagnostic flag: process median max/min > 1.10; no samples excluded.',
            'next_version':'V1 after reviewing V0 timing flags','stop_required':True}
    (dest/'local_audit.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},ensure_ascii=False))
    return result


if __name__=='__main__':
    audit()
