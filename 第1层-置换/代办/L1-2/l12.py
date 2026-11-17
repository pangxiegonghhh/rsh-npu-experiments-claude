"""L1-2：对称视图下的列置换（Cora）。固定 B1 的窗口成员，只调窗口先后与窗口内行序，以代价模型为目标做局部搜索。

仓库根目录运行（需先 git worktree add ../rsh-npu-v1 v1-final）：
    python3 -I -B 第1层-置换/代办/L1-2/l12.py <目标 nd|best> <步数> <种子>
    例：l12.py nd 300000 2（约 6 分钟）；l12.py best 300000 3
目标 nd = 全走 ND 的总代价（等价于压调用次数）；best = 逐窗取 min(按行, ND) 的总代价。
结果写到同目录 outputs/l12_<目标>_<步数>_<种子>.json（含起点、结果、得到的行序）。只用标准库。
"""
import json,sys,random,math,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[2]/'第5层-供数'/'代办'/'L5-1'))
from nd2nz_calls import load_cora, window_calls
A,B,C=23.5,67.5,140.0; N=128
n,rows,_orders=load_cora(); perm=_orders['B1']
W=16; wins=[perm[s:s+W] for s in range(0,n,W)]           # 窗口成员（节点）
nbr_w={}                                                  # 节点 -> 哪些窗口用到它这一列
for wi,m in enumerate(wins):
    for v in m:
        for c in rows[v]: nbr_w.setdefault(c,set()).add(wi)
Ucols=[sorted({c for v in m for c in rows[v]}) for m in wins]   # 每窗要的列（节点），不随编号变
def numbering(worder,inner):
    pos={};i=0
    for wi in worder:
        for v in inner[wi]: pos[v]=i;i+=1
    return pos
def wcost(wi,pos):
    U=sorted(pos[c] for c in Ucols[wi])
    if not U: return (0,0,0.0)
    T,calls,_=window_calls(U,N,n+16)
    return (T,calls,min(A*16*T,B*calls+C*T))
def evaluate(pos):
    return [wcost(wi,pos) for wi in range(len(wins))]
def summary(cs):
    T=sum(c[0] for c in cs);K=sum(c[1] for c in cs);best=sum(c[2] for c in cs);row=A*16*T;nd=B*K+C*T
    return dict(T=T,calls=K,rows_per_call=16*T/K,all_row=row/1e3,all_nd=nd/1e3,best=best/1e3,gain_pct=100*(1-best/min(row,nd)),
                nd_windows=sum(1 for c in cs if c[0] and B*c[1]+C*c[0]<A*16*c[0]))
def search(obj="best",iters=60000,seed=0,T0=3.0):
    rnd=random.Random(seed)
    worder=list(range(len(wins))); inner=[list(m) for m in wins]
    pos=numbering(worder,inner); cs=evaluate(pos)
    key=(lambda c:c[2]) if obj=='best' else (lambda c:B*c[1]+C*c[0])
    cur=sum(key(c) for c in cs); t0=time.time()
    for it in range(iters):
        temp=T0*(1-it/iters)
        mv=rnd.random()
        if mv<0.4:   # 交换两个窗口的位置
            i,j=rnd.sample(range(len(worder)),2); worder[i],worder[j]=worder[j],worder[i]; undo=('w',i,j)
        elif mv<0.6: # 把一个窗口挪到另一位置
            i,j=rnd.sample(range(len(worder)),2); x=worder.pop(i); worder.insert(j,x); undo=('m',j,i)
        else:        # 窗口内交换两行
            wi=rnd.randrange(len(wins)); m=inner[wi]
            if len(m)<2: continue
            i,j=rnd.sample(range(len(m)),2); m[i],m[j]=m[j],m[i]; undo=('r',wi,i,j)
        newpos=numbering(worder,inner)
        moved=[v for v in newpos if newpos[v]!=pos[v]]
        aff=set()
        for v in moved: aff|=nbr_w.get(v,set())
        newc={wi:wcost(wi,newpos) for wi in aff}
        delta=sum(key(newc[wi])-key(cs[wi]) for wi in aff)
        if delta<=0 or (temp>0 and rnd.random()<math.exp(-delta/temp)):
            pos=newpos; cur+=delta
            for wi,c in newc.items(): cs[wi]=c
        else:
            if undo[0]=='w': worder[undo[1]],worder[undo[2]]=worder[undo[2]],worder[undo[1]]
            elif undo[0]=='m': x=worder.pop(undo[1]); worder.insert(undo[2],x)
            else: m=inner[undo[1]]; m[undo[2]],m[undo[3]]=m[undo[3]],m[undo[2]]
    return worder,inner,pos,cs,time.time()-t0
if __name__=='__main__':
    obj=sys.argv[1]; iters=int(sys.argv[2]); seed=int(sys.argv[3])
    base=summary(evaluate(numbering(list(range(len(wins))),[list(m) for m in wins])))
    wo,inn,pos,cs,dt=search(obj,iters,seed)
    cs=evaluate(pos)   # 全量复核
    order=[v for wi in wo for v in inn[wi]]
    json.dump({'obj':obj,'iters':iters,'seed':seed,'base':base,'result':summary(cs),'seconds':dt,'order':order},open(HERE/'outputs'/f'l12_{obj}_{iters}_{seed}.json','w'))
    print(obj,iters,seed,'base',{k:round(v,3) for k,v in base.items()});print('  result',{k:round(v,3) for k,v in summary(cs).items()},'%.0fs'%dt)
