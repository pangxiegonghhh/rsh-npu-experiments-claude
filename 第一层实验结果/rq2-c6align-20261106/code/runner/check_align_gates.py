from __future__ import annotations
import csv,json,re
from pathlib import Path
from align_context import BASE,OLD,PARENT,OUT,PROTOCOL,dump,sha
METRICS=('sumU','T','sumGamma','sumR','R_p50','R_p90','R_max')
def condition(row:dict)->tuple:
    return tuple(str(row[k])for k in ('diag','W','tau','placement','d_rule'))
def gate2()->dict:
    root=OUT/'checks/gate2-cora-runs';cases=[]
    with (PARENT/'joint.csv').open(newline='')as f:oldrows=list(csv.DictReader(f))
    for mnc in (0,4):
        member='C6'if mnc==0 else'C6-M';key=f'c6__cora__{member}__W16__{mnc}'
        old=json.loads((PARENT/'checks'/(key+'-bisections.json')).read_text());new=json.loads((root/'checks'/(key+'-bisections.json')).read_text())
        assert len(old['calls'])==len(new['calls'])==169,key
        fields=('hypergraph_sha256','labels_sha256','actual_sizes')
        diffs=[i for i,(x,y)in enumerate(zip(old['calls'],new['calls']))if any(x[k]!=y[k]for k in fields)]
        task=json.loads((root/'tasks'/(key+'.json')).read_text());params=json.loads(task['rows'][0]['member_params'])
        assert not diffs and params['alignment_repair']['calls_repaired']==0,(key,diffs)
        baseline={condition(r):r for r in oldrows if r['matrix']=='cora'and r['member']==member and r['mnc']==str(mnc)}
        assert len(baseline)==16 and len(task['rows'])==16
        checked_orders=set()
        for row in task['rows']:
            reference=baseline[condition(row)]
            assert all(int(reference[k])==row[k]for k in METRICS),(key,condition(row))
            newname=re.search(r'order=([^;]+)',row['note'])[1];oldname=re.search(r'order=([^;]+)',reference['note'])[1]
            a=json.loads((root/newname).read_text())['row_perm'];b=json.loads((PARENT/oldname).read_text())['row_perm'];assert a==b,(key,newname)
            checked_orders.add(newname)
        cases.append({'case':key,'passed':True,'calls_equal':169,'calls_repaired':0,'metric_conditions_equal':16,
                      'fields_compared':list(METRICS),'order_vectors_equal':len(checked_orders)})
    result={'passed':True,'cases':cases};dump(OUT/'checks/gate2-cora-noop.json',result);return result
def gate3()->dict:
    expected=json.loads((PROTOCOL/'expected-repairs.json').read_text());cases=[]
    for name,exp in sorted(expected.items()):
        key=name.removesuffix('-bisections');oldpath=PARENT/'checks'/(name+'.json');newpath=OUT/'checks'/(name+'.json')
        old=json.loads(oldpath.read_text());new=json.loads(newpath.read_text())if newpath.exists()else{'calls':[]}
        first=None;reason='';calls=new['calls'];last_index=len(old['calls'])-1
        for i,ref in enumerate(old['calls'][:-1]):
            if i>=len(calls)or any(ref[k]!=calls[i][k]for k in ('hypergraph_sha256','labels_sha256')):
                first=i;reason='prefix hypergraph/labels differ or call unavailable';break
        hit=calls[last_index]if len(calls)>last_index else{};repair=hit.get('align_repair',{})
        actual={'raw_labels_sha256':hit.get('labels_sha256'),'moved_global_vertices':[m['global_vertex']for m in repair.get('moves',[])],
                'weighted_cut_after':repair.get('weighted_cut_after'),'final_labels_sha256':repair.get('final_labels_sha256')}
        if first is None and (actual['raw_labels_sha256']!=old['calls'][-1]['labels_sha256']or any(actual[k]!=exp[k]for k in ('moved_global_vertices','weighted_cut_after','final_labels_sha256'))):
            first=last_index;reason='old failure layer raw labels or specified repair differs'
        cases.append({'case':key,'reproduced':first is None,'prefix_calls_expected':last_index,'first_different_call_index_zero_based':first,
                      'first_different_call_number_one_based':None if first is None else first+1,'reason':reason,'old_failure_part':exp['part_id'],
                      'actual_at_old_failure':actual,'old_trace_sha256':sha(oldpath),'new_trace_sha256':sha(newpath)if newpath.exists()else None})
    result={'passed':all(c['reproduced']for c in cases),'nonstopping_gate':True,'cases':cases};dump(OUT/'checks/gate3-pattern1-prefix.json',result);return result
