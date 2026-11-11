import concurrent.futures,json,subprocess,time,sys
from pathlib import Path
BASE=Path(__file__).resolve().parents[1];cat=BASE/'work/t22-base-catalog';cat.mkdir(exist_ok=True);reuse=json.loads((BASE/'logs/reused-orders.json').read_text());records=[r for r in reuse if r['task']=='T22' and r['use'] in ['base-order','LS-full']]
for r in reuse:
 if r['task']=='T23' and r['use']=='W-sensitivity' and r['matrix'] in ['cora','ogbn-arxiv'] and int(r['W']) in [32,64]:records.append(dict(r,member='rsh-α0' if r['t23_member']=='B1' else r['t23_member']))
paths=[]
for i,r in enumerate(records):
 p=cat/f'base-{i:03d}.json';p.write_text(json.dumps(r,indent=2));paths.append(p)
def run(p):
 cmd=[sys.executable,'-B','scripts/measure_t22_base.py',str(p)];log=BASE/'logs'/('t22-base-'+p.stem);start=time.time()
 with open(str(log)+'.stdout','w') as o,open(str(log)+'.stderr','w') as e:
  try:rc=subprocess.run(cmd,cwd=BASE,stdout=o,stderr=e,timeout=7200).returncode
  except subprocess.TimeoutExpired:rc=124
 r=dict(command=cmd,start=start,end=time.time(),exitcode=rc);Path(str(log)+'.command.json').write_text(json.dumps(r,indent=2));print(p.stem,rc,round(time.time()-start,1),flush=True);return r
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:records=list(ex.map(run,paths))
(BASE/'logs/t22-base-evaluations.json').write_text(json.dumps(records,indent=2))
