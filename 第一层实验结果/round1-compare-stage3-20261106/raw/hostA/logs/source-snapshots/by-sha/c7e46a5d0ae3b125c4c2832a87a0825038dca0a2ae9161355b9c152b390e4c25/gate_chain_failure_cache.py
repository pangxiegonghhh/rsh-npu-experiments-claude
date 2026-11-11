import hashlib,json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from native_chain_v6 import BASE,Layout,chunks
snapshot=Path(json.loads((BASE/'logs/layout-v5-before.json').read_text())['snapshot'])
scope={'__file__':str(BASE/'scripts/native.py')};exec(compile(snapshot.read_text(),str(snapshot),'exec'),scope);Plain=scope['Layout']
message='co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE'
counts=dict(reference_co=0,candidate_co=0,reference_K=0,candidate_K=0)
class Reference(Plain):
 def layout(self,pi,residual,rule='tail',d=True):
  if rule=='tail-co':
   counts['reference_co']+=1
   if d:counts['reference_K']+=1;Plain.layout(self,pi,residual,'tail',d)
   raise RuntimeError(message)
  return Plain.layout(self,pi,residual,rule,d)
class Cached(Layout):
 def _layout_direct(self,pi,residual,rule='tail',d=True):
  if rule=='tail-co':
   counts['candidate_co']+=1
   if d:counts['candidate_K']+=1;Plain.layout(self,pi,residual,'tail',d)
   raise RuntimeError(message)
  if d:counts['candidate_K']+=1
  return Plain.layout(self,pi,residual,rule,d)
checks=[];n=64;pi=list(range(n));D=pi[32:];windows=chunks(pi[:32])
for matrix in range(2):
 adj=[[int((r+matrix+1)%n)] for r in range(n)];p=np.arange(n+1,dtype=np.int64);m=SimpleNamespace(n=n,p=p,c=np.asarray([x for v in adj for x in v],np.int32))
 for diag in [0,1]:
  a,b=Reference(m,windows,16,diag),Cached(m,windows,16,diag)
  for d in [False,True]:
   errors=[]
   for obj in [a,b]:
    try:obj.layout(pi,D,'tail-co',d)
    except RuntimeError as error:errors.append(str(error))
   assert errors==[message,message];checks.append(dict(matrix=matrix,diag=diag,d=d,identical_failure=True))
  a.close();b.close()
assert counts==dict(reference_co=8,candidate_co=2,reference_K=4,candidate_K=4),counts
observed=BASE/'work/stage3-partial-post/stage3-reddit__B0__W16__seed0__tau153/rows.json';raw=observed.read_bytes();assert message in raw.decode();(BASE/'logs/layout-v6-observed-failure-rows.json').write_bytes(raw)
result=dict(passed=True,cases=len(checks),checks=checks,counts=counts,synthetic_limit_injection=True,scope='wrapper failure memoization only: native limit is synthetically raised, not a scientific matrix run. Successful numerical layouts independently covered by Cora/reference/random/boundary gates. D-greedy still executes its K ordering before replaying the known chain failure.',observed_actual_failure_snapshot='layout-v6-observed-failure-rows.json',observed_actual_failure_snapshot_sha256=hashlib.sha256(raw).hexdigest(),candidate_source_sha256=hashlib.sha256((BASE/'scripts/native_chain_v6.py').read_bytes()).hexdigest())
(BASE/'logs/layout-v6-failure-cache-gate.json').write_text(json.dumps(result,indent=2));print('CHAIN_FAILURE_CACHE_GATE_OK',counts,flush=True)
