"""Fit the preregistered row/segment model and the separate API-count model.

Intervals describe timing variability across independently randomized blocks.
Model residuals and replay error are reported separately from those intervals.
"""
import csv
import json
from collections import defaultdict
from pathlib import Path
import numpy as np

root=Path(__file__).resolve().parent
rows=json.loads((root/'m4-manifest.json').read_text())
byname={r['name']:r for r in rows}
accepted=sorted((root/'results-blocks-v5').glob('b*-accepted.json'))
assert accepted, 'No accepted timing block'
samples={}
for journal in accepted:
    block=json.loads(journal.read_text())
    for group in block['groups']:
        for r in csv.DictReader((root/group['path']/'timing.csv').open()):
            geom=byname[r['case']]
            if (int(geom['dtype']=='FP32'),geom['n'])==(group['dtype'],group['N']):
                samples[block['block'],r['case']]=float(r['us_per_window'])
    assert sum(b==block['block'] for b,name in samples)==2592

def datum(block,row):
    name=row.get('alias_of',row['name'])
    while 'alias_of' in byname[name]:name=byname[name]['alias_of']
    return samples[block,name]

def fit(group,axis,holding_u=False):
    X=np.array([[1,r[axis]] if holding_u else [1,r['u'],r[axis]] for r in group],float)
    rank=int(np.linalg.matrix_rank(X))
    if rank<X.shape[1]:return dict(identifiable=False,rank=rank,columns=X.shape[1])
    coefficients=[];qualities=[];predictions=[]
    for block in [json.loads(p.read_text())['block'] for p in accepted]:
        y=np.array([datum(block,r) for r in group]);coef=np.linalg.lstsq(X,y,rcond=None)[0]
        pred=X@coef;den=float(np.sum((y-y.mean())**2))
        coefficients.append(coef.tolist());predictions.append(pred)
        qualities.append(dict(block=block,r2=1-float(np.sum((y-pred)**2))/den if den else None,
                              max_relative_error=float(np.max(np.abs(pred-y)/y))))
    betas=np.array(coefficients);mean=betas.mean(axis=0);n=len(betas)
    tcrit=2.093 if n==20 else (2.776 if n==5 else None)
    half=tcrit*betas.std(axis=0,ddof=1)/np.sqrt(n) if tcrit and n>1 else None
    return dict(identifiable=True,points=len(group),blocks=n,coefficients_by_block=coefficients,
                bytes_per_requested_row=group[0]['n']*group[0]['element_bytes'],
                byte_coefficient_conversion='slope_us_per_row / bytes_per_requested_row' if not holding_u else None,
                coefficient_order=['intercept_us','slope_us_per_'+axis] if holding_u else ['intercept_us','slope_us_per_row','slope_us_per_'+axis],
                mean=mean.tolist(),ci95_low=(mean-half).tolist() if half is not None else None,
                ci95_high=(mean+half).tolist() if half is not None else None,
                ci_scope='variation across randomized timing blocks; model misspecification reported separately',
                fit_quality=qualities)

groups=defaultdict(list)
for r in rows:groups[(r['dtype'],r['n'],r['cache'],r['merge'],r['pipeline'])].append(r)
results=[]
for key,group in sorted(groups.items()):
    near=[r for r in group if r['gap']==2]
    equal=[r for r in near if not r['skew']]
    far=[r for r in group if r['gap']==64 and r['family']=='core']
    results.append(dict(dtype=key[0],n=key[1],cache=key[2],merge=key[3],pipeline=key[4],
                        R_model=fit(near,'r'),api_model=fit(near,'commands_per_window'),
                        equal_length_R_model=fit(equal,'r'),far_U64_R_curve=fit(far,'r',True)))
analysis=root/'analysis-v5';analysis.mkdir(exist_ok=True)
(analysis/'model-fits.json').write_text(json.dumps(results,indent=2))
medians=[]
for r in rows:
    values=[datum(json.loads(p.read_text())['block'],r) for p in accepted]
    medians.append(dict(case=r['name'],median_us_per_window=float(np.median(values)),
                        q25=float(np.quantile(values,.25)),q75=float(np.quantile(values,.75)),
                        cv=float(np.std(values,ddof=1)/np.mean(values)) if len(values)>1 else None))
with (analysis/'case-summary.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(medians[0]));w.writeheader();w.writerows(medians)
(analysis/'analysis-status.json').write_text(json.dumps(dict(accepted_blocks=len(accepted),
    final=len(accepted)==20,logical_cases=len(rows),unique_cases=2592,models=len(results),
    main_model='near-gap equal and skew design points; far-gap U=64 curve is separate',
    units='global device makespan / all windows over 24 AICs; multiply by 24 only to express per-core equivalent throughput cost'),indent=2))
print('ANALYZED',len(accepted),'blocks;',len(results),'model cells')
