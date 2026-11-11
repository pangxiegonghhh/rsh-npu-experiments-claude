import concurrent.futures,json,subprocess,time,sys,os
from pathlib import Path
BASE=Path(__file__).resolve().parents[1];methods=['C2-LSH','C3-W1','C3-W4','C4-U','C4-T','C7-I'];matrices=['cora','ogbn-arxiv','wiki-RfA','dawson5','olafu','pattern1','human_gene1']
assert json.loads((BASE/'logs/candidate-port-gate.json').read_text())['passed']
def run(t):
 m,c,s=t;key=f'{m}__{c}__W16__seed{s}';cmd=[sys.executable,'-B',str(BASE/'scripts/generate_pure.py'),'--matrix',m,'--method',c,'--seed',str(s)];p=BASE/'logs'/('candidate-'+key);start=time.time()
 with open(str(p)+'.stdout','w') as o,open(str(p)+'.stderr','w') as e:
  try:r=subprocess.run(cmd,cwd=BASE,stdout=o,stderr=e,timeout=7200);rc=r.returncode
  except subprocess.TimeoutExpired:rc=124
 record=dict(command=cmd,start=start,end=time.time(),exitcode=rc);Path(str(p)+'.command.json').write_text(json.dumps(record,indent=2));print(key,rc,round(time.time()-start,1),flush=True);return record
tasks=[(m,c,0) for m in matrices for c in methods]+[(m,'C2-LSH',s) for m in matrices[:2] for s in (1,2)]
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:records=list(ex.map(run,tasks))
(BASE/'logs/pure-batch.json').write_text(json.dumps(records,indent=2))
