import hashlib,json,math
from pathlib import Path
from native import BASE
from derive_t22 import canon,record_for
from collect_t23_first import dumpcsv
from naming import t22_start
FIELDS='matrix diag member W tau tau_rule resid_frac resid_nnz_frac source lambda placement d_rule k_windows sumU T meanR R_p90 R_max write_runs_aic write_runs_resid sec status note start_source'.split()
def collect():
 out=BASE/'work/t22-collected';out.mkdir(exist_ok=True);data={};guards=[];neworders=[];reuse=json.loads((BASE/'logs/reused-orders.json').read_text());meta={x['matrix']:x for x in json.loads((BASE/'logs/matrices-and-taus.json').read_text())};matrixnames=[x for x in meta if x not in ['reddit','ogbn-products']]
 def identity(r):return (r['matrix'],r['diag'],r['member'],r['W'],r['tau'],r['source'],str(r.get('lambda','')),r['placement'],r['d_rule'],r.get('start_source','keep'))
 for root in ['t22-evaluations','t22-new-evaluations']:
  for p in (BASE/'work'/root).glob('*/results.json'):
   if not (p.parent/'status.json').exists():continue
   rec=record_for(p.parent) if root=='t22-new-evaluations' else json.loads((BASE/'work/t22-base-catalog'/(p.parent.name+'.json')).read_text())
   for r in json.loads(p.read_text()):
    r['member']=canon(t22_start(rec) if root=='t22-new-evaluations' else rec['member']);r['W']=int(r['W']);r.setdefault('start_source',rec.get('start_source','keep'))
    if r['W']!=16 and r['placement']=='gap':continue
    key=identity(r)
    if key in data:assert all(data[key].get(k)==r.get(k) for k in ['T','sumU','meanR','status']),key
    else:data[key]=r
   g=p.parent/'guards.json'
   if g.exists():
    for r in json.loads(g.read_text()):r['member']=canon(t22_start(rec) if root=='t22-new-evaluations' else rec['member']);guards.append(r)
 for p in (BASE/'work/t22-layout-repairs').glob('*/replacement-row.json'):
  r=json.loads(p.read_text());source=json.loads((p.parent/'source.json').read_text());rec=source['record'];isnew='t22-new-evaluations' in source['original_results'];r['member']=canon(t22_start(rec) if isnew else rec['member']);r.setdefault('start_source',rec.get('start_source','keep'));key=identity(r)
  if r['status']=='OK':assert key in data;data[key]=r
 for folder in ['order-jobs','extra-order-jobs']:
  for p in (BASE/'work'/folder).glob('*.record.json'):
   r=json.loads(p.read_text())
   if r.get('status')=='OK' and (r.get('tau') is not None or r.get('kind')=='lsfull'):neworders.append(dict(matrix=r['matrix'],member=r['member'],W=int(r.get('W',16)),tau=r.get('tau'),lam=r.get('lambda'),seed=0,kind=r['kind'],start_source=r.get('start_source','keep'),path=r['path'],sha256=r['sha256'],record=str(p),permutation_universe='kept original rows K' if r['kind']=='rerun' else 'all original rows'))
 pls=[]
 old_proof=BASE/'logs/reused-pls-invariants.json'
 if old_proof.exists():
  for r in json.loads(old_proof.read_text())['checks']:pls.append(dict(r,W=16,start_source='keep',status='OK',sec=r['T21_order_sec'],note='verified T21 output reused; U/G freshly recomputed',reused=True))
 for r in neworders:
  if r['kind']!='ls':continue
  rec=json.loads(Path(r['record']).read_text());d=rec.get('diagnostics',{});fresh=d.get('independent_full_recompute',{});pls.append(dict(matrix=r['matrix'],member=r['member'],W=r['W'],tau=r['tau'],lam=r['lam'],seed=0,start_source=r['start_source'],sweeps_done=d.get('sweeps_done'),accepted_swaps=d.get('accepted_swaps'),tracked_sumU=d.get('tracked_sumU'),tracked_sumGamma=d.get('tracked_sumGamma'),fresh_sumU=fresh.get('sumU'),fresh_sumGamma=fresh.get('sumGamma'),incremental_invariant_passed=d.get('incremental_invariant_passed'),sec=rec['seconds'],status='OK',order_path=r['path'],sha256=r['sha256'],reused=False))
 base9=['B0','rsh-α0','rabbit-pilot','neutron-pilot','C9-Gorder','C9-S','C10-BP','B-RCM-ref','SlashBurn'];cases=[]
 for matrix in matrixnames:
  members=base9+(['LS-full(C9-Gorder)','LS-full(rsh-α0)'] if matrix in ['cora','ogbn-arxiv','wiki-RfA'] else [])
  for member in members:
   for t in meta[matrix]['taus']:cases.append((matrix,member,16,t['tau']))
 for matrix in ['cora','ogbn-arxiv']:
  for W in [32,64]:
   for member in ['B0','rsh-α0','C9-Gorder','C10-BP']:
    for t in meta[matrix]['taus']:cases.append((matrix,member,W,t['tau']))
 derived=BASE/'work/t22-derived/four_numbers.json';fours=json.loads(derived.read_text()) if derived.exists() else [];states=[]
 for matrix,member,W,tau in cases:
  rows=[r for r in data.values() if (r['matrix'],r['member'],r['W'],r['tau'])==(matrix,member,W,tau)];counts={src:sum(r['source']==src for r in rows) for src in ['keep','rerun','pls-0','pls-1']};keep_expected=16 if W==16 else 6;rerun_expected=0 if member.startswith('LS-full') else 6 if W==16 else 4;pls_expected=0
  if W==16 and member in base9[:7]:pls_expected=4 if member in ['B0','rabbit-pilot','neutron-pilot'] else 16 if member=='C10-BP' else 8
  bad=[r['note'] for r in rows if r['status']!='OK'];missing=[]
  for label,actual,expected in [('keep',counts['keep'],keep_expected),('rerun',counts['rerun'],rerun_expected),('P-LS',counts['pls-0']+counts['pls-1'],pls_expected)]:
   if actual!=expected:missing.append(f'{label} rows {actual}/{expected}')
  four=[f for f in fours if (f['matrix'],f['member'],f['W'],f['tau'])==(matrix,member,W,tau)]
  if len(four)!=2:missing.append('four numbers unavailable')
  states.append(dict(matrix=matrix,member=member,W=W,tau=tau,status='INCOMPLETE' if bad or missing else 'OK',reason='; '.join(sorted(set(bad+missing))),keep_rows=counts['keep'],rerun_rows=counts['rerun'],pls_rows=counts['pls-0']+counts['pls-1'],expected_keep_rows=keep_expected,expected_rerun_rows=rerun_expected,expected_pls_rows=pls_expected))
 dumpcsv(out/'results.csv',list(data.values()),FIELDS);dumpcsv(out/'pls.csv',pls);dumpcsv(out/'status.csv',states);dumpcsv(out/'guard-counts.csv',guards);(out/'new-orders.json').write_text(json.dumps(neworders,indent=2));coverage=dict(expected_cases=len(cases),actual_cases=len(states),OK=sum(s['status']=='OK' for s in states),INCOMPLETE=sum(s['status']=='INCOMPLETE' for s in states),result_rows=len(data),expected_result_rows=4012,pls_records=len(pls),expected_pls_records=182,derived_present=derived.exists());(out/'coverage.json').write_text(json.dumps(coverage,indent=2));print(json.dumps(coverage),flush=True)
if __name__=='__main__':collect()
