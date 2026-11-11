# T24（cora 部分）：行粒度划分 vs Ascend 式整窗分配，在 Ascend-SpMM 自己的代价模型下试算
# 模型出处：Ascend-SpMM 式(2)(4)、定理 1；alpha=1/295、beta=1/505（原文 p8 实测带宽 295/505 GB/s）
# 方案出处：讨论记录/2026-11-11/独立审核/02-任务2-收益建模与T24方案.md §6
# 只读数据，不写仓库。用法：python3 -I -B t24_cora.py <仓库根目录>
#
# 求解方式：**精确动态规划**，不用拉格朗日近似。
#   代价已约去 N。AIC 侧 A = α·ΣC（ΣC 为整数，≤ ΣU=6035）；AIV 侧 V = β·ΣZ（ΣZ 整数，≤ 10556）。
#   f[C] = 总列数 ≤ C 时的最小总非零数 → 最优 makespan = min_C max(α·C, β·f[C])。
#   正确性：设最优解总量为 (C*,Z*)，则 f[C*] ≤ Z*，故 min_C ≤ opt；反之每个 (C, f[C]) 都由某个
#   真实解达到且其 A ≤ αC，故 min_C ≥ opt。两边夹紧，等号成立。
import importlib.util, sys, math, json
from collections import defaultdict

REPO = sys.argv[1] if len(sys.argv) > 1 else '.'
W = 16
ALPHA = 1 / 295.0
BETA = 1 / 505.0
INF = float('inf')

# ---------- 1. 数据与行序（自检 ΣU = 6035） ----------
SRC = REPO + '/第一层实验结果/cora-pilot-20261104/rsh_reorder_experiment.py'
spec = importlib.util.spec_from_file_location('pilot', SRC)
pilot = importlib.util.module_from_spec(spec); sys.modules['pilot'] = pilot
spec.loader.exec_module(pilot)

path = REPO + '/第一层实验结果/cora-pilot-20261104/neutron-matrices/cora.mtx'
hdr = None; pairs = []
with open(path) as f:
    for line in f:
        if line.startswith('%'): continue
        p = line.split()
        if hdr is None: hdr = (int(p[0]), int(p[1]), int(p[2])); continue
        pairs.append((int(p[0]) - 1, int(p[1]) - 1))
n = hdr[0]
ent = [set() for _ in range(n)]
for r, c in pairs:                      # A0：对称化、无自环
    if r != c: ent[r].add(c); ent[c].add(r)
nnz = sum(len(e) for e in ent)
assert nnz == 10556, f'nnz(A0)={nnz} != 10556'

M = pilot.SparseMatrix(n_rows=n, n_cols=n, entries=[[(c, 1.0) for c in sorted(e)] for e in ent])
sup = M.supports
order, _, _, _ = pilot.rsh_reorder(M, k=8, weighted_alpha=0.0)   # B1
pos = {old: i for i, old in enumerate(order)}

windows = []
for s in range(0, n, W):
    windows.append([frozenset(pos[c] for c in sup[old]) for old in order[s:s + W]])
sumU = sum(len(set().union(*rs)) for rs in windows if rs)
print(f'自检：n={n} nnz(A0)={nnz} 窗口数={len(windows)} ΣU={sumU}  期望 6035 -> {"OK" if sumU == 6035 else "不符"}')
assert sumU == 6035

# ---------- 2. 每窗菜单：移出 k 行后进 AIC ----------
# 第 k 项 = (剩余行的列并集 c^(k), 已移出行的非零数之和 Z^(k))；k=0 全进 AIC，k=len 全进 AIV。
# 移出顺序：按当前 ΔU/nz_r 降序贪心（ΔU = 该行在窗口内独占的列数，每步重算）。
def menu(rows):
    cnt = defaultdict(int)
    for cs in rows:
        for c in cs: cnt[c] += 1
    alive = set(range(len(rows)))
    out = [(len(cnt), 0)]
    moved = []; curZ = 0
    while alive:
        best = None
        for i in alive:
            nz = len(rows[i])
            dU = sum(1 for c in rows[i] if cnt[c] == 1)
            ratio = -1.0 if nz == 0 else dU / nz
            if best is None or ratio > best[0] or (ratio == best[0] and i < best[1]):
                best = (ratio, i, dU, nz)
        _, i, dU, nz = best
        alive.discard(i)
        for c in rows[i]:
            cnt[c] -= 1
            if cnt[c] == 0: del cnt[c]
        curZ += nz
        moved.append((i, dU, nz))
        out.append((len(cnt), curZ))
    return out, moved

