"""Independent numpy/scipy raw-input audit; does not import campaign/rq2lib/fast."""
from __future__ import annotations
import json, math, re, sys, time
from pathlib import Path
import numpy as np
import scipy.io as sio
import scipy.sparse as sp

BASE=Path(__file__).resolve().parents[1]
OUT=BASE/'delivery/第一层实验结果/rq2-validate-20261106'
KEYS=['n','k_windows','sumU','T','sumGamma','sumR','R_p50','R_p90','R_max','sumR_minus_Gamma']

def matrix(path: str) -> sp.csr_matrix:
    a=sio.mmread(path).tocoo();valid=(a.row!=a.col)  # Package ten: retain every stored entry, including zeros.
    r=a.row[valid];c=a.col[valid];n=a.shape[0]
    A=sp.csr_matrix((np.ones(2*len(r),dtype=np.int8),(np.r_[r,c],np.r_[c,r])),shape=(n,n))
    A.data[:]=1;A.sort_indices();return A

def metrics(data: dict,row: dict,A: sp.csr_matrix,deg: np.ndarray) -> dict:
    order=np.asarray(data['row_perm'],dtype=np.int64);n=len(order);W=int(row['W']);tau=None if row['tau']=='none' else int(row['tau'])
    kept=order if tau is None else order[deg[order]>tau]
    resid=np.empty(0,dtype=np.int64) if tau is None else order[deg[order]<=tau]
    if 'col_perm' in data:colorder=np.asarray(data['col_perm'],dtype=np.int64)
    else:colorder=order if tau is None or row['placement']=='inplace' else np.r_[kept,resid]
    pos=np.empty(n,dtype=np.int64);pos[colorder]=np.arange(n)
    Us=[];Gs=[];Rs=[]
    for start in range(0,len(kept),W):
        cols=A[kept[start:start+W]].indices
        p=np.unique(pos[cols]);Us.append(len(p));Gs.append(len(np.unique(p//W)));Rs.append(0 if not len(p) else int(1+np.count_nonzero(np.diff(p)!=1)))
    k=len(Us);sr=sorted(Rs)
    return dict(n=n,k_windows=k,sumU=sum(Us),T=sum((x+15)//16 for x in Us),sumGamma=sum(Gs),sumR=sum(Rs),R_p50=sr[min(k-1,int(.5*k))] if k else 0,R_p90=sr[min(k-1,int(.9*k))] if k else 0,R_max=max(Rs,default=0),sumR_minus_Gamma=sum(Rs)-sum(Gs))

if __name__=='__main__':
    started=time.perf_counter();rows=[]
    for p in sorted((OUT/'tasks').glob('*.json')):rows.extend(json.loads(p.read_text())['rows'])
    inputs={d['matrix']:d for d in json.loads((BASE/'logs/input-acquisition.json').read_text()) if d['status']=='OK' and not d.get('protocol_alias_of')}
    summary={'permutations_checked':0,'cases':[],'raw_input_preprocessing':[]}
    for name,entry in inputs.items():
        A0=matrix(entry['mtx']);deg=np.diff(A0.indptr);A1=A0+sp.eye(A0.shape[0],format='csr',dtype=np.int8)
        summary['raw_input_preprocessing'].append({'matrix':name,'n':A0.shape[0],'nnz_A0':A0.nnz,'nnz_A1':A1.nnz,'degree_max':int(deg.max())})
        for path in sorted((OUT/'orders').glob(name+'__*.json')):
            data=json.loads(path.read_text())
            for key in ('row_perm','col_perm'):
                if key not in data:continue
                a=np.asarray(data[key],dtype=np.int64);assert len(a)==A0.shape[0] and a.min()==0 and a.max()==len(a)-1 and np.all(np.bincount(a,minlength=len(a))==1),(path,key)
                summary['permutations_checked']+=1
        # One representative for every diagonal/window/partition/placement/D-rule combination.
        representatives={}
        for row in rows:
            if row['matrix']!=name or row['status']!='OK':continue
            key=tuple(row[x] for x in ('diag','W','tau','placement','d_rule'))
            representatives.setdefault(key,row)
        for row in representatives.values():
            match=re.search(r'order=([^;]+)',row['note']);assert match,row
            path=OUT/match.group(1);data=json.loads(path.read_text());actual=metrics(data,row,A0 if row['diag']=='A0' else A1,deg)
            assert all(actual[k]==row[k] for k in KEYS),(row,actual)
            summary['cases'].append({'matrix':name,'diag':row['diag'],'W':row['W'],'tau':row['tau'],'placement':row['placement'],'rule':row['d_rule'],'member':row['member'],'order':str(path.relative_to(OUT)),'integer_metrics':actual,'passed':True})
        print(name,'independent audit passed',len(representatives),'metric cases',flush=True)
    summary.update(passed=True,elapsed_sec=time.perf_counter()-started)
    (BASE/'logs/independent-campaign-audit.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
