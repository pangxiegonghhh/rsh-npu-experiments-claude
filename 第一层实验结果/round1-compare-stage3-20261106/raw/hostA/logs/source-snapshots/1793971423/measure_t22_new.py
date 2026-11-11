import argparse,json,time,traceback,hashlib
from pathlib import Path
import numpy as np
from native import BASE,Matrix,Layout,chunks,write_runs
from evaluate_t23 import read_order
def measure(r,out):
 m=Matrix(r['matrix']);tau=r['tau'];W=int(r.get('W',16));member=r.get('start',r['member']);kind=r.get('kind','ls');pi=read_order(r['path'] if r.get('path') else r['runtime_path']);original=read_order(r.get('original_runtime_path',r['runtime_path']));meta=next(x for x in json.loads((BASE/'logs/matrices-and-taus.json').read_text()) if x['matrix']==m.name);t=next(t for t in meta['taus'] if t['tau']==tau);D=[v for v in original if m.deg[v]<=tau];K=pi if kind=='rerun' else [v for v in pi if m.deg[v]>tau];assert sorted(K)==list(np.flatnonzero(m.deg>tau));full=K+D;rows=[];guards=[];summaries=[];source='rerun' if kind=='rerun' else 'pls-'+str(int(float(r.get('lambda',r.get('lam',0)))))
 for diag in [0,1]:
  lc=Layout(m,chunks(K,W),W,diag);base=lc.metrics(full);summaries.append(dict(matrix=m.name,member=member,W=W,tau=tau,diag=f'A{diag}',source=source,**base))
  rules=(['tail','tail-co'] if W!=16 else ['tail','tail-co','gap']) if kind=='rerun' or diag==0 else ['none']
  for rule in rules:
   start=time.time();row=dict(matrix=m.name,member=member,diag=f'A{diag}',W=W,tau=tau,tau_rule=t['tau_rule'],resid_frac=t['resid_frac'],resid_nnz_frac=t['resid_nnz_frac'],source=source,placement=rule,d_rule='none' if rule=='none' else 'D-greedy',status='OK',note='',start_source=r.get('start_source','keep'));row['lambda']='' if kind=='rerun' else r.get('lambda',r.get('lam',0))
   try:
    if rule=='none':row.update(k_windows=base['k_windows'],sumU=base['sumU'],T=base['T'])
    else:
     sigma,guard=lc.layout(full,D,rule,True);stats=lc.metrics(sigma);assert stats['sumU']==base['sumU'] and stats['T']==base['T'];assert stats['write_runs_aic']==stats['k_windows'];row.update(stats,write_runs_resid=write_runs(sigma,D));guards.append(dict(matrix=m.name,member=member,W=W,tau=tau,diag=diag,source=source,placement=rule,d_rule='D-greedy',**guard));np.save(out/(f'A{diag}__{rule}.sigma.npy'),np.asarray(sigma,np.int32))
   except Exception as e:row.update(status='INCOMPLETE',note=str(e))
   row['sec']=time.time()-start;rows.append(row);(out/'results.json').write_text(json.dumps(rows,indent=1))
  lc.close()
 (out/'summaries.json').write_text(json.dumps(summaries,indent=1));(out/'guards.json').write_text(json.dumps(guards,indent=1));return dict(status='OK' if all(x['status']=='OK' for x in rows) else 'INCOMPLETE',rows=len(rows))
if __name__=='__main__':
 from resource_slots import acquire
 cpu_slot=acquire()
 ap=argparse.ArgumentParser();ap.add_argument('record');args=ap.parse_args();r=json.loads(Path(args.record).read_text());out=BASE/'work/t22-new-evaluations'/Path(args.record).stem;out.mkdir(parents=True,exist_ok=True);start=time.time()
 try:result=measure(r,out)
 except Exception as e:result=dict(status='INCOMPLETE',error=str(e),traceback=traceback.format_exc())
 result['seconds']=time.time()-start;(out/'status.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
