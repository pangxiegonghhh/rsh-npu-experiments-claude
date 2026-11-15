"""Reproduce the exported M4 model means/CIs from recovered 20-block observations."""
from pathlib import Path
import collections,json,sys
base=Path(__file__).resolve().parent
sys.path.insert(0,str(base/'cora-offline-audit/analysis-deps'))
import numpy as np

root=base/'t8-m4-recovered-statistics-20261115'
records=json.loads((root/'timing-observations.json').read_text())
models=json.loads((root/'model-coefficients.json').read_text())
rows=json.loads((base/'t8-m4-20261114/m4-manifest.json').read_text());byname={r['name']:r for r in rows}
observed={r['case']:np.array(list(map(float,r['normalized_us']))) for r in records if r['stage']=='main'}
assert len(observed)==2592 and all(v.shape==(20,) for v in observed.values())
def canonical(row):
    name=row.get('alias_of',row['name'])
    while 'alias_of' in byname[name]:name=byname[name]['alias_of']
    return name
groups=collections.defaultdict(list);pooled=collections.defaultdict(list);seen=collections.defaultdict(set)
for row in rows:
    if row['gap']!=2:continue
    groups[(row['dtype'],row['n'],row['cache'],str(row['merge']),row['pipeline'])].append(row)
    key=(row['dtype'],row['n'],row['cache'],row['pipeline']);name=canonical(row)
    if name not in seen[key]:seen[key].add(name);pooled[key].append(row)
identifiable=0;unidentifiable=0;maximum_error=0
for model in models:
    key=(model['dtype'],model['n'],model['cache'],model['merge'],model['pipeline'])
    data=pooled[(key[0],key[1],key[2],key[4])] if model['kind']=='pooled_api' else groups[key]
    axis='r' if model['kind']=='R_model' else 'commands_per_window'
    X=np.array([[1,r['u'],r[axis]] for r in data],float)
    rank=int(np.linalg.matrix_rank(X));assert model['identifiable']==(rank==3)
    if rank<3:unidentifiable+=1;continue
    beta=[]
    for block in range(20):
        y=np.array([observed[canonical(r)][block] for r in data])
        beta.append(np.linalg.lstsq(X,y,rcond=None)[0])
    beta=np.array(beta);mean=beta.mean(axis=0);half=2.093*beta.std(axis=0,ddof=1)/np.sqrt(20)
    for field,value in [('mean',mean),('ci95_low',mean-half),('ci95_high',mean+half)]:
        delta=float(np.max(np.abs(value-np.array(model[field]))));maximum_error=max(maximum_error,delta)
        assert np.allclose(value,model[field],rtol=1e-8,atol=1e-10),(key,model['kind'],field,value,model[field])
    identifiable+=1
result=dict(status='PASS',main_cases=2592,blocks=20,normalized_samples=2592*20,model_tables_compared=len(models),identifiable_models=identifiable,rank_deficient_models=unidentifiable,max_absolute_coefficient_difference_us=maximum_error,
    scope='Recomputed existing primary R/API and supplementary pooled API fits from the recovered CSV observation values; no new experiment, no model/G2 gate change.')
(root/'model-recomputation-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
