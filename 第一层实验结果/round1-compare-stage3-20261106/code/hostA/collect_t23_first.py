import csv,hashlib,json,math
from pathlib import Path
from native import BASE
from naming import t23_name
from evaluate_t23 import read_order
MATRICES=['cora','ogbn-arxiv','wiki-RfA','dawson5','olafu','pattern1','human_gene1']
P0=['C9-Gorder','C9-S','C10-BP','C2-LSH','C3-W1','C3-W4','C4-U','C4-T','C7-I','C1-J','C1-H','C5','C5-U','C8-METIS']
PRIMARY=['B0','B1','B-RCM-ref','rabbit-pilot','neutron-pilot']+P0
FIELDS='matrix category diag member member_params seed W tau tau_rule resid_frac placement d_rule source k_windows sumU meanU T T_ratio_B0 sumGamma meanGamma sumR meanR R_p50 R_p90 R_max sumR_minus_Gamma order_sec d_sec post_sec peak_mem_mb status note'.split()
def category(m):return 'GNN 图' if m in ['cora','ogbn-arxiv','reddit','ogbn-products'] else '真实网络' if m=='wiki-RfA' else '有限元带状' if m in ['dawson5','olafu'] else '合成幂律' if m=='mycielskian15' else '长行'
def dumpcsv(p,rows,fields=None):
 fields=fields or list(dict.fromkeys(k for r in rows for k in r))
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows({k:json.dumps(v,ensure_ascii=False,separators=(',',':')) if isinstance(v,(list,dict)) else v for k,v in r.items()} for r in rows)
def collect():
 out=BASE/'work/t23-first-collected';out.mkdir(exist_ok=True);meta={r['matrix']:r for r in json.loads((BASE/'logs/matrices-and-taus.json').read_text())};reuse=json.loads((BASE/'logs/reused-orders.json').read_text());own={};post={};records=[];neworders=[];duplicates=[]
 for p in sorted((BASE/'work/t23-evaluations').glob('*/rows.json')):
  if not (p.parent/'status.json').exists():continue
  for r in json.loads(p.read_text()):
   if r['matrix'] not in MATRICES:continue
   r['member']=t23_name(r['member']);r['seed']=int(r.get('seed') or 0)
   if r['member'] not in PRIMARY:continue
   key=(r['matrix'],r['member'],int(r['W']),r['seed'],r['diag'],str(r['tau']),r['placement'],r['d_rule'])
   if key in own:assert all(own[key].get(k)==r.get(k) for k in ['sumU','T','sumR','sumGamma','status']),key
   else:own[key]=r
 for p in sorted((BASE/'work/post-e').glob('*/record.json')):
  rec=json.loads(p.read_text());name=t23_name(rec.get('member',rec.get('method','')))
  if name not in P0+['B0','B1'] or rec['matrix'] not in MATRICES:continue
  key=(rec['matrix'],name,int(rec['tau']));rowsfile=p.parent/'rows.json';rows=json.loads(rowsfile.read_text()) if rowsfile.exists() else []
  if rec.get('status') not in ['OK','INCOMPLETE']:continue
  old=None
  if name in ['B1','C9-Gorder']:
   alias='rsh-α0' if name=='B1' else name;old=next((x for x in reuse if x['task']=='T23' and x['use']=='post-E-reuse' and x['matrix']==rec['matrix'] and f'start={alias},' in x['params'] and f'tau={rec["tau"]},' in x['params']),None)
  if old and rec.get('order_path'):
   assert read_order(rec['order_path'])==read_order(old['runtime_path']),('T21 reused P-LS mismatch',key);duplicates.append(dict(case=key,selected_primary_reuse=old['runtime_path'],sha256=old['sha256'],runtime_validation=rec.get('order_path'),identical=True))
  elif rec.get('order_path') and not rec.get('reuse'):
   neworders.append(dict(matrix=rec['matrix'],member=name,W=16,tau=rec['tau'],seed=0,source='post-E',path=rec['order_path'],sha256=rec.get('sha256'),record=str(p)))
  if len(rows)!=4:
   have={(r.get('diag'),r.get('d_rule')) for r in rows}
   for diag in ['A0','A1']:
    for dr in ['own','D-greedy']:
     if (diag,dr) not in have:rows.append(dict(matrix=rec['matrix'],member=name,W=16,tau=rec['tau'],diag=diag,placement='tail-co',d_rule=dr,source='post-E',seed=0,status='INCOMPLETE',note=rec.get('error','post-E evaluation unavailable')))
  for r in rows:
   r['member']=name
   if old:r['post_sec']=0;r['note']=r.get('note','')+'; P-LS output reused from verified T21 order'
  if key in post:assert all(a.get('T')==b.get('T') and a.get('sumR')==b.get('sumR') for a,b in zip(post[key],rows)),key
  else:post[key]=rows
  records.append(rec)
 for folder in ['generated','external','bp-variance-orders']:
  for p in (BASE/'work'/folder).glob('*.record.json'):
   r=json.loads(p.read_text());name=t23_name(r.get('method',r.get('member','')))
   if r.get('status')=='OK' and r['matrix'] in MATRICES and int(r.get('W',16))==16 and name in P0:neworders.append(dict(matrix=r['matrix'],member=name,W=16,seed=int(r.get('seed') or 0),source='own',path=r['path'],sha256=r['sha256'],record=str(p)))
 baseline={(r['matrix'],r['diag'],r['W'],str(r['tau']),r['placement'],r['d_rule']):r for r in own.values() if r['member']=='B0' and r['seed']==0};t21=list(csv.DictReader(open(BASE/'inputs/t21/results.csv')));rows=list(own.values())+[r for group in post.values() for r in group]
 for r in rows:
  m=meta[r['matrix']];r['category']=category(r['matrix']);r['W']=int(r.get('W',16));r['seed']=int(r.get('seed') or 0);r.setdefault('tau_rule','none' if str(r['tau'])=='none' else next(t['tau_rule'] for t in m['taus'] if t['tau']==int(r['tau'])));r.setdefault('resid_frac',0 if str(r['tau'])=='none' else next(t['resid_frac'] for t in m['taus'] if t['tau']==int(r['tau'])));r.setdefault('note','')
  if r.get('k_windows'):
   for field,num in [('meanU','sumU'),('meanGamma','sumGamma')]:
    if num in r:r[field]=r[num]/r['k_windows']
  if 'sumR' in r and 'sumGamma' in r:r['sumR_minus_Gamma']=r['sumR']-r['sumGamma']
  b=baseline.get((r['matrix'],r['diag'],r['W'],str(r['tau']),r['placement'],r['d_rule']))
  if b and b.get('T') and 'T' in r:r['T_ratio_B0']=r['T']/b['T']
  if r.get('order_sec','')=='':
   oldname='rsh-α0' if r['member']=='B1' else r['member'];old=next((x for x in t21 if x['matrix']==r['matrix'] and x['member']==oldname and x['W']=='16' and x['tau']=='none' and x['diag']=='A0' and x['d_rule']=='own'),None)
   if old:r['order_sec']=old['order_sec'];r['note']+='; order cost inherited from T21'
  if r['member'] in ['rabbit-pilot','neutron-pilot']:r['note']+='; historical pilot reference, excluded from ranking'
  if r['member']=='B-RCM-ref':r['note']+='; reference, ranking only for finite-element matrices'
  if r['matrix']=='wiki-RfA':r['note']+='; reconstructed numbering, B0 and P11 sumR/sumU reference-only'
  r.setdefault('member_params','see manifest fixed parameters')
 expected_own={(m,c,16,0) for m in MATRICES for c in PRIMARY}|{(m,c,16,s) for m in MATRICES[:2] for c in ['C1-J','C1-H','C2-LSH','C5','C5-U','C10-BP'] for s in [1,2]};count={}
 for r in own.values():k=(r['matrix'],r['member'],r['W'],r['seed']);count[k]=count.get(k,0)+1
 missing_own=[dict(case=k,rows=count.get(k,0),expected_rows=20) for k in sorted(expected_own) if count.get(k,0)!=20];expected_post={(m,c,t['tau']) for m in MATRICES for c in P0+['B0','B1'] for t in meta[m]['taus']};missing_post=[k for k in sorted(expected_post) if k not in post];diags={};groups=[]
 for p in sorted((BASE/'work/t23-diagnostics').glob('*/diag.json')):
  r=json.loads(p.read_text());r['member']=t23_name(r['member']);k=(r['matrix'],r['member'])
  if k not in diags:
   diags[k]=r;g=p.parent/'groups.json'
   if g.exists():groups.extend(json.loads(g.read_text()))
 missing_diag=[k for k in sorted((m,c) for m in MATRICES for c in PRIMARY) if k not in diags];proofs=[]
 for m in MATRICES:
  p=BASE/'work/independent-all'/m/'status.json';proofs.append(dict(matrix=m,passed=p.exists() and json.loads(p.read_text())['status']=='OK'))
 gates=['reference-gates.json','candidate-port-gate.json','layout-port-gate.json','rect-port-gate.json','ls-port-gate.json','capacity-repair-gate.json','external-repeated-cora-gate.json','rabbit-reproducibility-gate.json','rabbit-local-gate.json'];missing_gates=[g for g in gates if not (BASE/'logs'/g).exists() or not json.loads((BASE/'logs'/g).read_text()).get('passed')];complete=not missing_own and not missing_post and not missing_diag and all(x['passed'] for x in proofs) and not missing_gates
 coverage=dict(complete=complete,expected_own_cases=len(expected_own),own_cases_complete=sum(count.get(k)==20 for k in expected_own),expected_post_cases=len(expected_post),post_cases_complete=len(expected_post.intersection(post)),missing_own=missing_own,missing_post=missing_post,missing_diag=missing_diag,independent_proofs=proofs,missing_gates=missing_gates)
 post_table=[];ug_path=BASE/'logs/reused-pls-invariants.json';ug_checks=json.loads(ug_path.read_text())['checks'] if ug_path.exists() else []
 for rec in records:
  name=t23_name(rec.get('member',rec.get('method','')));d=rec.get('diagnostics',{}).copy();key=(rec['matrix'],name,int(rec['tau']));primary_rows=post.get(key,[]);primary_reused=any(x['case']==key for x in duplicates);ug=next((x for x in ug_checks if x['matrix']==rec['matrix'] and x['member']==('rsh-α0' if name=='B1' else name) and x['tau']==rec['tau'] and x['lam']==0),None)
  if primary_reused and ug:
   if d.get('tracked_sumU') is not None:assert d['tracked_sumU']==ug['sumU'] and d['tracked_sumGamma']==ug['sumGamma']
   d.update(tracked_sumU=ug['sumU'],tracked_sumGamma=ug['sumGamma'],incremental_invariant_passed=True)
  post_table.append(dict(matrix=rec['matrix'],member=name,W=16,tau=rec['tau'],seed=0,lam=0,sweeps_done=d.get('sweeps_done'),accepted_swaps=d.get('accepted_swaps'),tracked_sumU=d.get('tracked_sumU'),tracked_sumGamma=d.get('tracked_sumGamma'),incremental_invariant_passed=d.get('incremental_invariant_passed','inherited T21 reuse' if rec.get('reuse') else ''),post_seconds=primary_rows[0].get('post_sec') if primary_rows else '',total_case_wall_seconds=rec.get('seconds'),status=rec['status'],order_path=rec.get('order_path'),note='primary T21 provenance selected by verified-T21-postE-reuse.json where applicable; total-case wall time includes layout evaluation'))
 dumpcsv(out/'results.csv',rows,FIELDS);dumpcsv(out/'diag.csv',list(diags.values()));dumpcsv(out/'groups.csv',groups);dumpcsv(out/'post-E.csv',post_table);(out/'coverage.json').write_text(json.dumps(coverage,indent=2));(out/'new-orders.json').write_text(json.dumps(neworders,indent=2));(out/'verified-T21-postE-reuse.json').write_text(json.dumps(duplicates,indent=2));(out/'post-records.json').write_text(json.dumps(records,indent=1));print(json.dumps(coverage),flush=True)
if __name__=='__main__':collect()
