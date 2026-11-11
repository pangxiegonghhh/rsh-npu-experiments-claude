import ctypes as C
import hashlib,json,random
from types import SimpleNamespace
import numpy as np
from native import BASE,Layout,I,L,chunks

def backend(filename):
 class Port(Layout):
  lib=C.CDLL(str(BASE/'work'/filename))
  lib.lc_make.argtypes=[C.c_int,L,I,I,L,C.c_int,C.c_int,C.c_int]
  lib.lc_make.restype=C.c_void_p
  lib.lc_free.argtypes=[C.c_void_p]
  lib.lc_layout.argtypes=[C.c_void_p,I,I,C.c_int,C.c_int,C.c_int,I,L,C.c_char_p]
  lib.lc_metrics.argtypes=[C.c_void_p,I,L]
 return Port

old,new=backend('liblayouts-v2.dylib'),backend('liblayouts-v3.dylib')
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
result=dict(passed=True,fixtures=36,cases=len(checks),seed=572903,checks=checks,
 source_sha256=hashlib.sha256((BASE/'scripts/layouts_dense.cpp').read_bytes()).hexdigest(),
 binary_sha256=hashlib.sha256((BASE/'work/liblayouts-v3.dylib').read_bytes()).hexdigest())
(BASE/'logs/layout-v3-random-gate.json').write_text(json.dumps(result,indent=2))
print('DENSE_LAYOUT_RANDOM_GATE_OK',len(checks),flush=True)
