import json,time,subprocess,sys,concurrent.futures
from pathlib import Path
BASE=Path(__file__).resolve().parents[1];cat=BASE/'work/bp-variance-catalog';cat.mkdir(exist_ok=True);out=BASE/'work/bp-variance-orders';out.mkdir(exist_ok=True);reuse=json.loads((BASE/'logs/reused-orders.json').read_text())
def call(cmd,key):
 if 'evaluate_t23.py' in cmd and (BASE/'work/t23-evaluations'/Path(cmd[-1]).stem/'status.json').exists():return
 if 'order_job.py' in cmd and (out/(Path(cmd[3]).stem+'.record.json')).exists():return
 start=time.time();log=BASE/'logs'/key
 with open(str(log)+'.stdout','w') as o,open(str(log)+'.stderr','w') as e:
  try:rc=subprocess.run(cmd,cwd=BASE,stdout=o,stderr=e,timeout=7200).returncode
  except subprocess.TimeoutExpired:rc=124
 Path(str(log)+'.command.json').write_text(json.dumps(dict(command=cmd,start=start,end=time.time(),exitcode=rc),indent=2));print(key,rc,round(time.time()-start,1),flush=True)
for matrix in ['cora','ogbn-arxiv']:
 for seed in [1,2]:
  base=next(r for r in reuse if r['task']=='T22' and r['use']=='base-order' and r['matrix']==matrix and r['member']=='C10-BP');key=f'{matrix}__C10-BP__W16__seed{seed}';r=dict(base,kind='variance',tau=None,W=16,seed=seed);p=cat/(key+'.json');p.write_text(json.dumps(r,indent=2));call([sys.executable,'-B','scripts/order_job.py',str(p),'--output-dir',str(out)],'bp-variance-order-'+key);q=out/(key+'.record.json')
  if q.exists():
   record=json.loads(q.read_text())
   if record['status']=='OK':
    record.update(runtime_path=record['path'],t23_member='C10-BP');p=BASE/'work/t23-external-catalog'/('variance-'+key+'.json');p.write_text(json.dumps(record,indent=2));call([sys.executable,'-B','scripts/evaluate_t23.py',str(p)],'bp-variance-eval-'+key)
(BASE/'logs/bp-variance-complete.json').write_text(json.dumps(dict(complete=True),indent=2))
