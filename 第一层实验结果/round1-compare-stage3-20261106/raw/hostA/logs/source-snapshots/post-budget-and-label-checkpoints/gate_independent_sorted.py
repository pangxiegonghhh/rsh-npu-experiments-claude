import json
from pathlib import Path
from native import BASE,Matrix,Layout,chunks
from evaluate_t23 import read_order
from independent_sorted import metrics
from resource_slots import acquire
token=acquire();m=Matrix('cora');reuse=json.loads((BASE/'logs/reused-orders.json').read_text());checks=[]
for member in ['B0','C9-Gorder','C10-BP']:
 r=next(r for r in reuse if r['task']=='T22' and r['use']=='base-order' and r['matrix']=='cora' and r['member']==member);pi=read_order(r['runtime_path'])
 for tau in [None,2,3]:
  D=[] if tau is None else [v for v in pi if m.deg[v]<=tau];K=[v for v in pi if v not in set(D)]
  for diag in [0,1]:
   lc=Layout(m,chunks(K),diag=diag)
   for placement in ['tail','tail-co','inplace','snap','gap']:
    for d in [False,True]:
     if placement=='gap' and not d:continue
     sigma,_=lc.layout(pi,D,placement,d);a=lc.metrics(sigma);b=metrics(m,chunks(K),sigma,diag=diag);assert all(a[k]==v for k,v in b.items()),(member,tau,diag,placement,d,a,b);checks.append(dict(member=member,tau=tau,diag=diag,placement=placement,d=d,identical=True))
   lc.close()
(BASE/'logs/independent-sorted-port-gate.json').write_text(json.dumps(dict(passed=True,cases=len(checks),checks=checks,independent_algorithm='sort/unique mapped column positions; run and bucket counts',native_candidate_counters_used=False),indent=2));print('INDEPENDENT_SORTED_162_CASES_IDENTICAL',flush=True)
