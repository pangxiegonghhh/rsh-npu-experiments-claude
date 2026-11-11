import importlib.util, sys, hashlib, math, time
REPO=sys.argv[1] if len(sys.argv)>1 else '.'
SRC=REPO+'/第一层实验结果/cora-pilot-20261104/rsh_reorder_experiment.py'
spec=importlib.util.spec_from_file_location('pilot', SRC)
m=importlib.util.module_from_spec(spec); sys.modules['pilot']=m; spec.loader.exec_module(m)

path=REPO+'/第一层实验结果/cora-pilot-20261104/neutron-matrices/cora.mtx'
hdr=None; pairs=[]
with open(path) as f:
    for line in f:
        if line.startswith('%'): continue
        p=line.split()
        if hdr is None: hdr=(int(p[0]),int(p[1]),int(p[2])); continue
        pairs.append((int(p[0])-1,int(p[1])-1))
n=hdr[0]
ent=[set() for _ in range(n)]
for r,c in pairs:            # A0：对称化、无自环
    if r!=c: ent[r].add(c); ent[c].add(r)
nnz=sum(len(e) for e in ent)
print(f'n={n}  nnz(A0)={nnz}   期望 10556 -> {"OK" if nnz==10556 else "不符"}')
M=m.SparseMatrix(n_rows=n, n_cols=n, entries=[[(c,1.0) for c in sorted(e)] for e in ent])
sup=M.supports

def evalT(order, W=16):
    pos={old:i for i,old in enumerate(order)}
    sumU=0; T=0
    for s in range(0,len(order),W):
        cols=set()
        for r in order[s:s+W]: cols.update(pos[c] for c in sup[r])
        sumU+=len(cols); T+=math.ceil(len(cols)/16)
    return sumU,T

print(f"\n{'alpha':>6}{'k':>4}{'sumU':>8}{'T':>6}{'T/base':>8}{'孤立行':>7}{'分量':>6}{'秒':>7}  哈希")
res={}
for alpha,kk in [(0.0,8),(0.125,8),(0.25,8),(0.5,8),(0.75,8),(1.0,8),
                 (0.0,4),(0.0,16),(0.0,32)]:
    t0=time.time()
    order,_,stats,_=m.rsh_reorder(M,k=kk,weighted_alpha=alpha)
    dt=time.time()-t0
    sumU,T=evalT(order)
    h=hashlib.sha256((','.join(map(str,order))).encode()).hexdigest()[:12]
    res[(alpha,kk)]=(sumU,T,h)
    base=res[(0.0,8)][1]
    print(f"{alpha:>6}{kk:>4}{sumU:>8}{T:>6}{T/base:>8.3f}{stats['isolated_rows']:>7}{stats['graph_components']:>6}{dt:>7.1f}  {h}")
# B0 参照
sumU0,T0=evalT(list(range(n)))
print(f"\nB0（原始序）sumU={sumU0} T={T0}；rsh(α=0,k=8) T/T(B0)={res[(0.0,8)][1]/T0:.3f}")
