# Ascend-SpMM 一阶模型对 α/β 比值的敏感性（审核记录 02 号 §3.1）
# 用法: python3 -I ascend_sensitivity.py <cora-pilot 的 window_metrics.csv>
import csv, sys
from collections import defaultdict
by=defaultdict(list)
for r in csv.DictReader(open(sys.argv[1])):
    if r['view']=='row_only': by[r['method']].append((int(r['nnz']),int(r['unique_columns'])))
def ms(ws,a,b):
    ws=sorted(ws,key=lambda t:-t[0]/t[1]); Z=sum(z for z,c in ws); best=1e18; pc=0; sz=Z
    for k in range(len(ws)+1):
        if k: z,c=ws[k-1]; pc+=c; sz-=z
        best=min(best,max(a*pc,b*sz))
    return best
print("AIV/AIC 带宽倍数（原文 505/295 = 1.71）-> rsh 相对 original 的 makespan")
for f in [0.5,0.75,1.0,1.5,2.0,3.0]:
    a=1/295; b=1/(295*1.712*f)
    r=ms(by['rsh'],a,b)/ms(by['original'],a,b)
    print(f"  倍数 {1.712*f:5.2f}: rsh/original = {r:.3f}  (省 {100*(1-r):.1f}%)")
