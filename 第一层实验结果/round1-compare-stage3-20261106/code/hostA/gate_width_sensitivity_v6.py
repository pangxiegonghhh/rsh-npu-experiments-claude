import hashlib,json,os,sys
from pathlib import Path
from native_chain_v6 import BASE,Matrix,Layout,chunks
from evaluate_t23 import read_order
from independent_sorted import metrics as independent_metrics
from resource_slots import acquire
slot=acquire();sys.dont_write_bytecode=True
for sub in ['T17-空白一试算脚本','T17-空白二试算脚本','T23派发']:sys.path.insert(0,str(BASE/'repo/第一层工作区'/sub))
os.chdir(BASE/'work/gates/t23-conditions-reference');import rq3lib;from rq2lib import dstage;from conditions_ref import metrics
m=Matrix('cora');a0=m.adjacency();reuse=json.loads((BASE/'logs/reused-orders.json').read_text());checks=[]
for W in [32,64,128]:
 for member in ['B0','C10-BP']:
  source=next(r for r in reuse if r['task']=='T23' and r['use']=='W-sensitivity' and r['matrix']=='cora' and int(r['W'])==W and r['t23_member']==member);pi=read_order(source['runtime_path']);assert hashlib.sha256(Path(source['runtime_path']).read_bytes()).hexdigest()==source['sha256']
  for diag,adj in enumerate([a0,[s|{i} for i,s in enumerate(a0)]]):
   for tau in [None,3]:
    D=[] if tau is None else [v for v in pi if m.deg[v]<=tau];K=[v for v in pi if v not in set(D)];windows=chunks(K,W);lc=Layout(m,windows,W,diag)
    for rule,d in ([('tail',False),('tail',True)] if tau is None else [('tail',False),('tail',True),('tail-co',False),('tail-co',True)]):
     actual,guard=lc.layout(pi,D,rule,d)
     expected=dstage(pi,adj,W=W,intra='greedy') if tau is None and d else pi if tau is None else rq3lib.layout_D(windows,adj,m.n,D,rule,W=W,pi=pi) if d else K+(rq3lib.co_chain(D,rq3lib._gv(windows,adj,m.n)) if rule=='tail-co' else D)
     assert actual==expected,(W,member,diag,tau,rule,d);r=lc.metrics(actual);ref=metrics(windows,adj,expected,W);ind=independent_metrics(m,windows,actual,W,diag);assert all(r[k]==v for k,v in ref.items());assert all(r[k]==v for k,v in ind.items());checks.append(dict(W=W,member=member,diag=diag,tau=tau,rule=rule,d=d,identical_reference_sigma=True,identical_reference_and_independent_metrics=True,sigma_sha256=hashlib.sha256(json.dumps(actual,separators=(',',':')).encode()).hexdigest(),guard=guard))
    lc.close()
  print('WIDTH_GATE',W,member,'OK',flush=True)
assert len(checks)==72;(BASE/'logs/layout-W-sensitivity-v6-gate.json').write_text(json.dumps(dict(passed=True,cases=72,checks=checks,reference='unchanged rq2lib/rq3lib/conditions_ref',independent='separate sorted-position counters',tile_K_width_fixed16=True),indent=2));print('WIDTH_SENSITIVITY_72_CASES_IDENTICAL',flush=True)
