# T24 第 5 步（cora）：补两项缺失代价，看行粒度的收益还剩多少
#  (i)  AIC 侧零填充浪费
#  (ii) AIV 侧随访问规整度变化的 β —— 用「每个 AIV 行段的固定开销 δ」表达
# 用法：python3 -I -B t24_step5.py <仓库根目录>
import importlib.util, sys, json
from collections import defaultdict

REPO = sys.argv[1] if len(sys.argv) > 1 else '.'
W = 16; ALPHA = 1 / 295.0; BETA = 1 / 505.0; INF = float('inf')

SRC = REPO + '/第一层实验结果/cora-pilot-20261104/rsh_reorder_experiment.py'
spec = importlib.util.spec_from_file_location('pilot', SRC)
pilot = importlib.util.module_from_spec(spec); sys.modules['pilot'] = pilot
spec.loader.exec_module(pilot)
hdr = None; pairs = []
for line in open(REPO + '/第一层实验结果/cora-pilot-20261104/neutron-matrices/cora.mtx'):
    if line.startswith('%'): continue
    p = line.split()
    if hdr is None: hdr = (int(p[0]),); continue
    pairs.append((int(p[0]) - 1, int(p[1]) - 1))
n = hdr[0]; ent = [set() for _ in range(n)]
for r, c in pairs:
    if r != c: ent[r].add(c); ent[c].add(r)
M = pilot.SparseMatrix(n_rows=n, n_cols=n, entries=[[(c, 1.0) for c in sorted(e)] for e in ent])
sup = M.supports
order, _, _, _ = pilot.rsh_reorder(M, k=8, weighted_alpha=0.0)
pos = {old: i for i, old in enumerate(order)}
windows = [[frozenset(pos[c] for c in sup[o]) for o in order[s:s + W]] for s in range(0, n, W)]
assert sum(len(set().union(*rs)) for rs in windows if rs) == 6035

# 菜单，并记录每一项「移出集合」在窗口内的行段数（移出行按窗口内位置是否相邻合并）
def menu(rows):
    cnt = defaultdict(int)
    for cs in rows:
        for c in cs: cnt[c] += 1
    alive = set(range(len(rows))); out = [(len(cnt), 0, 0, frozenset())]
    curZ = 0; movedset = set()
    while alive:
        best = None
        for i in alive:
            nz = len(rows[i]); dU = sum(1 for c in rows[i] if cnt[c] == 1)
            ratio = -1.0 if nz == 0 else dU / nz
            if best is None or ratio > best[0] or (ratio == best[0] and i < best[1]):
                best = (ratio, i, dU, nz)
        _, i, dU, nz = best
        alive.discard(i)
        for c in rows[i]:
            cnt[c] -= 1
            if cnt[c] == 0: del cnt[c]
        curZ += nz; movedset.add(i)
        segs = sum(1 for x in sorted(movedset) if x - 1 not in movedset)
        out.append((len(cnt), curZ, segs, frozenset(movedset)))
    return out

menus = [menu(rs) for rs in windows]
whole = [[m[0], m[-1]] for m in menus]
totalU = sum(m[0][0] for m in menus); totalZ = sum(m[-1][1] for m in menus)

def solve(menus_in, alpha, beta, delta=0.0):
    """精确 DP：A = alpha*ΣC，V = beta*ΣZ + delta*ΣR（R 为窗口内行段数，忽略跨窗合并）"""
    cap = sum(mx[0][0] for mx in menus_in)
    f = [INF] * (cap + 1); f[0] = 0.0
    layers = []
    for mn in menus_in:
        g = [INF] * (cap + 1); ch = [-1] * (cap + 1)
        for j, it in enumerate(mn):
            ci = it[0]; cost = beta * it[1] + delta * it[2]
            for C in range(ci, cap + 1):
                v = f[C - ci]
                if v != INF and v + cost < g[C]:
                    g[C] = v + cost; ch[C] = j
        layers.append(ch); f = g
    best = INF; argC = None; run = INF; runC = None
    for C in range(cap + 1):
        if f[C] < run: run = f[C]; runC = C
        if run == INF: continue
        ms = max(alpha * C, run)
        if ms < best: best = ms; argC = runC
    sel = []; C = argC
    for mn, ch in zip(reversed(menus_in), reversed(layers)):
        j = ch[C]; sel.append(j); C -= mn[j][0]
    return best, list(reversed(sel))

def globalR(sel, menus_in):
    """被移到 AIV 的行在全局新编号下的真实行段数（含跨窗合并）"""
    rows = set()
    for w, j in enumerate(sel):
        for i in menus_in[w][j][3]: rows.add(w * W + i)
    return sum(1 for x in sorted(rows) if x - 1 not in rows), len(rows)

