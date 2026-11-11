import importlib.util, sys, math, time, random, hashlib
REPO=sys.argv[1] if len(sys.argv)>1 else '.'
SRC=REPO+'/第一层实验结果/cora-pilot-20261104/rsh_reorder_experiment.py'
spec=importlib.util.spec_from_file_location('pilot', SRC)
m=importlib.util.module_from_spec(spec); sys.modules['pilot']=m; spec.loader.exec_module(m)

# 合成幂律图（优先连接），度数跨度大，用来检验 α 在 hub 多时是否起作用
def ba(n, mm, seed=7):
    rnd=random.Random(seed); adj=[set() for _ in range(n)]; targets=list(range(mm)); rep=[]
    for v in range(mm,n):
        for t in set(targets):
            adj[v].add(t); adj[t].add(v); rep.extend([v,t])
        targets=[]
        while len(targets)<mm:
            x=rnd.choice(rep) if rep and rnd.random()<0.9 else rnd.randrange(v+1)
            if x!=v: targets.append(x)
    return adj

for n,mm in [(8000,3)]:
    adj=ba(n,mm)
    deg=[len(a) for a in adj]
    nnz=sum(deg)
    print(f"合成幂律图 n={n} nnz={nnz} 平均度={nnz/n:.1f} 最大度={max(deg)} 度数跨度={max(deg)/ (sum(deg)/n):.0f}x")
    M=m.SparseMatrix(n_rows=n,n_cols=n,entries=[[(c,1.0) for c in sorted(a)] for a in adj])
    sup=M.supports
    def evalT(order,W=16):
        pos={o:i for i,o in enumerate(order)}; sU=0;T=0
        for s in range(0,len(order),W):
            cols=set()
            for r in order[s:s+W]: cols.update(pos[c] for c in sup[r])
            sU+=len(cols); T+=math.ceil(len(cols)/16)
        return sU,T
    sU0,T0=evalT(list(range(n)))
    print(f"B0: sumU={sU0} T={T0}")
    print(f"{'alpha':>6}{'k':>4}{'sumU':>8}{'T':>7}{'T/base':>8}{'孤立':>6}{'秒':>7}")
    base=None
    for alpha,kk in [(0.0,8),(0.25,8),(0.5,8),(1.0,8),(0.0,16),(0.0,4)]:
        t0=time.time(); order,_,st,_=m.rsh_reorder(M,k=kk,weighted_alpha=alpha); dt=time.time()-t0
        sU,T=evalT(order)
        if base is None: base=T
        print(f"{alpha:>6}{kk:>4}{sU:>8}{T:>7}{T/base:>8.3f}{st['isolated_rows']:>6}{dt:>7.1f}")
