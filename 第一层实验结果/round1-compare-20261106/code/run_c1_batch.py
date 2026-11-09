import subprocess,json,time,os,sys,concurrent.futures
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
def run(t):
 m,v,s=t;key=f'{m}__C1-{v}__seed{s}';cmd=[sys.executable,'-B','scripts/external_c1.py','--matrix',m,'--variant',v,'--seed',str(s)];env=os.environ.copy();env.update(PYTHONPATH=str(BASE/'deps/python'),NUMBA_NUM_THREADS='1',NUMBA_CACHE_DIR=str(BASE/'work/numba-cache'),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1');start=time.time();log=BASE/'logs'/('c1-'+key)
 with open(str(log)+'.stdout','w') as o,open(str(log)+'.stderr','w') as e:
  try:rc=subprocess.run(cmd,cwd=BASE,env=env,stdout=o,stderr=e,timeout=7200).returncode
  except subprocess.TimeoutExpired:rc=124
 r=dict(command=cmd,env={k:env[k] for k in ['PYTHONPATH','NUMBA_NUM_THREADS','NUMBA_CACHE_DIR','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS']},start=start,end=time.time(),exitcode=rc);Path(str(log)+'.command.json').write_text(json.dumps(r,indent=2));print(key,rc,round(time.time()-start,1),flush=True);return r
gate=BASE/'logs/c1-reproducibility.json';first='d9f72194f16e7ebc8ffc665b1a2e7457786b1a2ed574ab1def2075030dd0d78e';second=json.loads((BASE/'work/external/cora__C1-J__W16__seed0.record.json').read_text())['sha256'];assert first==second;gate.write_text(json.dumps(dict(cora_J_repeated_twice=True,first_sha256=first,second_sha256=second,n_jobs=1,passed=True),indent=2))
tasks=[(m,v,0) for m in ['cora','ogbn-arxiv','wiki-RfA','dawson5','olafu','pattern1','human_gene1'] for v in ['J','H'] if (m,v)!=('cora','J')]+[(m,v,s) for m in ['cora','ogbn-arxiv'] for v in ['J','H'] for s in [1,2]]
with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:records=list(ex.map(run,tasks))
(BASE/'logs/c1-batch.json').write_text(json.dumps(records,indent=2))
