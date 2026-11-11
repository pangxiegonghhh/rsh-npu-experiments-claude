# T24 补强：每个窗口枚举全部 2^16 个「移出子集」，取 (c, Z) 的完整帕累托前沿，
# 从而给出行粒度的**真正最优**（贪心菜单只是其子集，只能给下界）。
# 用法：python3 -I -B t24_exact_menu.py <仓库根目录>
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

def pareto_menu(rows):
    """枚举所有保留子集，返回 {c: 最小 Z} 的帕累托前沿（c=剩余列并集大小，Z=移出行的非零和）"""
    m = len(rows)
    cols = sorted(set().union(*rows)) if rows else []
    idx = {c: i for i, c in enumerate(cols)}
    cmask = [0] * m; nz = [0] * m
    for i, cs in enumerate(rows):
        b = 0
        for c in cs: b |= 1 << idx[c]
        cmask[i] = b; nz[i] = len(cs)
    total = sum(nz)
    size = 1 << m
    orv = [0] * size; snz = [0] * size
    for mask in range(1, size):
        lb = mask & -mask; i = lb.bit_length() - 1; prev = mask ^ lb
        orv[mask] = orv[prev] | cmask[i]; snz[mask] = snz[prev] + nz[i]
    best = {}
    for mask in range(size):
        c = bin(orv[mask]).count('1'); Z = total - snz[mask]
        if c not in best or Z < best[c]: best[c] = Z
    # 帕累托化：c 增大时 Z 必须严格减小
    out = []
    bz = INF
    for c in sorted(best):
        if best[c] < bz: out.append((c, best[c])); bz = best[c]
    return out

menus_ex = []
for k, rs in enumerate(windows):
    menus_ex.append(pareto_menu(rs))
sizes = [len(m) for m in menus_ex]
print(f'完整帕累托菜单：窗口 {len(menus_ex)} 个，菜单项数 最小 {min(sizes)} 中位 {sorted(sizes)[len(sizes)//2]} 最大 {max(sizes)}')

# 贪心菜单（与主脚本同法）作对照
def greedy_menu(rows):
    cnt = defaultdict(int)
    for cs in rows:
        for c in cs: cnt[c] += 1
    alive = set(range(len(rows))); out = [(len(cnt), 0)]; curZ = 0
    while alive:
        best = None
        for i in alive:
            nzi = len(rows[i]); dU = sum(1 for c in rows[i] if cnt[c] == 1)
            r = -1.0 if nzi == 0 else dU / nzi
            if best is None or r > best[0] or (r == best[0] and i < best[1]): best = (r, i, dU, nzi)
        _, i, dU, nzi = best
        alive.discard(i)
        for c in rows[i]:
            cnt[c] -= 1
            if cnt[c] == 0: del cnt[c]
        curZ += nzi; out.append((len(cnt), curZ))
    return out
menus_gr = [greedy_menu(rs) for rs in windows]
whole = [[m[0], m[-1]] for m in menus_gr]

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

ms_w = solve(whole); ms_g = solve(menus_gr); ms_e = solve(menus_ex)
print()
print(f"{'方案':30}{'makespan':>11}{'相对整窗':>11}")
print('-' * 52)
print(f"{'整窗最优':30}{ms_w:11.5f}{'—':>11}")
print(f"{'行粒度（贪心菜单）':30}{ms_g:11.5f}{(1-ms_g/ms_w)*100:10.4f}%")
print(f"{'行粒度（全部 2^16 子集，真最优）':30}{ms_e:11.5f}{(1-ms_e/ms_w)*100:10.4f}%")
print()
print(f'>>> 行粒度真最优相对整窗的改善 = {(1-ms_e/ms_w)*100:.4f}%  '
      f'预登记判据 ≥5% -> {"可见" if (1-ms_e/ms_w) >= 0.05 else "不可见"}')
print(f'    贪心菜单低估了 {(ms_g-ms_e)/ms_w*100:.4f} 个百分点')

print()
print('α/β 敏感性（真最优菜单）')
print(f"{'倍数':>7}{'α/β':>9}{'整窗':>10}{'行粒度':>11}{'改善':>9}")
sens = []
for mult in [0.86, 1.00, 1.28, 2.57, 3.42, 5.14]:
    ratio = (ALPHA / BETA) * mult; beta = ALPHA / ratio
    a = solve(whole, ALPHA, beta); b = solve(menus_ex, ALPHA, beta)
    sens.append((mult, ratio, a, b, 1 - b / a))
    print(f'{mult:7.2f}{ratio:9.3f}{a:10.5f}{b:11.5f}{(1-b/a)*100:8.4f}%')
mx = max(s[4] for s in sens)
print(f'>>> 在 α/β 的 0.86–5.14 倍全范围内，改善最大 {mx*100:.4f}%，始终 < 5%')

json.dump(dict(ms_whole=ms_w, ms_greedy=ms_g, ms_exact=ms_e,
               gain_greedy=1 - ms_g / ms_w, gain_exact=1 - ms_e / ms_w,
               menu_sizes=dict(min=min(sizes), med=sorted(sizes)[len(sizes) // 2], max=max(sizes)),
               sens=[dict(mult=m, ratio=r, whole=a, fine=b, gain=g) for m, r, a, b, g in sens],
               max_gain_over_sens=mx), open('t24_exact.json', 'w'), indent=1)
