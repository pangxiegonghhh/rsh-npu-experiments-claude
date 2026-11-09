import json,random,sys
from types import SimpleNamespace
import numpy as np
from native import BASE,Candidates
from resource_slots import acquire
slot=acquire();sys.path.insert(0,str(BASE/'repo/第一层工作区/T23参考实现'));import t23_candidates as ref
checks=[]
for n in [49999,50000,99999,100000]:
 rng=random.Random(n);vertices=sorted(rng.sample(range(n),250));a=[set() for _ in range(n)]
 for i,r in enumerate(vertices):
  for j in range(i+1,min(i+12,len(vertices))):
   if rng.random()<.5:s=vertices[j];a[r].add(s);a[s].add(r)
 p=np.asarray([0]+list(np.cumsum([len(x) for x in a])),np.int64);c=np.asarray([v for row in a for v in sorted(row)],np.int32);m=SimpleNamespace(n=n,p=p,c=c);g=Candidates(m);actual,diag=g.order('C3-A');expected,_=ref.CANDIDATES['C3-A'](a);g.close();assert actual==expected;checks.append(dict(n=n,b=diag['signature_bucket_width_b'],identical=True));print('C3-A',n,diag['signature_bucket_width_b'],'IDENTICAL',flush=True)
(BASE/'logs/adaptive-width-boundaries-gate.json').write_text(json.dumps(dict(passed=True,checks=checks,synthetic_only=True),indent=2))