menus = []; moved_log = []
for rs in windows:
    mn, mv = menu(rs); menus.append(mn); moved_log.append(mv)

whole = [[m[0], m[-1]] for m in menus]      # 只有两种选择：整窗 AIC / 整窗 AIV
fine = menus                                # 全菜单
totalZ = sum(m[-1][1] for m in menus)
totalU = sum(m[0][0] for m in menus)
assert totalZ == nnz and totalU == sumU
print(f'      ΣZ={totalZ} ΣU={totalU} 平均 ρ={totalZ/totalU:.3f}  盈亏平衡密度 ρ*=α/β={ALPHA/BETA:.3f}')

# ---------- 3. 精确 DP ----------
def solve_exact(menus_in, alpha=ALPHA, beta=BETA):
    cap = sum(mx[0][0] for mx in menus_in)          # 最大可能总列数
    f = [INF] * (cap + 1); f[0] = 0
    for mn in menus_in:
        g = [INF] * (cap + 1)
        for (ci, Zi) in mn:
            for C in range(ci, cap + 1):
                v = f[C - ci]
                if v != INF:
                    t = v + Zi
                    if t < g[C]: g[C] = t
        f = g
    # f[C] 当前为「总列数恰为 C」的最小 Z；转成「≤ C」
    best = INF; argC = None
    run = INF
    for C in range(cap + 1):
        if f[C] < run: run = f[C]
        if run == INF: continue
        ms = max(alpha * C, beta * run)
        if ms < best: best = ms; argC = (C, run)
    return best, argC

ms_w, (Cw, Zw) = solve_exact(whole)
ms_f, (Cf, Zf) = solve_exact(fine)
all_aic = ALPHA * totalU
all_aiv = BETA * totalZ

# 交叉自检：按 ρ 降序的前缀扫描（任务 2 §3 的 ascend_model.py 做法），应 ≥ 精确 DP
ws = sorted(((m[-1][1], m[0][0]) for m in menus), key=lambda t: -(t[0] / t[1]) if t[1] else -INF)
pre_c = 0; suf_z = totalZ; pref_best = INF
for k in range(len(ws) + 1):
    if k > 0:
        z, c = ws[k - 1]; pre_c += c; suf_z -= z
    pref_best = min(pref_best, max(ALPHA * pre_c, BETA * suf_z))

print()
print('3. 全矩阵汇总（代价已约去 N；makespan = max(AIC 侧, AIV 侧)；DP 为精确最优）')
print(f"{'方案':26}{'makespan':>11}{'AIC侧':>10}{'AIV侧':>10}")
print('-' * 57)
print(f"{'整窗最优（精确 DP）':26}{ms_w:11.5f}{ALPHA*Cw:10.5f}{BETA*Zw:10.5f}")
print(f"{'行粒度最优（精确 DP）':26}{ms_f:11.5f}{ALPHA*Cf:10.5f}{BETA*Zf:10.5f}")
print(f"{'整窗·ρ前缀扫描（交叉校验）':26}{pref_best:11.5f}   期望 ≈ 9.485（任务 2 §3）"
      f" -> {'OK' if abs(pref_best - 9.485) < 0.02 else '不符'}")
print(f"{'全上 AIC':26}{all_aic:11.5f}")
print(f"{'全上 AIV':26}{all_aiv:11.5f}")
gain = 1 - ms_f / ms_w
print()
print(f'>>> 行粒度相对整窗的 makespan 改善 = {gain*100:.4f}%（两端均为精确最优，无求解间隙）')
print(f'    预登记判据 ≥ 5% 记「模型下可见」 -> {"可见" if gain >= 0.05 else "不可见"}')

