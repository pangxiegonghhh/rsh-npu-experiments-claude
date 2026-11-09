import concurrent.futures,json,subprocess,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parents[1];cat=BASE/'work/t22-new-eval-catalog';cat.mkdir(exist_ok=True);seen=set();reuse=json.loads((BASE/'logs/reused-orders.json').read_text());pool=concurrent.futures.ThreadPoolExecutor(max_workers=2);futures=[]
def run(p):
 cmd=[sys.executable,'-B','scripts/measure_t22_new.py',str(p)];log=BASE/'logs'/('t22-new-'+p.stem);start=time.time()
 with open(str(log)+'.stdout','w') as o,open(str(log)+'.stderr','w') as e:
  try:rc=subprocess.run(cmd,cwd=BASE,stdout=o,stderr=e,timeout=7200).returncode
  except subprocess.TimeoutExpired:rc=124
 r=dict(command=cmd,start=start,end=time.time(),exitcode=rc);Path(str(log)+'.command.json').write_text(json.dumps(r,indent=2));print(p.stem,rc,round(time.time()-start,1),flush=True);return r
for i,r in enumerate(reuse):
 if r['task']=='T22' and r['use']=='M6-reuse':
  data=json.loads(Path(r['runtime_path']).read_text());base=next(x for x in reuse if x['task']=='T22' and x['use']=='base-order' and x['matrix']==r['matrix'] and x['member']==r['start']);r=dict(r,path=r['runtime_path'],original_runtime_path=base['runtime_path'],kind='ls',tau=int(r['tau']),W=16,**{'lambda':float(r['lam'])});p=cat/f'reuse-{i:03d}.json';p.write_text(json.dumps(r,indent=2));futures.append(pool.submit(run,p))
while True:
 for p in sorted((BASE/'work/order-jobs').glob('*.record.json')):
  if p.name in seen:continue
  r=json.loads(p.read_text())
  if r.get('status')!='OK' or r.get('tau') is None or r.get('kind') not in ['rerun','ls']:continue
  seen.add(p.name);q=cat/p.name;q.write_text(json.dumps(r,indent=2));futures.append(pool.submit(run,q))
 if (BASE/'logs/t22-order-jobs.json').exists():break
 time.sleep(5)
pool.shutdown(wait=True);records=[f.result() for f in futures];(BASE/'logs/t22-new-evaluations.json').write_text(json.dumps(records,indent=2))
