import json,os,random,sys
from types import SimpleNamespace
import numpy as np
from native import BASE,Matrix
from ls_runtime import local_search
from evaluate_t23 import read_order
from resource_slots import acquire
slot=acquire();sys.dont_write_bytecode=True;sys.path.insert(0,str(BASE/'repo/第一层工作区/T17-空白一试算脚本'));os.chdir(BASE/'work/gates/t22-reference');import methods
reuse=json.loads((BASE/'logs/reused-orders.json').read_text());checks=[];m=Matrix('cora')
for name in ['C9-Gorder','rsh-α0']:
 start=next(r for r in reuse if r['task']=='T22' and r['use']=='base-order' and r['matrix']=='cora' and r['member']==name);old=next(r for r in reuse if r['task']=='T22' and r['use']=='LS-full' and r['matrix']=='cora' and r['start']==name);actual,diag=local_search(m,read_order(start['runtime_path']),tau=None,lam=0,seed=0);assert actual==read_order(old['runtime_path']),(name,'frozen Cora full-control vector mismatch');checks.append(dict(matrix='cora',member=name,identical_to_T21_sha256=old['sha256']));print('LS_FULL_CORA',name,'IDENTICAL',flush=True)
for seed in range(2):
 rng=random.Random(seed);n=49;empty=set(rng.sample(range(n),11));a=[set() for _ in range(n)]
 for r in range(n):
  for s in range(r+1,n):
   if r not in empty and s not in empty and rng.random()<.13:a[r].add(s);a[s].add(r)
 p=np.asarray([0]+list(np.cumsum([len(x) for x in a])),np.int64);c=np.asarray([u for row in a for u in row],np.int32);m=SimpleNamespace(n=n,p=p,c=c,deg=np.diff(p));pi=list(range(n));rng.shuffle(pi)
 for lam in [0,1]:
  actual,diag=local_search(m,pi,W=8,tau=None,lam=lam,seed=0);ref=methods.MemberLS(pi,a,W=8);expected=ref.run(lam=lam,sweeps=10,cand_parts=3,seed=0);assert actual==expected,(seed,lam,'empty-vertex full-LS reference mismatch');assert diag['tracked_sumU']==ref.U and diag['tracked_sumGamma']==ref.G;checks.append(dict(fixture_seed=seed,empty_count=len(empty),lam=lam,identical_reference_order_and_UG=True));print('LS_FULL_EMPTY_FIXTURE',seed,lam,'IDENTICAL',flush=True)
(BASE/'logs/ls-full-port-gate.json').write_text(json.dumps(dict(passed=True,checks=checks),indent=2));print('LS_FULL_PORT_GATE_OK',flush=True)
