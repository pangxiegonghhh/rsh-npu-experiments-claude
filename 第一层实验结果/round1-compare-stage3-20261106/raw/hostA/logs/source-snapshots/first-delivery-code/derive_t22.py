import csv,json,math
from pathlib import Path
import numpy as np
from scipy.stats import kendalltau
from native import BASE,Matrix,Layout,chunks
from evaluate_t23 import read_order
from resource_slots import acquire
from naming import t22_start
def canon(name):return 'rsh-α0' if name.startswith('B1') else name
def record_for(folder):
 for root in ['t22-new-eval-catalog','extra-order-jobs']:
  p=BASE/'work'/root/(folder.name+'.json')
  if p.exists():return json.loads(p.read_text())
 raise RuntimeError('missing source record '+str(folder))
def derive():
 out=BASE/'work/t22-derived';out.mkdir(exist_ok=True);fours={};summary={};reused=json.loads((BASE/'logs/reused-orders.json').read_text());metadata={x['matrix']:x for x in json.loads((BASE/'logs/matrices-and-taus.json').read_text())};ranks=[];cross=[]
 for p in (BASE/'work/t22-evaluations').glob('*/four-base.json'):
  for row in json.loads(p.read_text()):
   row['member']=canon(row['member']);key=(row['matrix'],row['diag'],row['member'],row['W'],row['tau'])
   if key in fours:assert fours[key]==row,(key,fours[key],row)
   fours[key]=row
 for p in (BASE/'work/t22-new-evaluations').glob('*/summaries.json'):
  r=record_for(p.parent);start_source=r.get('start_source','keep')
  for row in json.loads(p.read_text()):
   row['member']=canon(t22_start(r));key=(row['matrix'],row['diag'],row['member'],row['W'],row['tau'],row['source'],start_source)
   if key in summary:assert summary[key]['T']==row['T'] and summary[key]['sumU']==row['sumU']
   summary[key]=row
 for key,row in fours.items():
  rr=summary.get((*key,'rerun','keep'))
  if rr:row.update(T_rerun=rr['T'],U_rerun=rr['sumU'])
  elif row['member'].startswith('LS-full'):row.update(T_rerun='—',U_rerun='—')
 base9=['B0','rsh-α0','rabbit-pilot','neutron-pilot','C9-Gorder','C9-S','C10-BP','B-RCM-ref','SlashBurn'];p0=base9[:7]
 for matrix in [x['matrix'] for x in metadata.values() if x['matrix'] not in ['reddit','ogbn-products']]:
  for t in metadata[matrix]['taus']:
   for diag in ['A0','A1']:
    cases={m:fours.get((matrix,diag,m,16,t['tau'])) for m in base9+(['LS-full(C9-Gorder)','LS-full(rsh-α0)'] if matrix in ['cora','ogbn-arxiv','wiki-RfA'] else [])}
    for comparison,expected in [('full_vs_keep',list(cases)),('keep_vs_rerun',base9),('keep_vs_afterE',p0)]:
     for noB0 in [False,True]:
      wanted=[m for m in expected if not noB0 or m!='B0'];members=[];a=[];b=[]
      for m in wanted:
       f=cases.get(m)
       if not f:continue
       if comparison=='full_vs_keep':x,y=f['T_full'],f['T_keep']
       elif comparison=='keep_vs_rerun':x,y=f['T_keep'],f.get('T_rerun','')
       else:
        e=summary.get((matrix,diag,m,16,t['tau'],'pls-0','keep'));x,y=f['T_keep'],e['T'] if e else ''
       if not isinstance(x,(int,float)) or not isinstance(y,(int,float)):continue
       members.append(m);a.append(x);b.append(y)
      tau=float(kendalltau(a,b,variant='b').statistic) if len(a)>=2 else float('nan');ranks.append(dict(matrix=matrix,diag=diag,W=16,tau=t['tau'],comparison=comparison,exclude_B0=noB0,members=members,n_methods=len(members),kendall_tau_b=tau if math.isfinite(tau) else '',status='OK' if members==wanted else 'INCOMPLETE',note='undefined tau_b when all ties' if not math.isfinite(tau) else ''))
  mtx=Matrix(matrix)
  for member in ['C9-Gorder','rsh-α0','C10-BP','SlashBurn']:
   pi=read_order(next(x for x in reused if x['task']=='T22' and x['use']=='base-order' and x['matrix']==matrix and x['member']==member)['runtime_path'])
   for assumed,actual in [(metadata[matrix]['taus'][0]['tau'],metadata[matrix]['taus'][1]['tau']),(metadata[matrix]['taus'][1]['tau'],metadata[matrix]['taus'][0]['tau'])]:
    source=BASE/'work/order-jobs'/f'{matrix}__{member}__rerun__tau{assumed}__lamnone.record.json';valid=source.exists() and json.loads(source.read_text()).get('status')=='OK';sig=None
    if valid:
     r=json.loads(source.read_text());sig=read_order(r['path'])+[v for v in pi if mtx.deg[v]<=assumed];assert sorted(sig)==list(range(mtx.n));kept=[v for v in sig if mtx.deg[v]>actual]
    for diag in ['A0','A1']:
     f=fours.get((matrix,diag,member,16,actual));row=dict(matrix=matrix,diag=diag,member=member,W=16,assumed_tau=assumed,actual_tau=actual,T_keep_pi=f['T_keep'] if f else '',T_rerun_actual=f.get('T_rerun','') if f else '',status='OK' if valid and f and isinstance(f.get('T_rerun'),(int,float)) else 'INCOMPLETE',note='')
     if sig is not None:
      lc=Layout(mtx,chunks(kept),diag=int(diag[1]));s=lc.metrics(sig);lc.close();row.update(T_sig_assumed=s['T'],sumU_sig_assumed=s['sumU'])
     else:row['note']='assumed-tau rerun unavailable'
     cross.append(row)
 (out/'four_numbers.json').write_text(json.dumps(list(fours.values()),indent=1));(out/'kendall.json').write_text(json.dumps(ranks,indent=1));(out/'cross_tau.json').write_text(json.dumps(cross,indent=1));print('T22_DERIVED',len(fours),len(ranks),len(cross),flush=True)
if __name__=='__main__':token=acquire();derive()
