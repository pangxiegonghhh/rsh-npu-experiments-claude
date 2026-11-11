# T24 §3：收益的驱动因素检查——ρ、受益行占比、优势因子 (ΔU/nz)·ρ 的分布
# 用法：python3 -I -B t24_driver.py <仓库根目录>
import importlib.util, sys, random, statistics as st
REPO=sys.argv[1]; W=16; A=1/295.0; B=1/505.0
spec=importlib.util.spec_from_file_location('pilot',REPO+'/第一层实验结果/cora-pilot-20261104/rsh_reorder_experiment.py')
pilot=importlib.util.module_from_spec(spec); sys.modules['pilot']=pilot; spec.loader.exec_module(pilot)
def stats(sup,order,n,label):
    pos={o:i for i,o in enumerate(order)}
    rhos=[];rates=[]
    for s in range(0,n,W):
        rs=[frozenset(pos[c] for c in sup[o]) for o in order[s:s+W]]
        if not rs: continue
        u=set().union(*rs); c=len(u); z=sum(len(x) for x in rs)
        if c==0 or z==0: continue
        rhos.append(z/c)
        cnt={}
        for x in rs:
            for q in x: cnt[q]=cnt.get(q,0)+1
        for x in rs:
            if not x: continue
            dU=sum(1 for q in x if cnt[q]==1)
            rates.append(dU/len(x)*(z/c))     # (ΔU/nz)·ρ_i：>1 即优于整窗移出
    cv=st.pstdev(rhos)/st.mean(rhos)
    good=sum(1 for r in rates if r>1)/len(rates)
    print(f'{label:26}ρ均值 {st.mean(rhos):6.3f}  ρ的CV {cv:5.3f}  '
          f'(ΔU/nz)·ρ>1 的行占比 {good*100:5.1f}%  该量 p90 {sorted(rates)[int(.9*len(rates))]:5.2f}')
hdr=None;pairs=[]
for line in open(REPO+'/第一层实验结果/cora-pilot-20261104/neutron-matrices/cora.mtx'):
    if line.startswith('%'): continue
    p=line.split()
    if hdr is None: hdr=(int(p[0]),); continue
    pairs.append((int(p[0])-1,int(p[1])-1))
n=hdr[0];ent=[set() for _ in range(n)]
for r,c in pairs:
    if r!=c: ent[r].add(c); ent[c].add(r)
M=pilot.SparseMatrix(n_rows=n,n_cols=n,entries=[[(c,1.0) for c in sorted(e)] for e in ent]); sup=M.supports
o,_,_,_=pilot.rsh_reorder(M,k=8,weighted_alpha=0.0)
stats(sup,o,n,'cora B1 (改善 3.97%)')
stats(sup,list(range(n)),n,'cora B0 (改善 1.63%)')
def pl(n,md,seed,gamma=2.5):
    rnd=random.Random(seed); w=[(i+1)**(-1/(gamma-1)) for i in range(n)]
    t=sum(w); w=[x/t for x in w]; cum=[];s=0
    for x in w: s+=x; cum.append(s)
    def pick():
        r=rnd.random();lo,hi=0,n-1
        while lo<hi:
            m=(lo+hi)//2
            if cum[m]<r: lo=m+1
            else: hi=m
        return lo
    e=[set() for _ in range(n)]; tg=n*md//2; c=0; g=0
    while c<tg and g<tg*40:
        g+=1; a,b=pick(),pick()
        if a==b or b in e[a]: continue
        e[a].add(b); e[b].add(a); c+=1
    return e
for md,gn in [(4,'3.62%'),(16,'0.46%'),(64,'0.013%')]:
    e=pl(1600,md,11); M2=pilot.SparseMatrix(n_rows=1600,n_cols=1600,entries=[[(c,1.0) for c in sorted(x)] for x in e])
    o2,_,_,_=pilot.rsh_reorder(M2,k=8,weighted_alpha=0.0)
    stats(M2.supports,o2,1600,f'合成 deg={md} (改善 {gn})')
