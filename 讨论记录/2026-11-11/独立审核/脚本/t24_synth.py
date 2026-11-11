# T24 补强：收益随 ρ 的趋势能否越过 5% 门槛——用合成图把 ρ 扫开
# 注意：合成图只用于看趋势，**不替代真实矩阵**（任务 2 §6 第 4 步）。
# 用法：python3 -I -B t24_synth.py <仓库根目录>
import importlib.util, sys, random, json

REPO = sys.argv[1] if len(sys.argv) > 1 else '.'
W = 16; ALPHA = 1 / 295.0; BETA = 1 / 505.0; INF = float('inf')
SRC = REPO + '/第一层实验结果/cora-pilot-20261104/rsh_reorder_experiment.py'
spec = importlib.util.spec_from_file_location('pilot', SRC)
pilot = importlib.util.module_from_spec(spec); sys.modules['pilot'] = pilot
spec.loader.exec_module(pilot)

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

def powerlaw(n, mdeg, seed, gamma=2.5):
    rnd = random.Random(seed)
    w = [(i + 1) ** (-1 / (gamma - 1)) for i in range(n)]
    tot = sum(w); w = [x / tot for x in w]
    cum = []; s = 0
    for x in w: s += x; cum.append(s)
    def pick():
        r = rnd.random(); lo, hi = 0, n - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if cum[mid] < r: lo = mid + 1
            else: hi = mid
        return lo
    ent = [set() for _ in range(n)]
    target = n * mdeg // 2
    cnt = 0; guard = 0
    while cnt < target and guard < target * 40:
        guard += 1
        a, b = pick(), pick()
        if a == b or b in ent[a]: continue
        ent[a].add(b); ent[b].add(a); cnt += 1
    return ent

print('合成幂律图（n=1600，γ=2.5，种子 11），行序一律用 B1 = rsh(α=0,k=8)')
print(f"{'平均度':>7}{'nnz':>9}{'ΣU':>8}{'平均ρ':>8}{'整窗ms':>10}{'行粒度ms':>11}{'改善':>10}  判据")
print('-' * 76)
res = []
for mdeg in [4, 8, 16, 32, 64]:
    n = 1600
    ent = powerlaw(n, mdeg, 11)
    nnz = sum(len(e) for e in ent)
    M = pilot.SparseMatrix(n_rows=n, n_cols=n, entries=[[(c, 1.0) for c in sorted(e)] for e in ent])
    sup = M.supports
    order, _, _, _ = pilot.rsh_reorder(M, k=8, weighted_alpha=0.0)
    pos = {o: i for i, o in enumerate(order)}
    wins = [[frozenset(pos[c] for c in sup[o]) for o in order[s:s + W]] for s in range(0, n, W)]
    menus = [pareto_menu(rs) for rs in wins]
    whole = [[m[-1], m[0]] for m in menus]
    U = sum(m[-1][0] for m in menus); Z = sum(m[0][1] for m in menus)
    a = solve(whole); b = solve(menus); g = 1 - b / a
    res.append(dict(mdeg=mdeg, nnz=nnz, sumU=U, rho=Z / U, whole=a, fine=b, gain=g))
    print(f'{mdeg:7d}{nnz:9d}{U:8d}{Z/U:8.3f}{a:10.5f}{b:11.5f}{g*100:9.4f}%  '
          f'{"可见(≥5%)" if g >= 0.05 else "不可见"}')

print()
print('对照：真实 cora（B1）ρ=1.749 改善 3.97%；B0 原始序 ρ=1.102 改善 1.63%')
print('T23 九张矩阵的 ρ（B1、W16、全行、A0）：cora 1.75、ogbn-arxiv 1.75、wiki-RfA 2.20、')
print('ogbn-products 2.45、reddit 3.07、dawson5 4.16、human_gene1 6.57、olafu 7.33、pattern1 13.63')
json.dump(res, open('t24_synth.json', 'w'), indent=1)
