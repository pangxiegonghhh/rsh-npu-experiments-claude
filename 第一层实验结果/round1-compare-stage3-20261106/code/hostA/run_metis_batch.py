import concurrent.futures,subprocess,json,time,sys,os
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
def run(m):
 cmd=[sys.executable,'-B','scripts/external_metis.py','--matrix',m];start=time.time();log=BASE/'logs'/('metis-'+m);env=os.environ.copy();env['PYTHONPATH']=str(BASE/'deps/python')
 with open(str(log)+'.stdout','w') as o,open(str(log)+'.stderr','w') as e:
  try:rc=subprocess.run(cmd,cwd=BASE,env=env,stdout=o,stderr=e,timeout=7200).returncode
  except subprocess.TimeoutExpired:rc=124
 r=dict(command=cmd,start=start,end=time.time(),exitcode=rc);Path(str(log)+'.command.json').write_text(json.dumps(r,indent=2));print(m,rc,round(time.time()-start,1),flush=True);return r
with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:records=list(ex.map(run,['ogbn-arxiv','wiki-RfA','dawson5','olafu','pattern1','human_gene1']))
(BASE/'logs/metis-batch.json').write_text(json.dumps(records,indent=2))
