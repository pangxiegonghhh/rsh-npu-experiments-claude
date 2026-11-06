# Independent re-implementation (numpy/scipy), does not import rq2lib.
# Usage: python3 -I indep_check.py <matrix.mtx> <orders.json>; keys ending in 'tau3D' are evaluated with tau=3, tail placement.
import json, sys, numpy as np, scipy.sparse as sp
mtx = sys.argv[1]; orders = json.load(open(sys.argv[2]))
rows=[];cols=[]
with open(mtx) as f:
    lines=[l for l in f if not l.startswith('%')]
n=int(lines[0].split()[0])
for l in lines[1:]:
    t=l.split()
    # explicit zeros are kept: structure = stored pattern (same rule as rq2lib.load_mtx)
    a,b=int(t[0])-1,int(t[1])-1
    if a==b: continue                              # A0: no diagonal
    rows+= [a,b]; cols+=[b,a]
A=sp.csr_matrix((np.ones(len(rows)),(rows,cols)),shape=(n,n)); A.data[:]=1
deg=np.asarray(A.sum(axis=1)).ravel()
def metrics(order, tau=None, W=16):
    order=np.array(order)
    if tau is None: kept=order; colorder=order
    else:
        kept=order[deg[order]>tau]; colorder=np.concatenate([kept, order[deg[order]<=tau]])
    pos=np.empty(n,dtype=int); pos[colorder]=np.arange(n)
    U=R=G=T=0; k=0
    for s in range(0,len(kept),W):
        sub=A[kept[s:s+W]]
        c=np.unique(pos[sub.indices]);
        U+=len(c); T+=-(-len(c)//16); G+=len(np.unique(c//W)); R+= (1+np.count_nonzero(np.diff(c)!=1)) if len(c) else 0; k+=1
    return round(float(U)/k,2),int(T),round(float(G)/k,2),round(float(R)/k,2)
for key,o in orders.items():
    assert sorted(o)==list(range(n))
    if key.endswith('tau3D'): print(key, metrics(o,tau=3))
    else: print(key, metrics(o))