# 行粒度解的构成
nk = defaultdict(int)
# 反解一个达到最优的方案（再跑一次 DP 并记录选择）
def recover(menus_in, targetC, alpha=ALPHA, beta=BETA):
    cap = sum(mx[0][0] for mx in menus_in)
    layers = []
    f = [INF] * (cap + 1); f[0] = 0
    for mn in menus_in:
        g = [INF] * (cap + 1); ch = [-1] * (cap + 1)
        for j, (ci, Zi) in enumerate(mn):
            for C in range(ci, cap + 1):
                v = f[C - ci]
                if v != INF and v + Zi < g[C]:
                    g[C] = v + Zi; ch[C] = j
        layers.append(ch); f = g
    sel = []; C = targetC
    for mn, ch in zip(reversed(menus_in), reversed(layers)):
        j = ch[C]; sel.append(j); C -= mn[j][0]
    return list(reversed(sel))

sel = recover(fine, Cf)
part = sum(1 for j, rs in zip(sel, windows) if 0 < j < len(rs))
moved_rows = sum(j for j, rs in zip(sel, windows) if 0 < j < len(rs))
full_aiv = sum(1 for j, rs in zip(sel, windows) if j == len(rs))
full_aic = sum(1 for j in sel if j == 0)
print(f'    行粒度最优解：{full_aic} 个窗口整窗进 AIC，{full_aiv} 个整窗进 AIV，'
      f'{part} 个部分移出（共移出 {moved_rows} 行）')

# ---------- 4. 交换率：为什么会有（小）收益 ----------
better = 0; tot = 0
for mn, mv in zip(fine, moved_log):
    c0 = mn[0][0]; z = mn[-1][1]
    if c0 == 0 or z == 0 or not mv or mv[0][2] == 0: continue
    tot += 1
    if mv[0][1] / mv[0][2] > c0 / z: better += 1
first = sorted(mv[0][1] / mv[0][2] for mv in moved_log if mv and mv[0][2] > 0)
print()
print('4. 交换率检查')
print(f'   单行移出的交换率 = αΔU/(β·nz_r)，整窗移出的交换率 = αc_i/(β·z_i)；')
print(f'   故「该行比整窗移出更划算」的充要条件是 ΔU/nz_r > c_i/z_i = 1/ρ_i（与 α、β 无关）。')
print(f'   最划算那一行满足此式的窗口：{better}/{tot}')
print(f'   最划算那一行的 ΔU/nz_r：最小 {first[0]:.3f} 中位 {first[len(first)//2]:.3f} 最大 {first[-1]:.3f}')

# ---------- 5. α/β 比值敏感性 ----------
print()
print('5. α/β 比值敏感性（固定 α=1/295，缩放 β；倍数 = (α/β)/1.712）')
print(f"{'倍数':>7}{'α/β':>9}{'整窗 ms':>11}{'行粒度 ms':>12}{'改善':>9}")
sens = []
for mult in [0.86, 1.00, 1.28, 1.712 / 1.712, 2.57, 3.42, 5.14]:
    ratio = (ALPHA / BETA) * mult
    beta = ALPHA / ratio
    a, _ = solve_exact(whole, ALPHA, beta)
    b, _ = solve_exact(fine, ALPHA, beta)
    sens.append((mult, ratio, a, b, 1 - b / a))
    print(f'{mult:7.2f}{ratio:9.3f}{a:11.5f}{b:12.5f}{(1-b/a)*100:8.4f}%')

json.dump(dict(sumU=sumU, totalZ=totalZ, windows=len(windows),
               ms_whole=ms_w, ms_fine=ms_f, gain=gain, prefix_scan=pref_best,
               all_aic=all_aic, all_aiv=all_aiv,
               full_aic=full_aic, full_aiv=full_aiv, part_windows=part, moved_rows=moved_rows,
               exchange_better=better, exchange_tot=tot,
               sens=[dict(mult=m, ratio=r, whole=a, fine=b, gain=g) for m, r, a, b, g in sens]),
          open('t24_step1_3.json', 'w'), indent=1)
