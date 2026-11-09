import json,random
from types import SimpleNamespace
from collections import Counter
import numpy as np
from native import BASE
from capacity import repair
checks=[]
for seed in range(100):
 rng=random.Random(seed);n=37;W=8;k=(n+W-1)//W;a=[{u for u in range(n) if u!=v and rng.random()<.12} for v in range(n)]
 for v in range(n):
  for u in list(a[v]):a[u].add(v)
 for v in range(n):
  if not a[v]:a[v].add((v+1)%n);a[(v+1)%n].add(v)
 labels=[rng.randrange(k) for _ in range(n)];groups=[set(v for v in range(n) if labels[v]==g) for g in range(k)];groups.sort(key=lambda g:(-len(g),min(g) if g else n));target=[W]*(k-1)+[n-W*(k-1)];ct=[Counter(c for v in g for c in a[v]) for g in groups];moves=[]
 while any(len(g)>t for g,t in zip(groups,target)):
  choices=[]
  for gi,g in enumerate(groups):
   if len(g)<=target[gi]:continue
   for r in g:
    for ti,tg in enumerate(groups):
     if len(tg)>=target[ti]:continue
     delta=sum(ct[ti][c]==0 for c in a[r])-sum(ct[gi][c]==1 for c in a[r]);choices.append((delta,r,ti,gi))
  delta,r,ti,gi=min(choices);groups[gi].remove(r);groups[ti].add(r)
  for c in a[r]:ct[gi][c]-=1;ct[ti][c]+=1
  moves.append([r,gi,ti,delta])
 p=np.asarray([0]+list(np.cumsum([len(s) for s in a])),np.int64);c=np.asarray([x for s in a for x in s],np.int32);m=SimpleNamespace(n=n,p=p,c=c,deg=np.diff(p));pi,d=repair(m,labels,W)
 assert d['trace']==moves,(seed,d['trace'],moves);assert pi==[v for g in groups for v in sorted(g)];checks.append(dict(seed=seed,moves=len(moves),identical=True))
(BASE/'logs/capacity-repair-gate.json').write_text(json.dumps(dict(passed=True,checks=checks),indent=2));print('CAPACITY_REPAIR_100_FIXTURES_IDENTICAL')
