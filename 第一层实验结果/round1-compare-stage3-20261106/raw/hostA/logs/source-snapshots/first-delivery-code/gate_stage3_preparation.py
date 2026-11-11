import ctypes as C,json,os,random,sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from native import BASE,Rect,Candidates,I,L,ip,lp
from resource_slots import acquire
token=acquire();sys.dont_write_bytecode=True
for sub in ['T17-空白一试算脚本','T17-空白二试算脚本','T23参考实现']:sys.path.insert(0,str(BASE/'repo/第一层工作区'/sub))
os.chdir(BASE/'work/gates/t22-reference')
import rq3lib,methods,t23_candidates
lib=C.CDLL(str(BASE/'work/liblarge-rcm.dylib'));lib.large_rcm.argtypes=[C.c_int,L,I,I];checks=[]
for seed in range(4):
 rng=random.Random(seed);n=71;empty=set(rng.sample(range(n),19));a=[set() for _ in range(n)]
 for r in range(n):
  for s in range(r+1,n):
   if r not in empty and s not in empty and rng.random()<.18:a[r].add(s);a[s].add(r)
 ne=[v for v in range(n) if a[v]];em=[v for v in range(n) if not a[v]];p=np.asarray([0]+list(np.cumsum([len(s) for s in a])),np.int64);c=np.asarray([v for s in a for v in s],np.int32);m=SimpleNamespace(n=n,p=p,c=c);rect=Rect(m,ne)
 for name in ['C9-Gorder','C9-S','C10-BP','rsh-α0']:
  if name=='C10-BP':expected=rq3lib.bp_sub(a,ne,W=8,seed=seed)
  elif name=='rsh-α0':expected=rq3lib.pilot_sub(a,ne,'rsh')
  else:expected=rq3lib.gorder_sub(a,ne,w=7,use_sn=name=='C9-Gorder')
  actual=rect.order(name,8,seed);assert actual==expected,(seed,name);checks.append(dict(fixture_seed=seed,method=name,nonempty_reference_identical=True))
 rect.close();K,sub=rq3lib.induced(a,ne);expected=[K[v] for v in methods.rcm(sub)]+em;actual=np.empty(n,np.int32);lib.large_rcm(n,lp(p),ip(c),ip(actual));assert actual.tolist()==expected;checks.append(dict(fixture_seed=seed,method='B-RCM-ref',nonempty_reference_identical=True))
 O=ne[:];rng.shuffle(O);O+=em;inverse={v:i for i,v in enumerate(O)};ren=[{inverse[u] for u in a[v]} for v in O];p2=np.asarray([0]+list(np.cumsum([len(s) for s in ren])),np.int64);c2=np.asarray([v for s in ren for v in s],np.int32);g=Candidates(SimpleNamespace(n=n,p=p2,c=c2))
 for name in ['C3-W4','C3-A','C4-U','C4-T','C7-I']:
  actual,_=g.order(name);expected,_=t23_candidates.CANDIDATES[name](ren);assert [O[v] for v in actual]==[O[v] for v in expected];checks.append(dict(fixture_seed=seed,method=name+'-R',symmetric_renumbering_identical=True))
 g.close()
(BASE/'logs/stage3-preparation-gate.json').write_text(json.dumps(dict(passed=True,synthetic_only=True,checks=checks,formal_stage3_started=False),indent=2));print('STAGE3_PREPARATION_40_CASES_IDENTICAL')
