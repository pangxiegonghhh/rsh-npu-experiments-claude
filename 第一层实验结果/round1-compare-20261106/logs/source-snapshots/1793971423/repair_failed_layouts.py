import concurrent.futures,hashlib,json,time,traceback
from pathlib import Path
import numpy as np
from native import BASE,Matrix,Layout,chunks,write_runs
from evaluate_t23 import read_order
out=BASE/'work/t22-layout-repairs';out.mkdir(exist_ok=True);seen=set();pool=concurrent.futures.ThreadPoolExecutor(max_workers=1);futures=[]
def repair(folder,record,row,index):
 key=folder.parent.name+'__'+folder.name+f'__row{index}';dest=out/key;dest.mkdir(exist_ok=True);start=time.time();result=dict(row)
 try:
  m=Matrix(row['matrix']);tau=row['tau'];W=row['W'];pi=read_order(record.get('path',record['runtime_path']));original=read_order(record.get('original_runtime_path',record['runtime_path']));D=[v for v in original if m.deg[v]<=tau]
  K=pi if record.get('kind')=='rerun' else [v for v in pi if m.deg[v]>tau];full=K+D;lc=Layout(m,chunks(K,W),W,int(row['diag'][1]));sigma,guard=lc.layout(pi if len(pi)==m.n else full,D,row['placement'],row['d_rule']=='D-greedy');metrics=lc.metrics(sigma);lc.close();assert metrics['write_runs_aic']==metrics['k_windows'];result.update(metrics,write_runs_resid=write_runs(sigma,D),sec=time.time()-start,status='OK',note='exact packed port-candidate representation; original workspace failure retained',**guard);np.save(dest/'sigma.npy',np.asarray(sigma,np.int32));result['sigma_sha256']=hashlib.sha256((dest/'sigma.npy').read_bytes()).hexdigest()
 except Exception as e:result.update(status='INCOMPLETE',note=str(e),traceback=traceback.format_exc(),sec=time.time()-start)
 (dest/'replacement-row.json').write_text(json.dumps(result,indent=2));(dest/'source.json').write_text(json.dumps(dict(original_results=str(folder/'results.json'),original_row_index=index,record=record,old_row=row,representation='packed, all logical candidates retained and ordered identically'),indent=2));print(key,result['status'],round(time.time()-start,1),flush=True)
while True:
 for root,cat in [('t22-evaluations','t22-base-catalog'),('t22-new-evaluations','t22-new-eval-catalog')]:
  for f in (BASE/'work'/root).glob('*/status.json'):
   folder=f.parent;rows=folder/'results.json';recordpath=BASE/'work'/cat/(folder.name+'.json')
   if not rows.exists() or not recordpath.exists():continue
   record=json.loads(recordpath.read_text())
   for index,row in enumerate(json.loads(rows.read_text())):
    key=(str(folder),index)
    if key in seen or row['status']!='INCOMPLETE' or 'inter candidate workspace' not in row.get('note',''):continue
    seen.add(key);dest=out/(folder.parent.name+'__'+folder.name+f'__row{index}')/'replacement-row.json'
    if dest.exists():continue
    futures.append(pool.submit(repair,folder,record,row,index))
 if (BASE/'logs/t22-base-evaluations.json').exists() and (BASE/'logs/t22-new-evaluations.json').exists():break
 time.sleep(5)
pool.shutdown(wait=True)
for f in futures:f.result()
(BASE/'logs/t22-layout-repairs-complete.json').write_text(json.dumps(dict(attempted=len(futures),complete=True),indent=2))