ms_w, sel_w = solve(whole, ALPHA, BETA)
ms_f, sel_f = solve(menus, ALPHA, BETA)
Rw, nw = globalR(sel_w, whole); Rf, nf = globalR(sel_f, menus)
print(f'基准（δ=0）：整窗 {ms_w:.5f}  行粒度 {ms_f:.5f}  改善 {(1-ms_f/ms_w)*100:.4f}%')
print(f'  AIV 行集合：整窗 {nw} 行 / {Rw} 段（平均段长 {nw/Rw:.1f}）；'
      f'行粒度 {nf} 行 / {Rf} 段（平均段长 {nf/Rf:.1f}）')

print()
print('(i) AIC 侧零填充浪费')
print('    窗口 i 的 AIC 侧无论怎么算都 ∝ c_i：B 搬运 α·c_i·N（原文式2）、Cube 的 MAC 数 W·c_i·N、')
print('    A 侧稠密 tile 字节 W·c_i——零填充浪费的是「有用比例 z_i/(W·c_i)」，不改变代价对 c_i 的正比关系。')
print('    故该项等价于把 α 放大为 α+γW，只改变 α/β 比值，不改变结构。实算确认：')
print(f"{'α 放大倍数':>10}{'α/β':>9}{'整窗 ms':>11}{'行粒度 ms':>12}{'改善':>9}")
for w in [1.0, 1.5, 2.0, 3.0, 5.0]:
    a = ALPHA * w
    x, _ = solve(whole, a, BETA); y, _ = solve(menus, a, BETA)
    print(f'{w:10.1f}{a/BETA:9.3f}{x:11.5f}{y:12.5f}{(1-y/x)*100:8.4f}%')
useful = [(m[-1][1], m[0][0]) for m in menus]
print(f'    参考：cora 上 B1 的 AIC 有用比例 z_i/(W·c_i) 全窗合计 = {totalZ/(W*totalU):.3f}'
      f'（即 Cube 的 MAC 有 {100*(1-totalZ/(W*totalU)):.1f}% 花在零上）')

print()
print('(ii) AIV 侧每段固定开销 δ（β 随访问规整度变化的最小表达）')
print('     依据：Ascend-SpMM §2.3、图 3(b)——朴素 CSR 的 AIV 受 8 个同步标志上限，只用到 16.17%')
print('     有效带宽；其环形缓冲对朴素 CSR 快 12.87–13.43×。即 β 不是常数，随访问是否连续成段变化。')
print('     δ 的单位取「相当于多少个非零的搬运时间」：δ = x·β。')
print(f"{'x(=δ/β)':>9}{'整窗 ms':>11}{'行粒度 ms':>12}{'改善':>9}{'行粒度段数':>11}")
rows_out = []
for x in [0, 1, 2, 4, 8, 16, 32, 64]:
    d = x * BETA
    a, sa = solve(whole, ALPHA, BETA, d); b, sb = solve(menus, ALPHA, BETA, d)
    rb, nb = globalR(sb, menus)
    rows_out.append((x, a, b, 1 - b / a, rb, nb))
    print(f'{x:9d}{a:11.5f}{b:12.5f}{(1-b/a)*100:8.4f}%{rb:11d}')

# 固定两个 δ=0 的最优分配，求「抹平 3.92% 差距」的 δ*（用真实全局段数，含跨窗合并）
def cost_fixed(sel, menus_in, delta):
    C = sum(menus_in[w][j][0] for w, j in enumerate(sel))
    Z = sum(menus_in[w][j][1] for w, j in enumerate(sel))
    R, _ = globalR(sel, menus_in)
    return max(ALPHA * C, BETA * Z + delta * R)
lo, hi = 0.0, 100 * BETA
for _ in range(200):
    mid = (lo + hi) / 2
    if cost_fixed(sel_f, menus, mid) >= cost_fixed(sel_w, whole, mid): hi = mid
    else: lo = mid
print()
print(f'     固定两个 δ=0 的最优分配（用含跨窗合并的真实段数）：δ* = {hi:.6f} = {hi/BETA:.2f}·β')
print(f'     即「一个额外的 AIV 行段 ≈ {hi/BETA:.1f} 个非零的搬运时间」时，行粒度的优势被抹平。')
print(f'     重新优化（允许按 δ 调整分配）时优势消失得更慢，见上表。')

json.dump(dict(ms_w=ms_w, ms_f=ms_f, Rw=Rw, nw=nw, Rf=Rf, nf=nf,
               useful_ratio=totalZ / (W * totalU), delta_star_over_beta=hi / BETA,
               delta_rows=[dict(x=x, whole=a, fine=b, gain=g, R=r, nrows=nn)
                           for x, a, b, g, r, nn in rows_out]),
          open('t24_step5.json', 'w'), indent=1)
