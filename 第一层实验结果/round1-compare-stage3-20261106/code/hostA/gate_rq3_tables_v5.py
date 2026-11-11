import csv,json,os,sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from native_chain_v5 import BASE,Layout,Rect,chunks
from order_job import induced_order
sys.dont_write_bytecode=True
for sub in ['T17-空白一试算脚本','T17-空白二试算脚本']:sys.path.insert(0,str(BASE/'repo/第一层工作区'/sub))
os.chdir(BASE/'work/gates/t22-reference')
from rq2lib import load_cora
n,a=load_cora();p=np.asarray([0]+list(np.cumsum([len(s) for s in a])),np.int64);c=np.fromiter((x for s in a for x in s),np.int32,count=int(p[-1]));m=SimpleNamespace(n=n,p=p,c=c,deg=np.diff(p));orders=json.loads(Path('out_rq3/orders.json').read_text());rows=list(csv.DictReader(open('out_rq3/table1_four_numbers.csv')));checks=[];mapping={'gorder':'C9-Gorder','gorder-S':'C9-S','rsh':'rsh-α0','rabbit':'rabbit-pilot','neutron':'neutron-pilot','bp':'C10-BP','rcm':'B-RCM-ref','slashburn':'SlashBurn'}
for tau in [2,3]:
 K=[v for v in range(n) if m.deg[v]>tau];rect=Rect(m,K)
 for key,pi in orders.items():
  D=set(range(n))-set(K);keep=[v for v in pi if v not in D];res=[v for v in pi if v in D];inplace=[[v for v in w if v not in D] for w in chunks(pi)];inplace=[w for w in inplace if w];method=mapping.get(key,'B0')
  rr=keep if key=='original' else induced_order(m,K,method) if key in ['rcm','slashburn'] else rect.order(method)
  expected=next(r for r in rows if r['member']==key and int(r['tau'])==tau)
  for diag in [0,1]:
   for label,wins in [('full',chunks(pi)),('inplace',inplace),('keep',chunks(keep)),('rerun',chunks(rr))]:
    lc=Layout(m,wins,diag=diag);s=lc.metrics(keep+res);lc.close();assert s['T']==int(expected[f'A{diag}_T_{label}']) and s['sumU']==int(expected[f'A{diag}_U_{label}']),(key,tau,diag,label,s,expected)
  checks.append(dict(member=key,tau=tau,table1_identical=True));print(key,tau,'TABLE1_IDENTICAL',flush=True)
 rect.close()
assert json.loads((BASE/'logs/layout-port-gate.json').read_text())['passed'];(BASE/'logs/rq3-native-table-v5-gate.json').write_text(json.dumps(dict(passed=True,checks=checks,table2_sigma_and_metrics_gate=str(BASE/'logs/layout-port-gate.json'),input_note='fresh reference load_cora adjacency for historical Table 1/2 gate; formal baseline row orders remain individually verified T21 index files, including frozen SlashBurn provenance'),indent=2))
