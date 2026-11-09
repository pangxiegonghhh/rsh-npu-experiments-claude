from __future__ import annotations
import gc,hashlib,json,pickle,sys,time
from pathlib import Path
import numpy as np
import scipy.io as sio
import scipy.sparse as sp
BASE=Path(__file__).resolve().parents[1];OLD=BASE.parent/'t21-rq2-20261106-pkg9'
def main():
    inputs=json.loads((BASE/'logs/first-batch-matrices.json').read_text());records=[]
    for meta in inputs:
        name=meta['matrix'];start=time.perf_counter();root=BASE/'work/matrices'/name;root.mkdir(parents=True,exist_ok=True)
        raw=sio.mmread(meta['input_path']).tocoo();mask=raw.row!=raw.col;r=raw.row[mask];c=raw.col[mask];n=raw.shape[0]
        A=sp.csr_matrix((np.ones(2*len(r),dtype=np.int8),(np.r_[r,c],np.r_[c,r])),shape=(n,n));A.data[:]=1;A.sort_indices()
        assert A.nnz==meta['nnz_A0']and n==meta['n'];del raw,r,c,mask;gc.collect()
        cache=OLD/'work'/(name+'-A0.pickle');adj=pickle.loads(cache.read_bytes())
        ptr=np.zeros(n+1,dtype=np.int64);ptr[1:]=np.cumsum([len(x)for x in adj]);idx=np.fromiter((u for row in adj for u in row),dtype=np.int32,count=int(ptr[-1]))
        C=sp.csr_matrix((np.ones(len(idx),dtype=np.int8),idx,ptr),shape=(n,n));C.sort_indices();assert (C!=A).nnz==0
        # Flatten again: scipy.sort_indices may sort a shared buffer. Preserve original set iteration for BP's float sums.
        idx=np.fromiter((u for row in adj for u in row),dtype=np.int32,count=int(ptr[-1]));degree=np.diff(ptr).astype(np.int32)
        for key,val in [('indptr',ptr),('indices',idx),('degrees',degree)]:np.save(root/(key+'.npy'),val)
        if np.mean(degree<=3)>=.1:taus=[(2,'fixed'),(3,'fixed')]
        else:
            sort=np.sort(degree);taus=[(int(sort[int(np.ceil(q*n))-1]),tag)for q,tag in[(.2,'q20'),(.4,'q40')]]
        rows=[]
        for tau,rule in taus:
            residual=degree<=tau;rows.append({'tau':tau,'tau_rule':rule,'resid_count':int(residual.sum()),'resid_frac':float(residual.mean()),'resid_nnz_frac':float(degree[residual].sum()/degree.sum())})
        record={**meta,'csr_dir':str(root),'adjacency_order':'original T21 pickle set iteration, independently identical to raw MTX pattern',
          'csr_sha256':{key:hashlib.sha256((root/(key+'.npy')).read_bytes()).hexdigest()for key in('indptr','indices','degrees')},'taus':rows,
          'fixed_tau_diagnostics':{str(t):{'resid_frac':float(np.mean(degree<=t)),'resid_nnz_frac':float(degree[degree<=t].sum()/degree.sum())}for t in(2,3)},'prepared_sec':time.perf_counter()-start}
        (root/'metadata.json').write_text(json.dumps(record,ensure_ascii=False,indent=2));records.append(record)
        print(name,n,A.nnz,rows,round(record['prepared_sec'],3),flush=True)
        del adj,ptr,idx,degree,A,C;gc.collect()
    (BASE/'logs/matrices-and-taus.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
