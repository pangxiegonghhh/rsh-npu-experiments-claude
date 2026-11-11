# T23 时间轴核对：逐矩阵的 order_sec、是否继承自 T21、执行主机；以及两种时间轴下的帕累托前沿
# 用法: python3 -I t23_time_axis.py <阶段1-2 results.csv> <阶段3 results.csv>
# 对应审核记录 04 号 §6.1、T4 方案 §4.2
import csv, math, sys
from collections import defaultdict
A, B = sys.argv[1], sys.argv[2]
rows=[]
for p in (A,B):
    for r in csv.DictReader(open(p)): rows.append(r)
def gm(v): return math.exp(sum(math.log(x) for x in v)/len(v))
P0=['C9-Gorder','C9-S','C10-BP','C2-LSH','C3-W1','C3-W4','C4-U','C4-T','C7-I','C1-J','C1-H','C5','C5-U','C8-METIS']
MATS=['cora','ogbn-arxiv','reddit','ogbn-products','wiki-RfA','dawson5','olafu','pattern1','human_gene1']
HOSTA=[m for m in MATS if m!='ogbn-products']

print("=== 逐矩阵 order_sec / 继承 / 主机（B1、C9-Gorder、C10-BP、C4-U）===")
for mem in ['B1','C9-Gorder','C10-BP','C4-U']:
    print(f"-- {mem}")
    seen=set()
    for r in rows:
        if r['member']!=mem or r['W']!='16' or r['status']!='OK' or not r.get('order_sec'): continue
        if r['matrix'] in seen: continue
        seen.add(r['matrix'])
        print(f"   {r['matrix']:16} {float(r['order_sec']):10.2f}s  继承={'是' if 'inherited' in r.get('note','') else '否'}  host={r.get('recorded_execution_host_id','')}")

sel=[r for r in rows if r['W']=='16' and r['tau'] not in ('','none') and r['status']=='OK'
     and r['T_ratio_B0'] and r.get('source','')!='post-E']
val={}
for r in sel: val[(r['matrix'],r['diag'],r['member'],r['tau'],r['seed'])]=float(r['T_ratio_B0'])
pt=defaultdict(list)
for (m,d,mem,t,s),v in val.items(): pt[(m,d,mem,t)].append(v)
pts={k:gm(v) for k,v in pt.items()}
tm=defaultdict(dict)
for r in rows:
    if r['W']=='16' and r['status']=='OK' and r.get('order_sec'):
        try: s=float(r['order_sec'])
        except ValueError: continue
        tm[r['member']].setdefault(r['matrix'], s)
for label, mats in (("全九张（含 hostB 的 ogbn-products）", MATS), ("同主机八张（products 另算）", HOSTA)):
    print(f"\n===== 时间轴：{label} =====")
    cand={}
    for mem in P0+['B1']:
        v=[x for (m,d,mm,t),x in pts.items() if mm==mem and d=='A0' and m in mats]
        nm={m for (m,d,mm,t) in pts if mm==mem and d=='A0' and m in mats}
        if len(nm)!=len(mats): continue
        cand[mem]=(gm(v), sum(tm[mem].get(m,0.0) for m in mats))
    print(f"{'成员':<12}{'T几何均值':>9}{'时间秒':>10}   前沿")
    for mem,(g,t) in sorted(cand.items(), key=lambda kv:kv[1][0]):
        dom=[o for o,(g2,t2) in cand.items() if o!=mem and g2<=g and t2<=t and (g2<g or t2<t)]
        domc=[o for o,(g2,t2) in cand.items() if o not in (mem,'B1') and g2<=g and t2<=t and (g2<g or t2<t)]
        print(f"{mem:<12}{g:9.3f}{t:10.1f}   {'★含B1前沿' if not dom else '':10} {'☆候选内前沿' if (mem!='B1' and not domc) else ''}")
