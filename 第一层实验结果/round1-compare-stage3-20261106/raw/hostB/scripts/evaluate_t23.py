import argparse,json,time,traceback,sys,hashlib,resource
from pathlib import Path
import numpy as np
from native import BASE,Matrix,Layout,chunks
sys.dont_write_bytecode=True
def read_order(path):
 d=json.loads(Path(path).read_text());return d['row_perm'] if isinstance(d,dict) else d
def evaluate(record,folder):
 assert json.loads((BASE/'logs/layout-port-gate.json').read_text())['passed']
 start=time.time();m=Matrix(record['matrix']);pi=read_order(record['runtime_path']);assert sorted(pi)==list(range(m.n));W=int(record.get('W',16));name=record.get('t23_member',record.get('method'))
 meta=next(x for x in json.loads((BASE/'logs/matrices-and-taus.json').read_text()) if x['matrix']==m.name);taus=[t for t in meta['taus'] if 'eval_taus' not in record or t['tau'] in record['eval_taus']];rows=[];guards=[]
 def emit(lc,tau,placement,rule,diag,D,tm):
  r=dict(matrix=m.name,member=name,diag=f'A{diag}',W=W,tau=tau,placement=placement,d_rule=rule,source='own',seed=record.get('seed',0),member_params=record.get('params',''),order_sec=record.get('seconds',''),post_sec=0,status='OK',note='',tau_rule='none' if tau=='none' else next(t['tau_rule'] for t in taus if t['tau']==tau),resid_frac=len(D)/m.n)
  try:
   sig,st=lc.layout(pi,D,placement if tau!='none' else 'tail',rule=='D-greedy');r.update(lc.metrics(sig),d_sec=time.time()-tm,co_chain_guard_windows_skipped=st['co_chain_guard_windows_skipped']);guards.append(dict(matrix=m.name,member=name,W=W,tau=tau,diag=diag,source='own',placement=placement,d_rule=rule,**st))
  except Exception as e:r.update(status='INCOMPLETE',note=str(e),d_sec=time.time()-tm)
  r.update(peak_mem_mb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/(2**20 if __import__('sys').platform=='darwin' else 2**10));rows.append(r);(folder/'rows.json').write_text(json.dumps(rows,indent=1))
 for diag in [0,1]:
  lc=Layout(m,chunks(pi,W),W,diag)
  for rule in ['own','D-greedy']:emit(lc,'none','none',rule,diag,[],time.time())
  lc.close()
  for t in taus:
   tau=t['tau'];mask=m.deg<=tau;D=[v for v in pi if mask[v]];kept=[v for v in pi if not mask[v]];lc=Layout(m,chunks(kept,W),W,diag)
   for placement,rule in [('tail-co','own'),('tail-co','D-greedy'),('tail','own'),('tail','D-greedy')]:emit(lc,tau,placement,rule,diag,D,time.time())
   lc.close()
 (folder/'guards.json').write_text(json.dumps(guards,indent=1));return dict(status='OK' if all(r['status']=='OK' for r in rows) else 'INCOMPLETE',rows=len(rows),seconds=time.time()-start)
if __name__=='__main__':
 from resource_slots import acquire
 cpu_slot=acquire()
 ap=argparse.ArgumentParser();ap.add_argument('record');args=ap.parse_args();r=json.loads(Path(args.record).read_text());out=BASE/'work'/r.get('evaluation_root','t23-evaluations')/Path(args.record).stem;out.mkdir(parents=True,exist_ok=True)
 try:result=evaluate(r,out)
 except Exception as e:result=dict(status='INCOMPLETE',error=str(e),traceback=traceback.format_exc())
 (out/'status.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
