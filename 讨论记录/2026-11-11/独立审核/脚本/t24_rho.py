# T24 补强：收益随窗口密度 ρ 变化的预测与验证
# 结构性必要条件：单行移出比整窗移出更划算 <=> ΔU/nz_r > 1/ρ_i；而 ΔU ≤ nz_r 恒成立，
# 故 ρ_i ≤ 1 的窗口**不可能**从行粒度得到任何好处。预测：收益随 ρ 单调增，低 ρ 矩阵上为零。
# 验证：同一张 cora，换三种行序（ρ 不同）各算一遍。
# 用法：python3 -I -B t24_rho.py <仓库根目录>
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

def pareto_menu(rows):
    m = len(rows); cols = sorted(set().union(*rows)) if rows else []
    idx = {c: i for i, c in enumerate(cols)}
    cmask = [0] * m; nz = [0] * m
    for i, cs in enumerate(rows):
        b = 0
        for c in cs: b |= 1 << idx[c]
        cmask[i] = b; nz[i] = len(cs)
    total = sum(nz); size = 1 << m
    orv = [0] * size; snz = [0] * size
    for mask in range(1, size):
        lb = mask & -mask; i = lb.bit_length() - 1; prev = mask ^ lb
        orv[mask] = orv[prev] | cmask[i]; snz[mask] = snz[prev] + nz[i]
    best = {}
    for mask in range(size):
        c = bin(orv[mask]).count('1'); Z = total - snz[mask]
        if c not in best or Z < best[c]: best[c] = Z
    out = []; bz = INF
    for c in sorted(best):
        if best[c] < bz: out.append((c, best[c])); bz = best[c]
    return out

def solve(menus_in, alpha=ALPHA, beta=BETA):
    cap = sum(max(it[0] for it in mx) for mx in menus_in)
    f = [INF] * (cap + 1); f[0] = 0
    for mn in menus_in:
        g = [INF] * (cap + 1)
        for (ci, Zi) in mn:
            for C in range(ci, cap + 1):
                v = f[C - ci]
                if v != INF and v + Zi < g[C]: g[C] = v + Zi
        f = g
    best = INF; run = INF
    for C in range(cap + 1):
        if f[C] < run: run = f[C]
        if run != INF: best = min(best, max(alpha * C, beta * run))
    return best

def run(name, order):
    pos = {old: i for i, old in enumerate(order)}
    wins = [[frozenset(pos[c] for c in sup[o]) for o in order[s:s + W]] for s in range(0, n, W)]
    menus = [pareto_menu(rs) for rs in wins]
    whole = [[m[0], m[-1]] for m in menus]
    # 帕累托菜单按 c 升序：m[-1] = 全进 AIC（c=c_i, Z=0），m[0] = 全进 AIV（c=0, Z=z_i）
    U = sum(m[-1][0] for m in menus); Z = sum(m[0][1] for m in menus)
    rho = Z / U
    lo = sum(1 for m in menus if m[0][1] <= m[-1][0])        # z_i ≤ c_i，即 ρ_i ≤ 1
    a = solve(whole); b = solve(menus)
    print(f'{name:16}{U:7d}{rho:8.3f}{lo:8d}{a:10.5f}{b:11.5f}{(1-b/a)*100:9.4f}%')
    return dict(name=name, sumU=U, rho=rho, low_rho_windows=lo, whole=a, fine=b, gain=1 - b / a)

print('同一张 cora（A0、W=16、全行），换行序看收益随 ρ 的变化')
print(f"{'行序':16}{'ΣU':>7}{'平均ρ':>8}{'ρ≤1窗口':>8}{'整窗ms':>10}{'行粒度ms':>11}{'改善':>10}")
print('-' * 71)
res = []
res.append(run('B0 原始序', list(range(n))))
o_rsh, _, _, _ = pilot.rsh_reorder(M, k=8, weighted_alpha=0.0)
res.append(run('B1 rsh(α=0,k=8)', o_rsh))
try:
    o_rb, _, _, _ = pilot.rabbit_reorder(M)
    res.append(run('rabbit（先导版）', o_rb if isinstance(o_rb, list) else list(o_rb)))
except Exception as e:
    print(f'（rabbit 跳过：{type(e).__name__}）')

print()
print('结构性结论：ΔU ≤ nz_r 恒成立，故「单行移出优于整窗移出」的必要条件 ΔU/nz_r > 1/ρ_i')
print('要求 ρ_i > 1。ρ_i ≤ 1 的窗口对行粒度毫无贡献——收益是密度门槛型的，不是普遍存在的。')
json.dump(res, open('t24_rho.json', 'w'), indent=1, ensure_ascii=False)
