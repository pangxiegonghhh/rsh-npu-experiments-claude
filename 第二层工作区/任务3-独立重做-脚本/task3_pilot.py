# 任务3 独立重做：cora 上的 CPU 先导核算（只读数据）。用法：python3 -I -B task3_pilot.py <rsh脚本> <cora.mtx>
import importlib.util, sys, math
from collections import Counter
W=16; ALPHA=1/295.0; BETA=1/505.0
spec=importlib.util.spec_from_file_location('pilot',sys.argv[1]); pilot=importlib.util.module_from_spec(spec); sys.modules['pilot']=pilot; spec.loader.exec_module(pilot)
hdr=None; pairs=[]
for line in open(sys.argv[2]):
    if line.startswith('%'): continue
    p=line.split()
    if hdr is None: hdr=(int(p[0]),int(p[1]),int(p[2])); continue
    pairs.append((int(p[0])-1,int(p[1])-1))
n=hdr[0]; ent=[set() for _ in range(n)]
for r,c in pairs:
    if r!=c: ent[r].add(c); ent[c].add(r)
nnz=sum(map(len,ent)); assert nnz==10556
M=pilot.SparseMatrix(n_rows=n,n_cols=n,entries=[[(c,1.0) for c in sorted(e)] for e in ent])
order,_,_,_=pilot.rsh_reorder(M,k=8,weighted_alpha=0.0)
def runs(cols):
    cols=sorted(cols); return sum(1 for i,c in enumerate(cols) if i==0 or c!=cols[i-1]+1)
def analyse(name,order):
    pos={old:i for i,old in enumerate(order)}
    rows=[frozenset(pos[c] for c in ent[old]) for old in order]   # 对称置换后的行
    wins=[rows[s:s+W] for s in range(0,n,W)]
    U=[set().union(*w) for w in wins]; c=[len(u) for u in U]; z=[sum(len(r) for r in w) for w in wins]
    print(f'\n===== {name}: 窗口 {len(wins)}  ΣU={sum(c)}  T=Σceil(U/16)={sum(math.ceil(x/16) for x in c)}  ΣR={sum(runs(u) for u in U)}')
    # Ascend 式整窗前缀分配
    idx=sorted(range(len(wins)),key=lambda i:-(z[i]/c[i] if c[i] else 0))
    best=None; C=0; Z=sum(z)
    for k in range(len(idx)+1):
        ms=max(ALPHA*C,BETA*Z)
        if best is None or ms<best[0]: best=(ms,k,C,Z)
        if k<len(idx): C+=c[idx[k]]; Z-=z[idx[k]]
    ms,k,C,Z=best; aic=set(idx[:k]); aiv=[i for i in range(len(wins)) if i not in aic]
    print(f'整窗前缀: makespan={ms:.5f} AIC窗口={k} ΣC={C} | AIV窗口={len(aiv)} ΣZ={Z}')
    # (1) AIV 侧指令构成（按 Ascend-SpMM 算法1：每非零1条MTE2+1条vaxpy；每行1次清零+1条MTE3写回）
    arows=[r for i in aiv for r in wins[i]]; nr=len(arows); ne=sum(1 for r in arows if not r)
    print(f'[AIV] 行={nr} (空行{ne}) 非零={Z} 平均每行非零={Z/nr:.2f}; 每行固定指令(清零+MTE3)=2 → 占全部搬运/计算指令 {2*nr/(2*nr+2*Z):.1%}; MTE3写回条数/ MTE2取数条数 = {nr/Z:.2f}')
    # (2) 热点列：AIV 非零对列的集中度
    cnt=Counter(cc for r in arows for cc in r); tot=sum(cnt.values()); srt=sorted(cnt.values(),reverse=True)
    print('[AIV] 不同B行数=%d; 前H个热点列覆盖的非零占比: '%len(cnt)+', '.join(f'H={H}:{sum(srt[:H])/tot:.1%}' for H in (16,64,256)))
    # 环形缓冲内的即时复用：相邻 L=64 次取数内重复出现的B行
    seq=[cc for r in arows for cc in sorted(r)]; last={}; hit=0
    for t,cc in enumerate(seq):
        if cc in last and t-last[cc]<64: hit+=1
        last[cc]=t
    print(f'[AIV] 取数序列中，64 次以内刚取过同一B行的占比={hit/len(seq):.1%}')
    # (3) AIC 侧：B 行重复搬运
    aw=sorted(aic); seqU=[sorted(U[i]) for i in aw]; SU=sum(len(u) for u in seqU); dist=len(set().union(*[U[i] for i in aw])) if aw else 0
    print(f'[AIC] 搬运B行次数 ΣU={SU}, 不同B行={dist}, 重复搬运倍数={SU/dist:.2f}, 重复占比={(SU-dist)/SU:.1%}')
    last={}; t=0; d=[]
    for u in seqU:
        for cc in u:
            if cc in last: d.append(t-last[cc])
            last[cc]=t; t+=1
    for cap in (64,256,1024,2000):
        print(f'      复用距离≤{cap} 行的搬运占全部搬运 {sum(1 for x in d if x<=cap)/SU:.1%}')
    ov=[len(U[aw[j]]&U[aw[j+1]])/len(U[aw[j+1]]) for j in range(len(aw)-1) if U[aw[j+1]]]
    print(f'      相邻AIC窗口列并集重合率(占后窗)均值={sum(ov)/len(ov):.1%}')
    cs=sorted(c[i] for i in aw); R=[runs(U[i]) for i in aw]
    print(f'      每窗U: 中位={cs[len(cs)//2]} 最小={cs[0]} 最大={cs[-1]}; 每窗K块数均值={sum(math.ceil(x/16) for x in cs)/len(cs):.2f}; 尾块填充列占比={(sum(16*math.ceil(x/16) for x in cs)-SU)/sum(16*math.ceil(x/16) for x in cs):.1%}')
    print(f'      段数ΣR={sum(R)} 平均段长={SU/sum(R):.2f}（即每条K方向搬运平均带几行B）')
    # (4) 若 HBM 为两引擎共享瓶颈：目标变成总搬运量 C+Z（B行数）
    Cb=sum(c[i] for i in range(len(wins)) if z[i]>=c[i]); Zb=sum(z[i] for i in range(len(wins)) if z[i]<c[i])
    print(f'[共享带宽口径] makespan最优解的总搬运量 C+Z={C+Z}; 最小总搬运量解 C+Z={Cb+Zb} (AIC窗口={sum(1 for i in range(len(wins)) if z[i]>=c[i])}); 全AIC={sum(c)} 全AIV={sum(z)}')
analyse('B0 原始序',list(range(n)))
analyse('B1 rsh(k=8,α=0)',order)
