import sys,json,time,hashlib
from pathlib import Path
import numpy as np
from native import BASE,Matrix,Candidates
sys.dont_write_bytecode=True
sys.path.insert(0,str(BASE/'repo/第一层工作区/T23参考实现'))
import t23_candidates as ref
m=Matrix('cora');a=m.adjacency();g=Candidates(m);rows=[]
for name,fn in ref.CANDIDATES.items():
 t=time.time();actual,diag=g.order(name);expected,rd=fn(a);assert actual==expected,(name,next(i for i,(x,y) in enumerate(zip(actual,expected)) if x!=y))
 rows.append(dict(candidate=name,identical=True,n=len(actual),sha256=hashlib.sha256(json.dumps(actual,separators=(',',':')).encode()).hexdigest(),seconds=time.time()-t,diag=diag,reference_diag=rd));print(name,'IDENTICAL',flush=True)
g.close();(BASE/'logs/candidate-port-gate.json').write_text(json.dumps(dict(passed=True,rows=rows),indent=2))
