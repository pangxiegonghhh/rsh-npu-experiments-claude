import json,subprocess,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parents[1];records=[]
for matrix in ['cora','ogbn-arxiv','wiki-RfA','dawson5','olafu','pattern1','human_gene1']:
 status=BASE/'work/independent-all'/matrix/'status.json'
 if status.exists() and json.loads(status.read_text())['status']=='OK':continue
 cmd=[sys.executable,'-B','scripts/independent_matrix_job.py',matrix];start=time.time();log=BASE/'logs'/('independent-all-'+matrix)
 with open(str(log)+'.stdout','w') as o,open(str(log)+'.stderr','w') as e:rc=subprocess.run(cmd,cwd=BASE,stdout=o,stderr=e).returncode
 r=dict(command=cmd,start=start,end=time.time(),exitcode=rc);Path(str(log)+'.command.json').write_text(json.dumps(r,indent=2));records.append(r);print(matrix,rc,round(time.time()-start,1),flush=True)
(BASE/'logs/independent-all-first-batch.json').write_text(json.dumps(records,indent=2))
