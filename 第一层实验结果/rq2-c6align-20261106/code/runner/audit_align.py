from __future__ import annotations
import json,re
from pathlib import Path
import numpy as np
from align_context import BASE,OUT,PARENT,dump,sha
import independent_audit as independent
def audit(rows:list[dict])->dict:
    parent=json.loads((PARENT/'manifest.json').read_text());meta=next(x for x in parent['matrices']if x['matrix']=='pattern1')
    input_path=Path(meta['input_path']);assert sha(input_path)==meta['input_mtx_sha256']
    A0=independent.matrix(str(input_path));assert A0.nnz==meta['nnz_A0'];deg=np.diff(A0.indptr)
    import scipy.sparse as sp
    A1=A0+sp.eye(A0.shape[0],format='csr',dtype=np.int8);data={};samples=[];D_checks=[]
    for path in (OUT/'orders').glob('*.json'):
        item=json.loads(path.read_text());order=np.asarray(item['row_perm'],dtype=np.int64)
        assert len(order)==A0.shape[0] and np.all(np.bincount(order,minlength=len(order))==1),path
        data[str(path.relative_to(OUT))]=item
    for row in rows:
        if row['status']!='OK':continue
        name=re.search(r'order=([^;]+)',row['note'])[1];actual=independent.metrics(data[name],row,A0 if row['diag']=='A0'else A1,deg)
        assert all(actual[k]==row[k]for k in independent.KEYS),(row,actual)
        k=actual['k_windows']
        for sumkey,meankey in [('sumU','meanU'),('sumGamma','meanGamma'),('sumR','meanR')]:assert row[meankey]==(actual[sumkey]/k if k else 0.)
        tau=None if row['tau']=='none'else int(row['tau']);assert row['resid_frac']==(0 if tau is None else int(np.count_nonzero(deg<=tau))/len(deg))
        samples.append({'member':row['member'],'mnc':json.loads(row['member_params'])['mnc'],'condition':[row[k]for k in ('diag','tau','placement','d_rule')],'order':name,'passed':True})
    def key(row):return (json.loads(row['member_params'])['mnc'],row['diag'],row['tau'],row['placement'],row['d_rule'])
    lookup={key(row):row for row in rows if row['status']=='OK'}
    for row in rows:
        if row['status']!='OK'or row['d_rule']!='D-greedy':continue
        mnc=json.loads(row['member_params'])['mnc'];peer=lookup[(mnc,row['diag'],row['tau'],row['placement'],'own')]
        assert row['sumU']==peer['sumU'] and row['sumGamma']==peer['sumGamma']
        tau=None if row['tau']=='none'else int(row['tau'])
        def split(r):
            name=re.search(r'order=([^;]+)',r['note'])[1];order=data[name]['row_perm'];kept=[v for v in order if tau is None or deg[v]>tau];res=[v for v in order if tau is not None and deg[v]<=tau]
            return [kept[i:i+16]for i in range(0,len(kept),16)],res
        a,ra=split(peer);b,rb=split(row);assert sorted(tuple(sorted(w))for w in a)==sorted(tuple(sorted(w))for w in b)and ra==rb
        if a and len(a[-1])<16:assert set(a[-1])==set(b[-1])
        D_checks.append({'mnc':mnc,'diag':row['diag'],'tau':row['tau'],'passed':True})
    result={'passed':True,'independent_raw_input':str(input_path),'input_sha256':meta['input_mtx_sha256'],'n':A0.shape[0],'nnz_A0':A0.nnz,
            'permutations_checked':len(data),'metric_conditions_checked':len(samples),'metric_samples':samples,'D_checks':D_checks}
    dump(OUT/'checks/independent-metrics.json',result);return result
