import concurrent.futures,json,subprocess,time,sys
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
def run(t):
 matrix,mode,rep=t;cmd=[sys.executable,'-B','scripts/rabbit_family.py','--matrix',matrix,'--mode',mode,'--rep',str(rep)];log=BASE/'logs'/f'rabbit-family-{matrix}-{mode}-{rep}';start=time.time()
 with open(str(log)+'.stdout','w') as o,open(str(log)+'.stderr','w') as e:
  try:rc=subprocess.run(cmd,cwd=BASE,stdout=o,stderr=e,timeout=7200).returncode
  except subprocess.TimeoutExpired:rc=124
 r=dict(command=cmd,start=start,end=time.time(),exitcode=rc);Path(str(log)+'.command.json').write_text(json.dumps(r,indent=2));print(matrix,mode,rep,rc,round(time.time()-start,1),flush=True);return r
tasks=[(m,mode,0) for m in ['cora','ogbn-arxiv','wiki-RfA','dawson5','olafu','pattern1','human_gene1'] for mode in ['B','U']]+[(m,mode,rep) for m in ['cora','ogbn-arxiv'] for mode in ['B','U'] for rep in [1,2]]
with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:records=list(ex.map(run,tasks))
(BASE/'logs/rabbit-primary-batch.json').write_text(json.dumps(records,indent=2))
