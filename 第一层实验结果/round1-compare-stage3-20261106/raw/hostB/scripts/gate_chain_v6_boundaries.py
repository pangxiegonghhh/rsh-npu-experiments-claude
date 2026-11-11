import hashlib,json
from types import SimpleNamespace
import numpy as np
from native_chain_v6 import BASE,Layout,chunks
from pathlib import Path
snapshot=Path(json.loads((BASE/'logs/layout-v6-before.json').read_text())['snapshot'])
scope={'__file__':str(BASE/'scripts/native.py')}
exec(compile(snapshot.read_text(),str(snapshot),'exec'),scope)
Plain=scope['Layout'];checks=[];n=640;pi=list(range(n));D=list(range(32,n));windows=chunks(pi[:32])
for dataset,expected_guard in [(0,1),(1,0)]:
 adj=[list(range(32,433 if dataset==0 else 432)) if r==0 else list(range(32,432)) if r==16 and dataset==0 else [] for r in range(n)]
 p=np.asarray([0]+list(np.cumsum([len(v) for v in adj])),np.int64)
 m=SimpleNamespace(n=n,p=p,c=np.asarray([v for a in adj for v in a],np.int32))
 for residual in [D,list(reversed(D))]:
  for diag in [0,1]:
   a,b=Plain(m,windows,16,diag),Layout(m,windows,16,diag)
   for d in [False,True]:
    sigma,st=a.layout(pi,residual,'tail-co',d);actual,stats=b.layout(pi,residual,'tail-co',d)
    assert actual==sigma and stats==st
    assert stats['co_chain_guard_windows_skipped']==expected_guard
    assert a.metrics(sigma)==b.metrics(actual)
    checks.append(dict(dataset=dataset,diag=diag,d=d,reversed_residual=residual[0]==D[-1],guard=expected_guard,identical=True))
   a.close();b.close()
assert Layout._chain_cache_hits>0
(BASE/'logs/layout-v6-boundary-gate.json').write_text(json.dumps(dict(passed=True,cases=len(checks),checks=checks,cache_hits=Layout._chain_cache_hits,scope='400/401 residual coverage, identical row IDs across different matrices, reversed residual iteration, A0/A1 and own/D-greedy',candidate_source_sha256=hashlib.sha256((BASE/'scripts/native_chain_v6.py').read_bytes()).hexdigest(),direct_reference_source_sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest()),indent=2))
print('CHAIN_CACHE_BOUNDARIES_OK',len(checks),Layout._chain_cache_hits,flush=True)
