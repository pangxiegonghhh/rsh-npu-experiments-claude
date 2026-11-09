import concurrent.futures,json,subprocess,sys,time
from pathlib import Path
from naming import t23_name
BASE=Path(__file__).resolve().parents[1];reuse=json.loads((BASE/'logs/reused-orders.json').read_text());meta={m['matrix']:m for m in json.loads((BASE/'logs/matrices-and-taus.json').read_text())};cat=BASE/'work/post-e-catalog';cat.mkdir(exist_ok=True);records=[]
for p in sorted((BASE/'work/t23-catalog').glob('initial-*.json')):
 r=json.loads(p.read_text());member=t23_name(r.get('t23_member',r.get('method')))
 if member in ['B-RCM-ref','rabbit-pilot','neutron-pilot'] or int(r.get('seed',0))!=0:continue
 for t in meta[r['matrix']]['taus']:
  row=dict(r,member=member,tau=t['tau'],W=16,reuse=False)
  alias='rsh-α0' if member=='B1' else member;old=next((x for x in reuse if x['task']=='T23' and x['use']=='post-E-reuse' and x['matrix']==r['matrix'] and f'start={alias},' in x['params'] and f'tau={t["tau"]},' in x['params']),None)
  if old:row.update(runtime_path=old['runtime_path'],sha256=old['sha256'],reuse=True,reuse_origin=old)
  records.append(row)
paths=[]
for r in records:
 p=cat/f"{r['matrix']}__{r['member']}__tau{r['tau']}.json";p.write_text(json.dumps(r,indent=2));paths.append(p)
def run(p):
 cmd=[sys.executable,'-B','scripts/post_e_job.py',str(p)];log=BASE/'logs'/('post-e-'+p.stem);start=time.time()
 with open(str(log)+'.stdout','w') as o,open(str(log)+'.stderr','w') as e:
  try:rc=subprocess.run(cmd,cwd=BASE,stdout=o,stderr=e,timeout=7200).returncode
  except subprocess.TimeoutExpired:rc=124
 r=dict(command=cmd,start=start,end=time.time(),exitcode=rc);Path(str(log)+'.command.json').write_text(json.dumps(r,indent=2));print(p.stem,rc,round(time.time()-start,1),flush=True);return r
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:records=list(ex.map(run,paths))
(BASE/'logs/post-e-initial-batch.json').write_text(json.dumps(records,indent=2))
