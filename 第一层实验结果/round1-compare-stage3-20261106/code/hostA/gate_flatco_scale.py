import hashlib,json,random
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from native_chain_v6 import BASE,Layout,chunks
from gate_pinned_reference import execute
from resource_slots import acquire
slot=acquire()
assert Path(Layout.lib._name).resolve()==(BASE/'work/liblayouts-v7.dylib').resolve()
snapshot=Path(json.loads((BASE/'logs/layout-v6-before.json').read_text())['snapshot'])
scope={'__file__':str(BASE/'scripts/native.py')}
execute(snapshot,scope)
Reference=scope['Layout']
assert Path(Reference.lib._name).resolve()==(BASE/'work/liblayouts-v4.dylib').resolve()
checks=[]
def matrix(adj):
 return SimpleNamespace(n=len(adj),p=np.asarray([0]+list(np.cumsum([len(x) for x in adj])),np.int64),c=np.asarray([v for row in adj for v in row],np.int32))
def compare(m,windows,pi,residual,diag,d,fixture):
 a,b=Reference(m,windows,16,diag),Layout(m,windows,16,diag)
 try:
  expected,guard=a.layout(pi,residual,'tail-co',d)
  actual,actual_guard=b.layout(pi,residual,'tail-co',d)
  assert actual==expected and actual_guard==guard,(fixture,diag,d)
  assert a.metrics(expected)==b.metrics(actual)
  checks.append(dict(fixture=fixture,n=m.n,windows=len(windows),diag=diag,d=d,identical=True,guard=guard,sigma_sha256=hashlib.sha256(json.dumps(actual,separators=(',',':')).encode()).hexdigest()))
 finally:a.close();b.close()

rng=random.Random(39017)
n=50000;adj=[[] for _ in range(n)]
active=[64,65,66,67,1000,1001,30000,40000,40001,49998,49999]+list(range(45000,45050))
for row in range(64):adj[row]=sorted(rng.sample(active,rng.randint(3,30)))
m=matrix(adj);keep=list(range(64));rng.shuffle(keep);D=list(range(64,n));rng.shuffle(D)
for reverse in [False,True]:
 residual=list(reversed(D)) if reverse else D;pi=keep+residual
 for diag in [0,1]:
  for d in [False,True]:compare(m,chunks(keep),pi,residual,diag,d,'large original IDs and sparse inactive residuals')

K=70000;n=K+3;adj=[[K,K+1,K+2] if row<65000 else [K,K+1] for row in range(K)]+[[],[],[]]
m=matrix(adj);windows=[[v] for v in range(K)]
for reverse in [False,True]:
 residual=list(reversed(range(K,n))) if reverse else list(range(K,n));pi=list(range(K))+residual
 for diag in [0,1]:
  compare(m,windows,pi,residual,diag,False,'70000 vs65000 co scores; uint16 overflow would reorder the three-point chain')
  assert checks[-1]['guard']['co_chain_guard_windows_skipped']==0
assert len(checks)==12
record=dict(passed=True,cases=len(checks),checks=checks,fixture_only=True,scientific_matrix_cases_executed=False,
 candidate_cpp_sha256=hashlib.sha256((BASE/'scripts/layouts_flatco.cpp').read_bytes()).hexdigest(),
 candidate_binary_sha256=hashlib.sha256((BASE/'work/liblayouts-v7.dylib').read_bytes()).hexdigest(),
 reference_binary_sha256=hashlib.sha256((BASE/'work/liblayouts-v4.dylib').read_bytes()).hexdigest())
(BASE/'logs/layout-v7-scale-gate.json').write_text(json.dumps(record,indent=2))
print('FLAT_CO_LARGE_ID_HIGH_SCORE_GATE_OK',len(checks),flush=True)
