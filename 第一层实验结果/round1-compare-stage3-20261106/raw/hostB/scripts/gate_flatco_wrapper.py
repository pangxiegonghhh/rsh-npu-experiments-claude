import os,json,hashlib
from pathlib import Path
os.environ.pop('RQ3_LAYOUT_LIB',None)
from native_flatco_v7 import BASE,Matrix,Layout,chunks
assert Path(Layout.lib._name).resolve()==(BASE/'work/liblayouts-v7.dylib').resolve()
m=Matrix('cora');a0=m.adjacency();a1=[s|{i} for i,s in enumerate(a0)]
exp=json.loads((BASE/'repo/第一层工作区/T23派发/expected_conditions_cora.json').read_text());grid=[]
for name in exp:
 pi=list(range(m.n)) if name=='B0' else json.loads((BASE/'work/generated/cora__C4-U__W16__seed0.order.json').read_text());rows=[]
 for diag,adj in enumerate([a0,a1]):
  wins=chunks(pi);lc=Layout(m,wins,diag=diag)
  for rule in ['own','D-greedy']:
   sig=pi if rule=='own' else lc.layout(pi,[])[0]
   metric=lc.metrics(sig);metric.pop('write_runs_aic');rows.append(dict(diag=f'A{diag}',W=16,tau='none',placement='none',d_rule=rule,**metric))
  lc.close()
  for tau in [2,3]:
   D={v for v in range(m.n) if len(a0[v])<=tau};res=[v for v in pi if v in D];wins=chunks([v for v in pi if v not in D]);lc=Layout(m,wins,diag=diag)
   for placement,rule in [('tail-co','own'),('tail-co','D-greedy'),('tail','own'),('tail','D-greedy')]:
    sig,_=lc.layout(pi,res,placement,rule=='D-greedy');metric=lc.metrics(sig);metric.pop('write_runs_aic');rows.append(dict(diag=f'A{diag}',W=16,tau=tau,placement=placement,d_rule=rule,resid_frac=round(len(D)/m.n,6),**metric))
   lc.close()
 assert rows==exp[name],(name,next((x,y) for x,y in zip(rows,exp[name]) if x!=y));grid.append(dict(member=name,rows=len(rows),identical=True))

assert sum(x['rows'] for x in grid)==40
provenance=json.loads(Layout._backend_log_path.read_text())
assert provenance['library_path']==str(BASE/'work/liblayouts-v7.dylib')
assert provenance['library_sha256']==hashlib.sha256((BASE/'work/liblayouts-v7.dylib').read_bytes()).hexdigest()
assert provenance['library_override_at_import'] is None
record=dict(passed=True,official_condition_rows=40,grid=grid,default_binary_confirmed=True,actual_backend_record=str(Layout._backend_log_path),actual_backend_record_sha256=hashlib.sha256(Layout._backend_log_path.read_bytes()).hexdigest(),candidate_python_sha256=hashlib.sha256((BASE/'scripts/native_flatco_v7.py').read_bytes()).hexdigest(),candidate_binary_sha256=provenance['library_sha256'],new_logging_only=True)
(BASE/'logs/layout-v7-wrapper-gate.json').write_text(json.dumps(record,indent=2))
print('V7_DEFAULT_WRAPPER_AND_BACKEND_PROVENANCE_40_ROWS_OK',flush=True)
