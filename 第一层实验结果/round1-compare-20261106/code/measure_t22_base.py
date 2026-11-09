import argparse,json,time,traceback,hashlib,sys
from pathlib import Path
import numpy as np
from native import BASE,Matrix,Layout,chunks,write_runs
from evaluate_t23 import read_order
def measure(r,out):
 m=Matrix(r['matrix']);pi=read_order(r['runtime_path']);W=int(r.get('W',16));member=r['member'];meta=next(x for x in json.loads((BASE/'logs/matrices-and-taus.json').read_text()) if x['matrix']==m.name);full=chunks(pi,W);offsets=list(range(2,16,2)) if m.name in ['pattern1','human_gene1'] and W==16 else list(range(1,W));phases=[]
 for s in offsets:
  lc=Layout(m,chunks(pi,W,s),W);stats=lc.metrics(pi);lc.close();phases.append(dict(offset=s,**stats))
 phaseT=sum(x['T'] for x in phases)/len(phases);fours=[];results=[];guards=[];sigma_records=[]
 for diag in [0,1]:
  lc=Layout(m,full,W,diag);fm=lc.metrics(pi);lc.close()
  for t in meta['taus']:
   tau=t['tau'];mask=m.deg<=tau;K=[v for v in pi if not mask[v]];D=[v for v in pi if mask[v]];inplace=[[v for v in w if not mask[v]] for w in full];inplace=[w for w in inplace if w];wins=chunks(K,W);lc=Layout(m,inplace,W,diag);im=lc.metrics(pi);lc.close();lc=Layout(m,wins,W,diag);km=lc.metrics(K+D)
   fours.append(dict(matrix=m.name,diag=f'A{diag}',member=member,W=W,tau=tau,T_full=fm['T'],T_inplace=im['T'],T_keep=km['T'],T_rerun='',U_full=fm['sumU'],U_inplace=im['sumU'],U_keep=km['sumU'],U_rerun='',k_inplace=im['k_windows'],T_full_phase=phaseT if diag==0 else '',align_premium=phaseT-fm['T'] if diag==0 else '',offsets_used=offsets if diag==0 else []))
   cases=[('tail',False),('tail',True),('tail-co',True)] if W!=16 else [('tail',False),('tail',True),('inplace',False),('inplace',True),('snap',False),('snap',True),('tail-co',True),('gap',True)]
   for rule,d in cases:
    tm=time.time();row=dict(matrix=m.name,diag=f'A{diag}',member=member,W=W,tau=tau,tau_rule=t['tau_rule'],resid_frac=t['resid_frac'],resid_nnz_frac=t['resid_nnz_frac'],source='keep',placement=rule,d_rule='D-greedy' if d else 'own',status='OK',note='');row['lambda']=''
    try:
     sigma,guard=lc.layout(pi,D,rule,d);stats=lc.metrics(sigma);assert stats['sumU']==km['sumU'] and stats['T']==km['T'];assert rule=='inplace' or stats['write_runs_aic']==stats['k_windows'];row.update(stats,write_runs_resid=write_runs(sigma,D));guards.append(dict(matrix=m.name,member=member,W=W,tau=tau,diag=diag,source='keep',placement=rule,d_rule=row['d_rule'],**guard));key=f"A{diag}__tau{tau}__{rule}__{row['d_rule']}";p=out/(key+'.sigma.npy');np.save(p,np.asarray(sigma,np.int32));sigma_records.append(dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),windows_sha256=hashlib.sha256(np.asarray(K,np.int32).tobytes()).hexdigest(),**{k:row[k] for k in ['matrix','member','W','tau','diag','source','placement','d_rule']}))
    except Exception as e:row.update(status='INCOMPLETE',note=str(e))
    row['sec']=time.time()-tm;results.append(row);(out/'results.json').write_text(json.dumps(results,indent=1))
   lc.close()
   (out/'four-base.json').write_text(json.dumps(fours,indent=1))
 (out/'phase.json').write_text(json.dumps(phases,indent=1));(out/'guards.json').write_text(json.dumps(guards,indent=1));(out/'sigmas.json').write_text(json.dumps(sigma_records,indent=1));return dict(status='OK' if all(x['status']=='OK' for x in results) else 'INCOMPLETE',rows=len(results))
if __name__=='__main__':
 from resource_slots import acquire
 cpu_slot=acquire()
 ap=argparse.ArgumentParser();ap.add_argument('record');args=ap.parse_args();r=json.loads(Path(args.record).read_text());out=BASE/'work/t22-evaluations'/Path(args.record).stem;out.mkdir(parents=True,exist_ok=True);start=time.time()
 try:result=measure(r,out)
 except Exception as e:result=dict(status='INCOMPLETE',error=str(e),traceback=traceback.format_exc())
 result['seconds']=time.time()-start;(out/'status.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
