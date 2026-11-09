import concurrent.futures,subprocess,json,time,sys
from pathlib import Path
BASE=Path(__file__).resolve().parents[1];cat=BASE/'work/t23-catalog';cat.mkdir(exist_ok=True);records=[]
for r in json.loads((BASE/'logs/reused-orders.json').read_text()):
 if r['task']=='T23' and r['use']=='base-order' and not r['t23_member'].startswith('C6'):records.append(r)
for p in sorted((BASE/'work/generated').glob('*.record.json')):
 r=json.loads(p.read_text())
 if r['status']=='OK':r['runtime_path']=r['path'];records.append(r)
paths=[]
for i,r in enumerate(records):
 p=cat/f'initial-{i:03d}.json';p.write_text(json.dumps(r,indent=2));paths.append(p)
def run(p):
 cmd=[sys.executable,'-B',str(BASE/'scripts/evaluate_t23.py'),str(p)];log=BASE/'logs'/('t23-eval-'+p.stem);start=time.time()
 with open(str(log)+'.stdout','w') as o,open(str(log)+'.stderr','w') as e:
  try:rc=subprocess.run(cmd,cwd=BASE,stdout=o,stderr=e,timeout=7200).returncode
  except subprocess.TimeoutExpired:rc=124
 d=dict(command=cmd,start=start,end=time.time(),exitcode=rc);Path(str(log)+'.command.json').write_text(json.dumps(d,indent=2));print(p.stem,rc,round(time.time()-start,1),flush=True);return d
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:results=list(ex.map(run,paths))
(BASE/'logs/t23-initial-evaluation.json').write_text(json.dumps(results,indent=2))
