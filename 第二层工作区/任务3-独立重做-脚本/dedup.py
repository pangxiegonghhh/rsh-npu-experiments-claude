import importlib.util, sys
W=16; ALPHA=1/295.0; BETA=1/505.0
spec=importlib.util.spec_from_file_location('pilot',sys.argv[1]); pilot=importlib.util.module_from_spec(spec); sys.modules['pilot']=pilot; spec.loader.exec_module(pilot)
hdr=None; ent=None
for line in open(sys.argv[2]):
    if line.startswith('%'): continue
    p=line.split()
    if hdr is None: hdr=1; n=int(p[0]); ent=[set() for _ in range(n)]; continue
    r,c=int(p[0])-1,int(p[1])-1
    if r!=c: ent[r].add(c); ent[c].add(r)
M=pilot.SparseMatrix(n_rows=n,n_cols=n,entries=[[(c,1.0) for c in sorted(e)] for e in ent])
order,_,_,_=pilot.rsh_reorder(M,k=8,weighted_alpha=0.0)
for name,o in (('B0',list(range(n))),('B1',order)):
    pos={old:i for i,old in enumerate(o)}; rows=[sorted(pos[c] for c in ent[old]) for old in o]
    wins=[rows[s:s+W] for s in range(0,n,W)]; c=[len(set().union(*map(set,w))) for w in wins]; z=[sum(map(len,w)) for w in wins]
    idx=sorted(range(len(wins)),key=lambda i:-z[i]/c[i]); best=None; C=0; Z=sum(z)
    for k in range(len(idx)+1):
        ms=max(ALPHA*C,BETA*Z)
        if best is None or ms<best[0]: best=(ms,k)
        if k<len(idx): C+=c[idx[k]]; Z-=z[idx[k]]
    aic=set(idx[:best[1]])
    for label,sel in (('整窗分配后的AIV行',[i for i in range(len(wins)) if i not in aic]),('全部行都走AIV',range(len(wins)))):
        seq=[cc for i in sel for r in wins[i] for cc in r]; out=[]
        for L in (16,32,64):
            last={}; hit=0
            for t,cc in enumerate(seq):
                if cc in last and t-last[cc]<L: hit+=1
                last[cc]=t   # 保守：命中后不刷新槽位寿命
            # 更保守：槽位寿命从首次取数算起
            last={}; hit2=0
            for t,cc in enumerate(seq):
                if cc in last and t-last[cc]<L: hit2+=1
                else: last[cc]=t
            out.append(f'L={L}: {hit/len(seq):.1%} / {hit2/len(seq):.1%}')
        print(name,label,'取数',len(seq),'| 可省比例(刷新/不刷新寿命)',' ; '.join(out))
