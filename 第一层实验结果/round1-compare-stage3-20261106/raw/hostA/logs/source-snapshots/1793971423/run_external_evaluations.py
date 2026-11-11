import concurrent.futures,json,subprocess,sys,time,os
from pathlib import Path
BASE=Path(__file__).resolve().parents[1];seen=set();cat=BASE/'work/t23-external-catalog';cat.mkdir(exist_ok=True);pool=concurrent.futures.ThreadPoolExecutor(max_workers=2);futures=[]
def execute(p):
 cmd=[sys.executable,'-B','scripts/evaluate_t23.py',str(p)];log=BASE/'logs'/('t23-external-eval-'+p.stem);start=time.time()
 with open(str(log)+'.stdout','w') as o,open(str(log)+'.stderr','w') as e:
  try:rc=subprocess.run(cmd,cwd=BASE,stdout=o,stderr=e,timeout=7200).returncode
  except subprocess.TimeoutExpired:rc=124
 r=dict(command=cmd,start=start,end=time.time(),exitcode=rc);Path(str(log)+'.command.json').write_text(json.dumps(r,indent=2));print(p.stem,rc,round(time.time()-start,1),flush=True);return r
while True:
 for p in sorted((BASE/'work/external').glob('*.record.json')):
  if p.name in seen:continue
  r=json.loads(p.read_text())
  if r['status']!='OK':continue
  seen.add(p.name);q=cat/('external-'+p.stem+'.json');q.write_text(json.dumps(r,indent=2));futures.append(pool.submit(execute,q))
 if (BASE/'logs/c1-batch.json').exists() and (BASE/'logs/metis-batch.json').exists():break
 time.sleep(5)
pool.shutdown(wait=True);records=[f.result() for f in futures];(BASE/'logs/external-evaluations.json').write_text(json.dumps(records,indent=2))
