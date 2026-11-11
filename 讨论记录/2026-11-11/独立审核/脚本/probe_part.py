import importlib.util, sys, math
REPO=sys.argv[1] if len(sys.argv)>1 else '.'
SRC=REPO+'/第一层实验结果/cora-pilot-20261104/rsh_reorder_experiment.py'
spec=importlib.util.spec_from_file_location('pilot', SRC)
m=importlib.util.module_from_spec(spec); sys.modules['pilot']=m; spec.loader.exec_module(m)
path=REPO+'/第一层实验结果/cora-pilot-20261104/neutron-matrices/cora.mtx'
hdr=None; pr=[]
for line in open(path):
    if line.startswith('%'): continue
    p=line.split()
    if hdr is None: hdr=(int(p[0]),int(p[1]),int(p[2])); continue
    pr.append((int(p[0])-1,int(p[1])-1))
n=hdr[0]; ent=[set() for _ in range(n)]
for r,c in pr:
    if r!=c: ent[r].add(c); ent[c].add(r)
M=m.SparseMatrix(n_rows=n,n_cols=n,entries=[[(c,1.0) for c in sorted(e)] for e in ent])
sup=M.supports; nz=[len(s) for s in sup]

def T_part(order, tau, W=16):
    """划分后主口径：nz<=tau 的行送残余；残余按原相对顺序接在编号末尾（末尾规则）"""
    K=[r for r in order if nz[r]>tau]; D=[r for r in order if nz[r]<=tau]
    pos={};
    for i,r in enumerate(K+D): pos[r]=i
    sU=0; T=0
    for s in range(0,len(K),W):
        cols=set()
        for r in K[s:s+W]: cols.update(pos[c] for c in sup[r])
        sU+=len(cols); T+=math.ceil(len(cols)/16)
    return sU,T,len(K)

B0=list(range(n))
print(f"{'alpha':>6}{'k':>4} | " + " | ".join(f"tau={t}: T  T/T(B0)" for t in (2,3)))
base={}
for t in (2,3): base[t]=T_part(B0,t)[1]
print(f"{'B0':>6}{'-':>4} | " + " | ".join(f"       {base[t]:5d}  1.000" for t in (2,3)))
rows=[]
for alpha,kk in [(0.0,8),(0.125,8),(0.25,8),(0.5,8),(0.75,8),(1.0,8),(0.0,4),(0.0,16),(0.0,32),(0.25,16)]:
    order,_,st,_=m.rsh_reorder(M,k=kk,weighted_alpha=alpha)
    out=[]
    for t in (2,3):
        sU,T,nk=T_part(order,t); out.append((T,T/base[t]))
    rows.append((alpha,kk,out))
    print(f"{alpha:>6}{kk:>4} | " + " | ".join(f"       {T:5d}  {r:.3f}" for T,r in out))
g0=[r for a,k,o in rows if (a,k)==(0.0,8) for T,r in o]
print(f"\n几何均值 T/T(B0)（两个 tau）：")
for a,k,o in rows:
    g=math.exp(sum(math.log(r) for T,r in o)/2)
    g00=math.exp(sum(math.log(r) for r in g0)/2)
    print(f"  alpha={a:<6} k={k:<3} {g:.4f}   相对 α0k8 {g/g00:.4f}")
