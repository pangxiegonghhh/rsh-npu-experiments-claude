from gate_pinned_reference import execute as execute_pinned_reference
import ctypes as C
import hashlib,json,random
from types import SimpleNamespace
import numpy as np
from native_chain_v6 import BASE,Layout,I,L,chunks
from pathlib import Path
assert Path(Layout.lib._name).resolve()==(BASE/'work/liblayouts-v7.dylib').resolve()

snapshot=__import__('pathlib').Path(json.loads((BASE/'logs/layout-v6-before.json').read_text())['snapshot']);scope={'__file__':str(BASE/'scripts/native.py')};execute_pinned_reference(snapshot,scope);old=scope['Layout'];new=Layout
rng=random.Random(572903);checks=[]
for fixture in range(36):
 n=rng.randrange(9,96);W=rng.choice([1,2,3,4,7,16,32]);adj=[]
 density=rng.choice([0,.03,.15,.6,1])
 for r in range(n):adj.append([c for c in range(n) if rng.random()<density])
 p=np.asarray([0]+list(np.cumsum([len(s) for s in adj])),np.int64)
 m=SimpleNamespace(n=n,p=p,c=np.asarray([c for s in adj for c in s],np.int32))
 pi=list(range(n));rng.shuffle(pi);D=pi[::4];mask=set(D);keep=[v for v in pi if v not in mask]
 for diag in [0,1]:
  for style in ['packed','singletons','mixed']:
   windows=chunks(keep,W) if style=='packed' else [[v] for v in keep]
   if style=='mixed':
    windows=[];i=0
    while i<len(keep):
     k=rng.randint(1,W);windows.append(keep[i:i+k]);i+=k
   a,b=old(m,windows,W,diag),new(m,windows,W,diag)
   for rule in ['tail','tail-co','inplace','snap','gap']:
    for d in ([True] if rule=='gap' else [False,True]):
     x,s=a.layout(pi,D,rule,d);y,t=b.layout(pi,D,rule,d)
     assert x==y and s==t,(fixture,W,diag,style,rule,d)
     assert a.metrics(x)==b.metrics(y)
     checks.append(dict(fixture=fixture,n=n,W=W,diag=diag,style=style,rule=rule,d=d))
   a.close();b.close()
assert Layout._chain_cache_hits>0
result=dict(cache_hits=Layout._chain_cache_hits,passed=True,fixtures=36,cases=len(checks),seed=572903,checks=checks,
 source_sha256=hashlib.sha256((BASE/'scripts/layouts_flatco.cpp').read_bytes()).hexdigest(),
 binary_sha256=hashlib.sha256((BASE/'work/liblayouts-v7.dylib').read_bytes()).hexdigest())
(BASE/'logs/layout-v7-random-gate.json').write_text(json.dumps(result,indent=2))
print('DENSE_LAYOUT_RANDOM_GATE_OK',len(checks),flush=True)

import hashlib
_gate_path=BASE/'logs'/'layout-v7-random-gate.json'
_gate_record=json.loads(_gate_path.read_text());_gate_record.update(candidate_cpp_sha256=hashlib.sha256((BASE/'scripts/layouts_flatco.cpp').read_bytes()).hexdigest(),candidate_binary_sha256=hashlib.sha256((BASE/'work/liblayouts-v7.dylib').read_bytes()).hexdigest(),candidate_python_wrapper='unchanged native_chain_v6; child-specific RQ3_LAYOUT_LIB=v7',reference_cpp_sha256=hashlib.sha256((BASE/'scripts/layouts_cached.cpp').read_bytes()).hexdigest(),reference_binary_sha256=hashlib.sha256((BASE/'work/liblayouts-v4.dylib').read_bytes()).hexdigest());_gate_path.write_text(json.dumps(_gate_record,indent=2))
