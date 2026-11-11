import csv, math
from collections import defaultdict
import sys
A=sys.argv[1]  # 阶段1-2 results.csv（round1-compare-20261106/results.csv）
B=sys.argv[2]  # 阶段3 results.csv（round1-compare-stage3-20261106/results.csv）
rows=[]
for p in (A,B):
    for r in csv.DictReader(open(p)): rows.append(r)
def gm(v): return math.exp(sum(math.log(x) for x in v)/len(v))
# 主口径：W16、划分后(tau 不是 none)、OK、后处理之前
sel=[r for r in rows if r['W']=='16' and r['tau'] not in ('','none') and r['status']=='OK'
     and r['T_ratio_B0'] and r.get('source','')!='post-E']
val={}
for r in sel: val[(r['matrix'],r['diag'],r['member'],r['tau'],r['seed'])]=float(r['T_ratio_B0'])
pt=defaultdict(list)
for (m,d,mem,t,s),v in val.items(): pt[(m,d,mem,t)].append(v)
pts={k:gm(v) for k,v in pt.items()}
CAT={'cora':'GNN','ogbn-arxiv':'GNN','reddit':'GNN','ogbn-products':'GNN',
     'wiki-RfA':'真实网络','dawson5':'有限元','olafu':'有限元',
     'pattern1':'长行','human_gene1':'长行'}
NEED={'GNN':4,'真实网络':1,'有限元':2,'长行':2}
P0=['C9-Gorder','C9-S','C10-BP','C2-LSH','C3-W1','C3-W4','C4-U','C4-T','C7-I','C1-J','C1-H','C5','C5-U','C8-METIS']
tsec=defaultdict(float); seen=defaultdict(set)
for r in rows:
    if r['W']=='16' and r['status']=='OK' and r.get('order_sec'):
        try: s=float(r['order_sec'])
        except: continue
        if r['matrix'] not in seen[r['member']]:
            seen[r['member']].add(r['matrix']); tsec[r['member']]+=s
def report(diag):
    res={}
    for mem in P0+['B1','B0']:
        row={}
        for cat in NEED:
            v=[];mats=set()
            for (m,d,mm,t),x in pts.items():
                if mm==mem and d==diag and CAT.get(m)==cat: v.append(x); mats.add(m)
            row[cat]=(gm(v),max(v),len(mats)) if v and len(mats)==NEED[cat] else None
        res[mem]=row
    print(f"\n######## {diag} 主口径（W16/划分后/后处理之前）T/T(B0) ########")
    print(f"{'成员':<12}{'GNN(4张)':>10}{'真实网络':>10}{'有限元':>9}{'长行':>9}  {'有效类数':>6} {'时间秒':>9}")
    print("-"*72)
    def f(c):
        if c is None: return "    n/a  "
        g,w,_=c; return f"{g:8.3f}{'✓' if (g<=0.95 and w<=1.05) else '✗'}"
    def nv(r): return sum(1 for c in r.values() if c and c[0]<=0.95 and c[1]<=1.05)
    for mem in sorted(res, key=lambda m: res[m]['GNN'][0] if res[m]['GNN'] else 9):
        r=res[mem]
        print(f"{mem:<12}{f(r['GNN'])}{f(r['真实网络'])}{f(r['有限元'])}{f(r['长行'])}  {nv(r):>6} {tsec[mem]:9.1f}")
    allg={}
    for mem in P0+['B1']:
        v=[x for (m,d,mm,t),x in pts.items() if mm==mem and d==diag and m in CAT]
        nm=len({m for (m,d,mm,t) in pts if mm==mem and d==diag and m in CAT})
        if nm==9: allg[mem]=(gm(v),tsec[mem])
    print(f"--- 全体九张几何均值 × 时间 的帕累托前沿（{diag}）---")
    for mem,(g,t) in sorted(allg.items(), key=lambda kv:kv[1][0]):
        dom=[o for o,(g2,t2) in allg.items() if o!=mem and g2<=g and t2<=t and (g2<g or t2<t)]
        print(f"  {mem:<12} {g:.3f}  {t:8.1f}秒  {'★前沿' if not dom else ''}")
for d in ('A0','A1'): report(d)
