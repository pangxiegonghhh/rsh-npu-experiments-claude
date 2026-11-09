import concurrent.futures,json,subprocess,time,sys
from pathlib import Path
BASE=Path(__file__).resolve().parents[1];cat=BASE/'work/t22-extra-catalog';cat.mkdir(exist_ok=True);out=BASE/'work/extra-order-jobs';out.mkdir(exist_ok=True);pool=concurrent.futures.ThreadPoolExecutor(max_workers=1);futures=[];seen=set();reuse=json.loads((BASE/'logs/reused-orders.json').read_text());meta={x['matrix']:x for x in json.loads((BASE/'logs/matrices-and-taus.json').read_text())}
def command(cmd,key):
 log=BASE/'logs'/key;start=time.time()
 with open(str(log)+'.stdout','w') as o,open(str(log)+'.stderr','w') as e:
  try:rc=subprocess.run(cmd,cwd=BASE,stdout=o,stderr=e,timeout=7200).returncode
  except subprocess.TimeoutExpired:rc=124
 d=dict(command=cmd,start=start,end=time.time(),exitcode=rc);Path(str(log)+'.command.json').write_text(json.dumps(d,indent=2));print(key,rc,round(time.time()-start,1),flush=True);return rc
def order_and_eval(r,key):
 p=cat/(key+'.json');p.write_text(json.dumps(r,indent=2));command([sys.executable,'-B','scripts/order_job.py',str(p),'--output-dir',str(out)],'extra-order-'+key);q=out/(key+'.record.json')
 if q.exists():
  record=json.loads(q.read_text())
  if record['status']=='OK' and record.get('tau') is not None:command([sys.executable,'-B','scripts/measure_t22_new.py',str(q)],'extra-eval-'+key)
def base_eval(r,key):
 r=dict(r,member='LS-full('+r['member']+')',runtime_path=r['path']);p=BASE/'work/t22-base-catalog'/(key+'.json');p.write_text(json.dumps(r,indent=2));command([sys.executable,'-B','scripts/measure_t22_base.py',str(p)],'extra-base-'+key)
for r in reuse:
 if r['task']=='T23' and r['use']=='W-sensitivity' and r['matrix'] in ['cora','ogbn-arxiv'] and int(r['W']) in [32,64]:
  member='rsh-α0' if r['t23_member'].startswith('B1') else r['t23_member']
  for tau in [None]+[x['tau'] for x in meta[r['matrix']]['taus']]:
   row=dict(r,member=member,kind='rerun',tau=tau,W=int(r['W']),seed=0);key=f"{r['matrix']}__{member}__W{r['W']}__rerun__tau{tau}";futures.append(pool.submit(order_and_eval,row,key))
while True:
 for matrix in meta:
  for t in meta[matrix]['taus']:
   parent=BASE/'work/order-jobs'/f"{matrix}__C10-BP__rerun__tau{t['tau']}__lamnone.record.json"
   if not parent.exists():continue
   r=json.loads(parent.read_text())
   if r['status']!='OK':continue
   for lam in [0,1]:
    key=f"{matrix}__C10-BP__rerun-start-LS__tau{t['tau']}__lam{lam}"
    if key in seen:continue
    seen.add(key);row=dict(r,member='C10-BP',kind='ls',tau=t['tau'],W=16,seed=0,start_source='rerun',runtime_path=r['path'],original_runtime_path=r['runtime_path'],**{'lambda':lam});futures.append(pool.submit(order_and_eval,row,key))
 for p in (BASE/'work/order-jobs').glob('wiki-RfA__*__lsfull__*.record.json'):
  if p.name in seen:continue
  r=json.loads(p.read_text())
  if r['status']!='OK':continue
  seen.add(p.name);futures.append(pool.submit(base_eval,r,'LSfull-'+p.stem))
 if (BASE/'logs/t22-order-jobs.json').exists():break
 time.sleep(5)
pool.shutdown(wait=True)
for f in futures:f.result()
(BASE/'logs/t22-extras-complete.json').write_text(json.dumps(dict(tasks=len(futures),complete=True),indent=2))
