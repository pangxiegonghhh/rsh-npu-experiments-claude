import concurrent.futures,json,subprocess,time,sys
from pathlib import Path
from resume_utils import completed_post
BASE=Path(__file__).resolve().parents[1];cat=BASE/'work/t23-rabbit-catalog';cat.mkdir(exist_ok=True);meta={m['matrix']:m for m in json.loads((BASE/'logs/matrices-and-taus.json').read_text())};evalpool=concurrent.futures.ThreadPoolExecutor(max_workers=2);postpool=concurrent.futures.ThreadPoolExecutor(max_workers=1);seen=set();futures=[];donepost=completed_post()
def run(cmd,label):
 p=Path(cmd[-1])
 if 'evaluate_t23.py' in cmd and (BASE/'work/t23-evaluations'/p.stem/'status.json').exists():return dict(skipped_completed=True)
 log=BASE/'logs'/label;start=time.time()
 with open(str(log)+'.stdout','w') as o,open(str(log)+'.stderr','w') as e:
  try:rc=subprocess.run(cmd,cwd=BASE,stdout=o,stderr=e,timeout=7200).returncode
  except subprocess.TimeoutExpired:rc=124
 record=dict(command=cmd,start=start,end=time.time(),exitcode=rc);Path(str(log)+'.command.json').write_text(json.dumps(record,indent=2));print(label,rc,round(time.time()-start,1),flush=True);return record
while True:
 for p in sorted((BASE/'work/external').glob('*__C5*__W16__*.record.json')):
  if p.name in seen:continue
  r=json.loads(p.read_text())
  if r['status']!='OK' or r['method'] not in ['C5','C5-U']:continue
  seen.add(p.name);q=cat/('rabbit-'+p.stem+'.json');q.write_text(json.dumps(r,indent=2));futures.append(evalpool.submit(run,[sys.executable,'-B','scripts/evaluate_t23.py',str(q)],'t23-rabbit-eval-'+p.stem))
  if r['seed']==0:
   for t in meta[r['matrix']]['taus']:
    if (r['matrix'],r['method'],t['tau']) in donepost:continue
    row=dict(r,member=r['method'],tau=t['tau'],reuse=False);q=BASE/'work/post-e-catalog'/f"{r['matrix']}__{r['method']}__tau{t['tau']}.json";q.write_text(json.dumps(row,indent=2));futures.append(postpool.submit(run,[sys.executable,'-B','scripts/post_e_job.py',str(q)],'post-e-'+q.stem))
 if (BASE/'logs/rabbit-primary-batch.json').exists():break
 time.sleep(5)
evalpool.shutdown(wait=True);postpool.shutdown(wait=True);records=[f.result() for f in futures];(BASE/'logs/rabbit-eval-post.json').write_text(json.dumps(records,indent=2))
