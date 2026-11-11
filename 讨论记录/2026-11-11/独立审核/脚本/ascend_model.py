# 一阶模型试算：用 Ascend-SpMM 自己标定的 alpha/beta 在 Cora 上算 AIC/AIV 分工与 makespan
# 模型出处：Ascend-SpMM 式(2)(4)、定理1；alpha=1/295, beta=1/505（原文 p8，实测带宽 295/505 GB/s）
import csv, sys
from collections import defaultdict

ALPHA = 1/295.0   # AIC: 每个非空 W×1 块访问一次 B[k,:]（N 个元素）
BETA  = 1/505.0   # AIV: 每个非零访问一次 B[k,:] 的对应元素

path = sys.argv[1]
rows = list(csv.DictReader(open(path)))
by = defaultdict(list)
for r in rows:
    if r['view'] != 'row_only':   # 列序不影响 c_i / z_i
        continue
    by[r['method']].append((int(r['nnz']), int(r['unique_columns'])))

print(f"break-even density rho* = alpha/beta = {ALPHA/BETA:.3f} (nnz per nonempty block, max {16})")
print()
hdr = f"{'method':9} {'wins':>5} {'SumU':>7} {'SumZ':>7} {'rho_avg':>8} {'k*':>4} {'AIC win%':>9} {'AIC nnz%':>9} {'makespan':>9} {'vs allAIC':>10} {'serial':>8}"
print(hdr); print('-'*len(hdr))
res = {}
for m, ws in by.items():
    # rho 降序排序（定理 1）
    ws_sorted = sorted(ws, key=lambda t: -(t[0]/t[1]))
    n = len(ws_sorted)
    totalZ = sum(z for z,c in ws_sorted)
    totalU = sum(c for z,c in ws_sorted)
    # 前缀 k 个窗口给 AIC，其余给 AIV
    best = None
    pre_c = 0
    suf_z = totalZ
    for k in range(0, n+1):
        if k > 0:
            z,c = ws_sorted[k-1]
            pre_c += c
            suf_z -= z
        t_aic = ALPHA*pre_c
        t_aiv = BETA*suf_z
        ms = max(t_aic, t_aiv)
        if best is None or ms < best[0]:
            best = (ms, k, pre_c, totalZ-suf_z, t_aic, t_aiv)
    ms, k, aic_c, aic_z, t_aic, t_aiv = best
    all_aic = ALPHA*totalU
    serial  = sum(min(ALPHA*c, BETA*z) for z,c in ws_sorted)   # T6 的「逐行/逐窗取小者」
    res[m] = dict(ms=ms, all_aic=all_aic, k=k, n=n, aic_z=aic_z, totalZ=totalZ,
                  totalU=totalU, t_aic=t_aic, t_aiv=t_aiv, serial=serial)
    print(f"{m:9} {n:5d} {totalU:7d} {totalZ:7d} {totalZ/totalU:8.3f} {k:4d} "
          f"{100*k/n:8.1f}% {100*aic_z/totalZ:8.1f}% {ms:9.4f} {ms/all_aic:10.3f} {serial:8.4f}")

print()
base = res['original']['ms']
print("makespan 相对 original（越小越好）：")
for m in ['original','rabbit','neutron','rsh']:
    if m in res:
        r = res[m]
        print(f"  {m:9} {r['ms']/base:6.3f}   (全上 AIC 时为 {r['all_aic']/res['original']['all_aic']:.3f})")
