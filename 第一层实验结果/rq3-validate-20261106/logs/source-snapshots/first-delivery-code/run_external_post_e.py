import concurrent.futures,json,subprocess,time,sys
from pathlib import Path
from resume_utils import completed_post
BASE=Path(__file__).resolve().parents[1];meta={m['matrix']:m for m in json.loads((BASE/'logs/matrices-and-taus.json').read_text())};cat=BASE/'work/post-e-catalog';cat.mkdir(exist_ok=True);records=[];done=completed_post()
for p in sorted((BASE/'work/external').glob('*.record.json')):
 r=json.loads(p.read_text())
 if r['status']!='OK' or r['seed']!=0 or r['method'] not in ['C1-J','C1-H','C8-METIS']:continue
 for t in meta[r['matrix']]['taus']:
  if (r['matrix'],r['method'],t['tau']) in done:continue
  row=dict(r,member=r['method'],tau=t['tau'],reuse=False);q=cat/f"{r['matrix']}__{r['method']}__tau{t['tau']}.json";q.write_text(json.dumps(row,indent=2));records.append(q)
def execute(p):
 cmd=[sys.executable,'-B','scripts/post_e_job.py',str(p)];log=BASE/'logs'/('post-e-'+p.stem);start=time.time()
 with open(str(log)+'.stdout','w') as o,open(str(log)+'.stderr','w') as e:
  try:rc=subprocess.run(cmd,cwd=BASE,stdout=o,stderr=e,timeout=7200).returncode
  except subprocess.TimeoutExpired:rc=124
 r=dict(command=cmd,start=start,end=time.time(),exitcode=rc);Path(str(log)+'.command.json').write_text(json.dumps(r,indent=2));print(p.stem,rc,round(time.time()-start,1),flush=True);return r
with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:records=list(ex.map(execute,records))
(BASE/'logs/external-post-e.json').write_text(json.dumps(records,indent=2))
