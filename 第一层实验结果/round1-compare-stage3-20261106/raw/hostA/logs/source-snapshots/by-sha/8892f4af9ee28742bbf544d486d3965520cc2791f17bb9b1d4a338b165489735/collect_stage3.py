import csv,hashlib,json
from pathlib import Path
from native import BASE
from collect_t23_first import FIELDS,category,dumpcsv
from collect_t23_first import P0
from group_metadata import complete_stats
import numpy as np

def collect():
 planned=json.loads((BASE/'logs/stage3-planned-cases.json').read_text());meta={r['matrix']:r for r in json.loads((BASE/'logs/matrices-and-taus.json').read_text())};out=BASE/'work/stage3-collected';out.mkdir(exist_ok=True);rows=[];states=[];orders=[];reuse=[];diags=[];groups=[];guards=[];post=[]
 first=list(csv.DictReader(open(BASE/'delivery/第一层实验结果/round1-compare-20261106/results.csv')))
 for case in planned:
  key=case['case_id'];p=BASE/'work/stage3-cases'/key/'record.json';rec=json.loads(p.read_text()) if p.exists() else dict(case,status='INCOMPLETE',error='controller case not yet attempted');matrix,member,W=case['matrix'],case['method'],case['W'];folder=BASE/'work/stage3-evaluations'/key;rp=folder/'rows.json';actual=json.loads(rp.read_text()) if rp.exists() else [];expected=12 if case.get('main_tau_only') else 20
  reason=[]
  if rec['status']!='OK':reason.append(rec.get('error','generation incomplete'))
  command=rec.get('generation_command',{})
  if command.get('exitcode') not in [None,0]:reason.append(command.get('reason','generator exit code '+str(command['exitcode'])))
  guard=command.get('cpu_slot',{}).get('memory_guard_path')
  if guard and Path(guard).exists():reason.append('resident-memory guard: '+str(json.loads(Path(guard).read_text())['peak_rss_bytes'])+' bytes > 8GiB')
  for root in ['stage3-generated','external']:
   trigger=BASE/'work'/root/f'{matrix}__{member}__W{W}__seed{case["seed"]}.cost-budget-trigger.json'
   if trigger.exists():reason.append(json.loads(trigger.read_text())['reason'])
  phase=BASE/'work/stage3-generated'/f'{matrix}__{member}__W{W}__seed{case["seed"]}.phase.json'
  if rec['status']!='OK' and phase.exists():reason.append('last completed preparation phase: '+json.loads(phase.read_text()).get('phase','unknown'))
  for phase in ['eval','diag']:
   cp=BASE/'logs'/('stage3-'+phase+'-'+key+'.command.json')
   if cp.exists():
    cr=json.loads(cp.read_text())
    if cr.get('exitcode') not in [None,0]:reason.append(phase+': '+cr.get('reason','exit code '+str(cr['exitcode'])))
   failure=rec.get('evaluation_status' if phase=='eval' else 'diagnostic_status',{})
   if failure.get('error'):reason.append(phase+': '+failure['error'])
  if rec['status']=='OK' and len(actual)!=expected:reason.append(f'evaluation rows {len(actual)}/{expected}')
  reason.extend(r.get('note','evaluation failure') for r in actual if r.get('status')!='OK')
  for r in actual:r.update(member=member,seed=case['seed'],scope=case['scope']);rows.append(r)
  taus=[] if matrix not in meta else [t for t in meta[matrix]['taus'] if not case.get('main_tau_only') or t==meta[matrix]['taus'][-1]];present={(r['diag'],str(r['tau']),r['placement'],r['d_rule']) for r in actual}
  for diag in ['A0','A1']:
   for tau,placement,dr in [('none','none',d) for d in ['own','D-greedy']]+[(t['tau'],pl,d) for t in taus for pl in ['tail-co','tail'] for d in ['own','D-greedy']]:
    if (diag,str(tau),placement,dr) not in present:rows.append(dict(matrix=matrix,member=member,W=W,seed=case['seed'],diag=diag,tau=tau,placement=placement,d_rule=dr,source='own',scope=case['scope'],status=rec['status'] if rec['status'] in ['INCOMPLETE','SKIPPED'] else 'INCOMPLETE',note='; '.join(reason)))
  if rec.get('path') and rec.get('status')=='OK':
   order=dict(matrix=matrix,member=member,W=W,seed=case['seed'],source='own',path=rec['path'],sha256=rec['sha256'],record=str(p),scope=case['scope'],alias_of=rec.get('alias_of'),alias_nonindependent=rec.get('alias_nonindependent',False))
   if rec.get('reused'):reuse.append(dict(order,origin=case.get('reuse'),alias_of=case.get('reuse',{}).get('alias_of'),alias_nonindependent=case.get('reuse',{}).get('alias_nonindependent',False)))
   else:orders.append(order)
  if W==16 and case['seed']==0 and rec['status']=='OK':
   dp=BASE/'work/stage3-diagnostics'/key/'diag.json';gp=dp.parent/'groups.json'
   if dp.exists():
    d=json.loads(dp.read_text());d['member']=member;extras=rec.get('diagnostics',{});nonempty=int(np.count_nonzero(np.load(BASE/'work/matrices'/matrix/'degrees.npy',mmap_mode='r')));d.update(complete_stats(member,extras,meta[matrix]['n'],nonempty,W,frozen_T21=bool(rec.get('reused') and '(T21 口径)' in member)));diags.append(d)
   else:reason.append('W16 A0 diagnostics incomplete')
   if gp.exists():
    for g in json.loads(gp.read_text()):g['member']=member;groups.append(g)
  if (folder/'guards.json').exists():
   for g in json.loads((folder/'guards.json').read_text()):g.update(member=member,seed=case['seed']);guards.append(g)
  else:
   for r in actual:
    if 'co_chain_guard_windows_skipped' in r:
     guards.append(dict(matrix=matrix,member=member,W=W,tau=r['tau'],diag=int(r['diag'][-1]),source=r.get('source','own'),placement=r['placement'],d_rule=r['d_rule'],seed=case['seed'],co_chain_guard_windows_skipped=r['co_chain_guard_windows_skipped'],partial_evaluation_recovery=True))
  if case['scope']=='second batch' and member in P0+['B0','B1'] and not rec.get('post_cases'):
   for t in taus:
    for diag in ['A0','A1']:
     for dr in ['own','D-greedy']:rows.append(dict(matrix=matrix,member=member,W=W,seed=0,diag=diag,tau=t['tau'],placement='tail-co',d_rule=dr,source='post-E',scope=case['scope'],status='SKIPPED' if rec['status']=='SKIPPED' else 'INCOMPLETE',note='post-E dependency unavailable: '+rec.get('error','order unavailable')))
  for pp in rec.get('post_cases',[]):
   pp=Path(pp)
   supplemental=BASE/'work/stage3-partial-post'/pp.parent.name/'record.json'
   if supplemental.exists() and json.loads(supplemental.read_text()).get('order_path'):pp=supplemental
   if pp.exists():
    pr=json.loads(pp.read_text());post.append(pr)
    if (pp.parent/'rows.json').exists():rows.extend(json.loads((pp.parent/'rows.json').read_text()))
    else:
     for diag in ['A0','A1']:
      for dr in ['own','D-greedy']:rows.append(dict(matrix=matrix,member=member,W=W,seed=0,diag=diag,tau=pr['tau'],placement='tail-co',d_rule=dr,source='post-E',scope=case['scope'],status='INCOMPLETE',note=pr.get('error','post-E incomplete')))
    if pr.get('order_path') and not pr.get('reuse'):orders.append(dict(matrix=matrix,member=member,W=W,seed=0,tau=pr['tau'],source='post-E',path=pr['order_path'],sha256=pr['sha256'],record=str(pp)))
    if pr.get('status')!='OK':reason.append('post-E: '+pr.get('error','incomplete'))
   else:
    catalog=BASE/'work/stage3-post-catalog'/(pp.parent.name+'.json');pending=json.loads(catalog.read_text());tau=pending['tau'];cp=BASE/'logs'/('stage3-post-'+pp.parent.name+'.command.json');command=json.loads(cp.read_text()) if cp.exists() else {};error=command.get('reason','post-E controller ended before final record')
    if command.get('exitcode') not in [None,0]:error+='; exit code '+str(command['exitcode'])
    reason.append('post-E: '+error);post.append(dict(matrix=matrix,member=member,W=W,tau=tau,status='INCOMPLETE',error=error,raw_record_missing=True))
    for diag in ['A0','A1']:
     for dr in ['own','D-greedy']:rows.append(dict(matrix=matrix,member=member,W=W,seed=0,diag=diag,tau=tau,placement='tail-co',d_rule=dr,source='post-E',scope=case['scope'],status='INCOMPLETE',note=error))
  states.append(dict(matrix=matrix,member=member,W=W,seed=case['seed'],scope=case['scope'],status='SKIPPED' if rec['status']=='SKIPPED' else 'INCOMPLETE' if reason else 'OK',reason='; '.join(sorted(set(reason))),result_rows=len(actual),expected_rows=expected,attempt_record=str(p),attempted=p.exists()))
 for r in rows:
  if r.get('source')=='post-E' and 'co_chain_guard_windows_skipped' in r:
   guards.append(dict(matrix=r['matrix'],member=r['member'],W=r['W'],seed=r.get('seed',0),tau=r['tau'],diag=int(r['diag'][-1]),source='post-E',placement=r['placement'],d_rule=r['d_rule'],co_chain_guard_windows_skipped=r['co_chain_guard_windows_skipped'],guard_count_source='actual saved post-E evaluation row',original_status=r['status']))
 recovered=BASE/'work/stage3-guard-recovery.json'
 if recovered.exists():
  proof=json.loads(recovered.read_text());assert proof['passed']
  def guard_key(r):return tuple(str(r.get(k,'')) for k in ['matrix','member','W','seed','tau','diag','source','placement','d_rule'])
  existing={guard_key(g) for g in guards}
  for g in proof['recovered_actual_guard_counts']:
   if guard_key(g) not in existing:guards.append(g);existing.add(guard_key(g))
 base={}
 for r in first+rows:
  if r['member']=='B0' and str(r.get('seed',0))=='0' and r['source']=='own' and r.get('status')=='OK':base[(r['matrix'],r['diag'],int(r['W']),str(r['tau']),r['placement'],r['d_rule'])]=r
 for r in rows:
  r.setdefault('source','own');r['category']=category(r['matrix']);r.setdefault('member_params','fixed dispatch parameters; see manifest');r.setdefault('post_sec',0)
  if r['matrix'] in meta:
   t=next((t for t in meta[r['matrix']]['taus'] if str(t['tau'])==str(r['tau'])),None);r.setdefault('tau_rule',t['tau_rule'] if t else 'none');r.setdefault('resid_frac',t['resid_frac'] if t else 0)
  if r.get('k_windows'):
   for target,source in [('meanU','sumU'),('meanGamma','sumGamma')]:r[target]=r[source]/r['k_windows']
  if 'sumR' in r:r['sumR_minus_Gamma']=r['sumR']-r['sumGamma']
  b=base.get((r['matrix'],r['diag'],int(r['W']),str(r['tau']),r['placement'],r['d_rule']))
  if b and b.get('T') and 'T' in r:r['T_ratio_B0']=r['T']/float(b['T'])
  r.setdefault('note','')
  c=r['member'];W=int(r['W']);params=dict(W=W,seed=int(r.get('seed',0)))
  if c.startswith('C3-'):
   n=meta[r['matrix']]['n'] if r['matrix'] in meta else None;params.update(b=(4 if n<50000 else 32 if n<100000 else 128) if n is not None and c.startswith('C3-A') else 1 if c=='C3-W1' else 4,P='off' if c=='C3-W4-noP' else 'on',signature_J_min='1/5')
  elif c=='C2-LSH':params.update(num_perm=128,bands=32,rows_per_band=4,J_min='1/5')
  elif c.startswith('C1-'):params.update(k=16,n_jobs=1,metric='Jaccard' if c=='C1-J' else 'Hamming symmetric-difference count',forest='exact-distance undirected union, Kruskal MSF, deterministic DFS')
  elif c.startswith('C5'):params.update(coarse='A0 undirected row graph' if c.startswith('C5-U') else 'A0 bipartite row/column graph',local='common-neighbor chain' if c.endswith('-CN') else 'anchor Jaccard',Q=8*W,actual_seed=None)
  elif c in ['C9-Gorder','C9-S']:params.update(w=W-1,S_n=c=='C9-Gorder')
  elif c=='C8-METIS':params.update(ufactor=30,recursive=False,capacity_repair='exact specified greedy')
  elif c=='C6-HP':params.update(epsilon=.03,objective='km1',partition='direct k-way',capacity_repair='exact specified greedy')
  elif '(T21 口径)' in c:params.update(epsilon=0,partition='frozen T21 recursive bisection; message weight in member label; alignment repair for pattern1')
  if c.endswith('-R'):params.update(symmetric_row_and_column_renumbering='genuine Rabbit-U coarse; map output back to original IDs')
  r['member_params']=params
  if r['matrix']=='wiki-RfA':r['note']+='; reconstructed numbering, B0/P11 reference-only'
  if '(T21 口径)' in r['member']:r['note']+='; frozen recursive-bisection epsilon0 T21 order, not T20 epsilon.03 capacity repair'
 optional=[dict(matrix=m,member=c,W=16,seed=0,scope='optional unavailable reference',status='SKIPPED',reason='T4/T2 reference dependency unavailable; optional by dispatch, not part of409core cases',result_rows=0,expected_rows=0,attempt_record='',attempted=False) for m in ['reddit','ogbn-products','mycielskian15'] for c in ['B-RSH-ref','B-Neutron-ref']]
 dumpcsv(out/'results.csv',rows,FIELDS+['scope']);dumpcsv(out/'status.csv',states+optional);dumpcsv(out/'diag.csv',diags);dumpcsv(out/'groups.csv',groups);dumpcsv(out/'guard-counts.csv',guards);dumpcsv(out/'post-E.csv',[{k:r.get(k) for k in ['matrix','member','W','tau','status','seconds','error','diagnostics','order_path']} for r in post]);(out/'new-orders.json').write_text(json.dumps(orders,ensure_ascii=False,indent=2));(out/'reused-orders.json').write_text(json.dumps(reuse,ensure_ascii=False,indent=2));coverage=dict(planned_cases=len(planned),attempted=sum(r['attempted'] for r in states),OK=sum(r['status']=='OK' for r in states),INCOMPLETE=sum(r['status']=='INCOMPLETE' for r in states),SKIPPED=sum(r['status']=='SKIPPED' for r in states),optional_reference_skip_cells=len(optional),result_rows=len(rows),post_records=len(post),all_attempted=all(r['attempted'] for r in states));(out/'coverage.json').write_text(json.dumps(coverage,indent=2));print(json.dumps(coverage),flush=True);return coverage
if __name__=='__main__':collect()
