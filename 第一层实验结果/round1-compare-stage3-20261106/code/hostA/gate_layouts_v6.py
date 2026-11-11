import sys,os,json,time,hashlib
from pathlib import Path
from native_chain_v6 import BASE,Matrix,Layout,chunks
sys.dont_write_bytecode=True
for sub in ['T17-空白一试算脚本','T17-空白二试算脚本','T23参考实现','T23派发']:sys.path.insert(0,str(BASE/'repo/第一层工作区'/sub))
os.chdir(BASE/'work/gates/t23-conditions-reference')
import rq3lib as ref
from rq2lib import dstage
import conditions_ref as cr
m=Matrix('cora');a0=m.adjacency();a1=[s|{v} for v,s in enumerate(a0)];orders=json.loads((BASE/'work/gates/t22-reference/out_rq3/orders.json').read_text());checks=[]
for name,pi in orders.items():
 for tau in [2,3]:
  D={v for v in range(m.n) if len(a0[v])<=tau};res=[v for v in pi if v in D];wins=chunks([v for v in pi if v not in D])
  for diag,adj in enumerate([a0,a1]):
   lc=Layout(m,wins,diag=diag)
   for rule in ['tail','tail-co','inplace','snap','gap']:
    actual,st=lc.layout(pi,res,rule);expected=ref.layout_D(wins,adj,m.n,res,rule=rule,pi=pi);assert actual==expected,(name,tau,diag,rule,'sigma')
    stats=lc.metrics(actual);r=cr.metrics(wins,adj,expected,16);assert all(stats[k]==v for k,v in r.items()),(name,tau,diag,rule,stats,r)
    checks.append(dict(member=name,tau=tau,diag=diag,rule=rule,identical=True,guard=st))
   actual,_=lc.layout(pi,res,'tail-co',False);expected=[v for w in wins for v in w]+ref.co_chain(res,ref._gv(wins,adj,m.n));assert actual==expected
   lc.close()
 print(name,'all placements/metrics IDENTICAL',flush=True)
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
(BASE/'logs/layout-v6-port-gate.json').write_text(json.dumps(dict(passed=True,placements=checks,condition_grid=grid),indent=2));print('ALL_LAYOUT_GATES_OK',flush=True)
