"""L1-2 对照：非对称视图（列序独立于行序），B1 窗口固定，只搜列编号。

仓库根目录运行：python3 -I -B 第1层-置换/代办/L1-2/l12_asym.py <步数> <种子>（例：150000 4，约 4–5 分钟）
结果写到 outputs/l12_asym_<步数>_<种子>.json。
"""
import sys,random,math,time,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from l12 import *
def search_cols(iters,seed,T0=3.0,init='sym'):
    rnd=random.Random(seed)
    colorder=[v for wi in range(len(wins)) for v in wins[wi]]   # 起点 = 对称 B1 编号
    pos={v:i for i,v in enumerate(colorder)}; cs=evaluate(pos)
    key=lambda c:B*c[1]+C*c[0]; t0=time.time()
    for it in range(iters):
        temp=T0*(1-it/iters)
        if rnd.random()<0.5:
            i,j=rnd.sample(range(n),2); moved=[colorder[i],colorder[j]]
            colorder[i],colorder[j]=colorder[j],colorder[i]; undo=('s',i,j); lo,hi=min(i,j),max(i,j)
        else:
            i=rnd.randrange(n); j=min(n-1,max(0,i+rnd.randint(-40,40)))
            x=colorder.pop(i); colorder.insert(j,x); undo=('m',j,i); lo,hi=min(i,j),max(i,j)
        newpos=dict(pos)
        for k in range(lo,hi+1): newpos[colorder[k]]=k
        moved=[colorder[k] for k in range(lo,hi+1)]
        aff=set()
        for v in moved: aff|=nbr_w.get(v,set())
        newc={wi:wcost(wi,newpos) for wi in aff}
        delta=sum(key(newc[wi])-key(cs[wi]) for wi in aff)
        if delta<=0 or (temp>0 and rnd.random()<math.exp(-delta/temp)):
            pos=newpos
            for wi,c in newc.items(): cs[wi]=c
        else:
            if undo[0]=='s': colorder[undo[1]],colorder[undo[2]]=colorder[undo[2]],colorder[undo[1]]
            else: x=colorder.pop(undo[1]); colorder.insert(undo[2],x)
    return pos,time.time()-t0
it_,sd_=int(sys.argv[1]),int(sys.argv[2])
pos,dt=search_cols(it_,sd_); res=summary(evaluate(pos))
json.dump({'view':'asym','iters':it_,'seed':sd_,'result':res,'seconds':dt,'col_pos':pos},open(HERE/'outputs'/f'l12_asym_{it_}_{sd_}.json','w'))
print('asym',res,'%.0fs'%dt)
