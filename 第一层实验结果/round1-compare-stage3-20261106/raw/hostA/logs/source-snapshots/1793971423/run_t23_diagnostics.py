import concurrent.futures,json,subprocess,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parents[1];cat=BASE/'work/t23-diag-catalog';cat.mkdir(exist_ok=True);records=[]
for p in sorted((BASE/'work/t23-catalog').glob('initial-*.json')):
 r=json.loads(p.read_text())
 if int(r.get('seed') or 0)==0:records.append(r)
for p in sorted((BASE/'work/external').glob('*.record.json')):
 r=json.loads(p.read_text())
 if r['status']=='OK' and r['seed']==0 and r['method'] in ['C1-J','C1-H','C5','C5-U','C8-METIS']:records.append(r)
paths=[]
for i,r in enumerate(records):
 p=cat/f'diag-{i:03d}.json';p.write_text(json.dumps(r,indent=2));paths.append(p)
def run(p):
 cmd=[sys.executable,'-B','scripts/diagnose_t23.py',str(p)];log=BASE/'logs'/('t23-diag-'+p.stem);start=time.time()
 with open(str(log)+'.stdout','w') as o,open(str(log)+'.stderr','w') as e:
  try:rc=subprocess.run(cmd,cwd=BASE,stdout=o,stderr=e,timeout=7200).returncode
  except subprocess.TimeoutExpired:rc=124
 r=dict(command=cmd,start=start,end=time.time(),exitcode=rc);Path(str(log)+'.command.json').write_text(json.dumps(r,indent=2));print(p.stem,rc,round(time.time()-start,1),flush=True);return r
with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:records=list(ex.map(run,paths))
(BASE/'logs/t23-diagnostics.json').write_text(json.dumps(records,indent=2))
