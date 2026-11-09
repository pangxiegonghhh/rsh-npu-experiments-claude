import json,sys
from pathlib import Path
from native import BASE
from collect_t23_first import MATRICES,P0
from naming import t23_name
P1=['C3-A','C3-W4-noP','C3-W4-R','C3-A-R','C4-U-R','C4-T-R','C7-I-R','C5-CN','C5-U-CN']
P2=['C6-HP','C6-RB (T21 口径)','C6-M mnc=1 (T21 口径)','C6-M mnc=4 (T21 口径)','C6-M mnc=16 (T21 口径)']
def catalog():
 reuse=json.loads((BASE/'logs/reused-orders.json').read_text());cases=[]
 def add(m,c,W=16,s=0,scope='P1/P2',**kw):cases.append(dict(matrix=m,method=c,member=c,W=W,seed=s,scope=scope,case_id=f'stage3-{m}__{c}__W{W}__seed{s}',**kw))
 for m in MATRICES:
  for c in P1+P2:add(m,c)
 for m in MATRICES[:2]:
  for c in ['C5-CN','C5-U-CN']:
   for s in [1,2]:add(m,c,s=s,scope='P1 variance')
 for m in MATRICES[:4]:
  for W in [32,64,128]:
   for c in ['B0','B1','B-RCM-ref']+P0:add(m,c,W=W,scope='W sensitivity',main_tau_only=True)
 for m in ['reddit','ogbn-products','mycielskian15']:
  for c in ['B0','B1','B-RCM-ref','rabbit-pilot','neutron-pilot']+P0+P1+P2:
   add(m,c,scope='second batch',data_missing=m=='mycielskian15')
 # Each planned condition remains in the catalog even if its dependency is unavailable.
 for r in cases:
  m,c,W,s=r['matrix'],r['method'],r['W'],r['seed'];old=None
  if m in MATRICES:
   if c.startswith('C6-') and c!='C6-HP':
    old=next((x for x in reuse if x['task']=='T23' and x['use']=='base-order' and x['matrix']==m and t23_name(x['t23_member'])==c),None)
    if old is None:
     choices=[x for x in reuse if x['task']=='T23' and x['use']=='base-order' and x['matrix']==m and x['t23_member'].startswith('C6')];r['lookup_options']=[x['t23_member'] for x in choices]
   elif W!=16:
    old=next((x for x in reuse if x['task']=='T23' and x['use']=='W-sensitivity' and x['matrix']==m and int(x['W'])==W and t23_name(x['t23_member'])==c),None)
    if old is None and c in ['B0','B1','B-RCM-ref']:
     old=next(x for x in reuse if x['task']=='T23' and x['use']=='base-order' and x['matrix']==m and t23_name(x['t23_member'])==c)
    if old is None and c in ['C1-J','C1-H']:
     p=BASE/'work/external'/f'{m}__{c}__W16__seed0.record.json';old=json.loads(p.read_text());old['reuse_record']=str(p)
   elif c=='C3-A' and m not in ['ogbn-arxiv']:
    p=BASE/'work/generated'/f'{m}__C3-W4__W16__seed0.record.json';old=json.loads(p.read_text());old.update(alias_of='C3-W4',alias_nonindependent=True,reuse_record=str(p))
  if old:r.update(reuse=old)
 assert len({r['case_id'] for r in cases})==len(cases)
 dest=BASE/'work/stage3-catalog';dest.mkdir(exist_ok=True)
 for r in cases:(dest/(r['case_id']+'.json')).write_text(json.dumps(r,ensure_ascii=False,indent=2))
 (BASE/'logs/stage3-planned-cases.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2));return cases
if __name__=='__main__':
 cases=catalog();print('STAGE3_PLANNED',len(cases));print('UNRESOLVED_C6',[(r['matrix'],r['method'],r.get('lookup_options')) for r in cases if r['matrix'] in MATRICES and r['method'].startswith('C6-') and r['method']!='C6-HP' and not r.get('reuse')])
