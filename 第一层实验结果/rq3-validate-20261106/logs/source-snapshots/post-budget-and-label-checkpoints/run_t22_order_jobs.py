import concurrent.futures,json,subprocess,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parents[1];assert json.loads((BASE/'logs/rect-port-gate.json').read_text())['passed'];assert json.loads((BASE/'logs/ls-port-gate.json').read_text())['passed'];reuse=json.loads((BASE/'logs/reused-orders.json').read_text());meta={x['matrix']:x for x in json.loads((BASE/'logs/matrices-and-taus.json').read_text())};cat=BASE/'work/t22-order-catalog';cat.mkdir(exist_ok=True);records=[]
for base in reuse:
 if base['task']=='T22' and base['use']=='base-order':
  for tau in [None]+[t['tau'] for t in meta[base['matrix']]['taus']]:records.append(dict(base,kind='rerun',tau=tau,W=16))
  if base['matrix']=='wiki-RfA' and base['member'] in ['C9-Gorder','rsh-α0']:records.append(dict(base,kind='lsfull',tau=None,W=16,**{'lambda':0}))
  if base['member'] in ['B0','rsh-α0','rabbit-pilot','neutron-pilot','C9-Gorder','C9-S','C10-BP']:
   for t in meta[base['matrix']]['taus']:
    for lam in ([0] if base['member'] in ['B0','rabbit-pilot','neutron-pilot'] else [0,1]):
     if any(x['task']=='T22' and x['use']=='M6-reuse' and x['matrix']==base['matrix'] and x['start']==base['member'] and int(x['tau'])==t['tau'] and int(x['lam'])==lam for x in reuse):continue
     records.append(dict(base,kind='ls',tau=t['tau'],W=16,**{'lambda':lam}))
paths=[]
for i,r in enumerate(records):
 r['seed']=0;key=f"{r['matrix']}__{r['member']}__{r['kind']}__tau{r['tau']}__lam{r.get('lambda','none')}";p=cat/(key+'.json');p.write_text(json.dumps(r,indent=2));done=BASE/'work/order-jobs'/(key+'.record.json')
 if done.exists() and json.loads(done.read_text())['status']=='OK':continue
 paths.append(p)
def execute(p):
 cmd=[sys.executable,'-B','scripts/order_job.py',str(p)];log=BASE/'logs'/('t22-order-'+p.stem);start=time.time()
 with open(str(log)+'.stdout','w') as o,open(str(log)+'.stderr','w') as e:
  try:rc=subprocess.run(cmd,cwd=BASE,stdout=o,stderr=e,timeout=7200).returncode
  except subprocess.TimeoutExpired:rc=124
 r=dict(command=cmd,start=start,end=time.time(),exitcode=rc);Path(str(log)+'.command.json').write_text(json.dumps(r,indent=2));print(p.stem,rc,round(time.time()-start,1),flush=True);return r
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:records=list(ex.map(execute,paths))
(BASE/'logs/t22-order-jobs.json').write_text(json.dumps(records,indent=2))
