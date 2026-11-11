import argparse,hashlib,json,time,traceback
from pathlib import Path
from native import BASE,Matrix,Layout,chunks
from independent_sorted import metrics
from evaluate_t23 import read_order
from resource_slots import acquire
ap=argparse.ArgumentParser();ap.add_argument('matrix');args=ap.parse_args();slot=acquire();start=time.time();root=BASE/'work/stage3-independent'/args.matrix;root.mkdir(parents=True,exist_ok=True);result=dict(matrix=args.matrix,status='INCOMPLETE',start=start)
try:
 assert json.loads((BASE/'logs/independent-sorted-port-gate.json').read_text())['passed'];m=Matrix(args.matrix);meta=next(x for x in json.loads((BASE/'logs/matrices-and-taus.json').read_text()) if x['matrix']==args.matrix);records=[]
 for p in (BASE/'work/stage3-cases').glob(f'stage3-{args.matrix}__*__W16__seed0/record.json'):
  r=json.loads(p.read_text())
  if r['status']=='OK' and r.get('runtime_path'):records.append(r)
 records.sort(key=lambda r:(r['method'] not in ['B0','B-RCM-ref','C4-U'],r['method']));assert len(records)>=3,'fewer than3 successful independent row orders';checks=[]
 for r in records[:3]:
  pi=read_order(r['runtime_path']);h=hashlib.sha256(Path(r['runtime_path']).read_bytes()).hexdigest();assert h==r['sha256'];assert sorted(pi)==list(range(m.n))
  for tau in [None]+[t['tau'] for t in meta['taus']]:
   K=pi if tau is None else [v for v in pi if m.deg[v]>tau];D=[] if tau is None else [v for v in pi if m.deg[v]<=tau]
   for diag in [0,1]:
    windows=chunks(K);lc=Layout(m,windows,diag=diag)
    for placement,d in [('tail',False),('tail-co',False),('tail-co',True)]:
     sigma,guard=lc.layout(pi,D,placement,d);expected=lc.metrics(sigma);actual=metrics(m,windows,sigma,diag=diag);assert all(expected[k]==v for k,v in actual.items());checks.append(dict(member=r['method'],order_sha256=h,tau=tau,diag=diag,placement=placement,d=d,metrics=actual,identical=True))
    lc.close()
 result.update(status='OK',independent_orders=3,checks=checks,checker='independent sorted-position implementation; no candidate counters imported',Cora_port_gate_sha256=hashlib.sha256((BASE/'logs/independent-sorted-port-gate.json').read_bytes()).hexdigest())
except Exception as e:result.update(error=str(e),traceback=traceback.format_exc())
result.update(end=time.time(),seconds=time.time()-start);(root/'status.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
