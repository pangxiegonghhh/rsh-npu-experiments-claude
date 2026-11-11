import json,sys,os,time
from native import BASE,Matrix,Rect
sys.dont_write_bytecode=True
for sub in ['T17-空白一试算脚本','T17-空白二试算脚本']:sys.path.insert(0,str(BASE/'repo/第一层工作区'/sub))
os.chdir(BASE/'work/gates/t22-reference')
import rq3lib as ref
m=Matrix('cora');a=m.adjacency();orders=json.loads((BASE/'work/gates/t22-reference/out_rq3/orders.json').read_text());reruns=json.loads((BASE/'work/gates/t22-reference/out_rq3/reruns.json').read_text());mapping={'C9-Gorder':'gorder','C9-S':'gorder-S','rsh-α0':'rsh','rabbit-pilot':'rabbit','neutron-pilot':'neutron','C10-BP':'bp'};checks=[]
for tau in [None,2,3]:
 K=[v for v in range(m.n) if tau is None or m.deg[v]>tau];r=Rect(m,K)
 for method,key in mapping.items():
  actual=r.order(method);expected=orders[key] if tau is None else reruns[f'{tau}|{key}'];assert actual==expected,(method,tau,next((i,x,y) for i,(x,y) in enumerate(zip(actual,expected)) if x!=y));checks.append(dict(member=method,tau=tau,identical=True));print(method,tau,'IDENTICAL',flush=True)
 r.close()
(BASE/'logs/rect-port-gate.json').write_text(json.dumps(dict(passed=True,checks=checks),indent=2))
