"""RQ2 pilot evaluator (symmetric view). Research pilot only, NOT the T1 evaluator.
Reference implementation for 第一层工作区/RQ2验证实验方案.md. Pure Python: fine for Cora-size graphs,
too slow for ogbn-arxiv-size graphs (port D-greedy / P-LS / BP to C++ or numba there)."""
import json, math, subprocess, itertools, os
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
BASE = os.path.join(REPO, '第一层实验结果', 'cora-pilot-20261104') + os.sep

def load_mtx(path, selfloop=False, stats=None):
    """Matrix Market -> symmetric 0/1 adjacency (A ∪ Aᵀ), diagonal removed (A0); selfloop=True adds full diagonal (A1).
    Structure = stored pattern: every stored entry counts, including explicit zeros (2026-11-06; matches SuiteSparse
    "Pattern Entries"). If a dict is passed as `stats`, it receives entries / explicit_zeros / diagonal_entries counts."""
    with open(path) as f:
        header = f.readline().lower().split()
        pattern = 'pattern' in header
        line = f.readline()
        while line.startswith('%'): line = f.readline()
        nr, nc, _ = map(int, line.split()[:3])
        assert nr == nc, 'square matrices only'
        adj = [set() for _ in range(nr)]
        entries = zeros = diag = 0
        for line in f:
            t = line.split()
            if not t or t[0].startswith('%'): continue
            a = int(t[0]) - 1; b = int(t[1]) - 1
            entries += 1
            if not pattern and len(t) > 2 and float(t[2]) == 0.0: zeros += 1   # kept as structure, only counted
            if a == b: diag += 1; continue
            adj[a].add(b); adj[b].add(a)
    if stats is not None:
        stats.update(entries=entries, explicit_zeros=zeros, diagonal_entries=diag)
    if selfloop:
        for v in range(nr): adj[v].add(v)
    return nr, adj

def load_cora(selfloop=False):
    return load_mtx(BASE + 'neutron-matrices/cora.mtx', selfloop)

def existing_perms():
    out = {}
    for m in ['original', 'rsh', 'rabbit', 'neutron']:
        d = json.load(open(BASE + f'results-cora-pilot/cora__{m}__native.json'))
        out[m] = d['row_perm']
    return out

def runs_sorted(s):
    return (1 + sum(1 for x, y in zip(s, s[1:]) if y != x + 1)) if s else 0

def layout(order, adj, W=16, tau=None, placement='tail'):
    """Return (windows, colpos). windows: list of row lists (AIC); colpos: dict point->position."""
    n = len(order)
    if tau is None:
        kept = list(order); resid = []
    else:
        kept = [v for v in order if len(adj[v]) > tau]
        resid = [v for v in order if len(adj[v]) <= tau]
    windows = [kept[i:i + W] for i in range(0, len(kept), W)]
    if tau is None or placement == 'inplace':
        colpos = {v: i for i, v in enumerate(order)}
    else:
        colpos = {v: i for i, v in enumerate(kept + resid)}
    return windows, colpos

def evaluate(order, adj, W=16, tau=None, placement='tail'):
    windows, colpos = layout(order, adj, W, tau, placement)
    U = R = T = G = 0
    Rs = []
    for w in windows:
        cols = set().union(*(adj[v] for v in w)) if w else set()
        p = sorted(colpos[c] for c in cols)
        r = runs_sorted(p)
        U += len(p); R += r; T += math.ceil(len(p) / 16); G += len({x // W for x in p}); Rs.append(r)
    k = len(windows)
    Rs.sort()
    q = lambda f: Rs[min(len(Rs) - 1, int(f * len(Rs)))]
    return dict(k=k, U=U / k, T=T, R=R / k, G=G / k, sumU=U, sumR=R, sumG=G, p50=q(0.5), p90=q(0.9), max=Rs[-1])

# ---------- D stage (membership fixed) ----------
# Held-Karp helper is compiled into the current working directory (never into the repo)
HK = os.environ.get('RQ2_HK', os.path.join(os.getcwd(), 'rq2_hk_bin'))
if not os.path.exists(HK):
    subprocess.run(['gcc', '-O2', '-o', HK, os.path.join(HERE, 'hk.c')], check=True)

def _gv(windows, adj, n):
    Gv = [set() for _ in range(n)]
    for gi, w in enumerate(windows):
        for v in w:
            for c in adj[v]: Gv[c].add(gi)
    return Gv

class DSU:
    def __init__(s, n): s.p = list(range(n))
    def f(s, x):
        while s.p[x] != x:
            s.p[x] = s.p[s.p[x]]; x = s.p[x]
        return x
    def u(s, a, b):
        a, b = s.f(a), s.f(b)
        if a == b: return False
        s.p[a] = b; return True

def intra_exact(groups, Gv):
    inp = [str(len(groups))]
    for g in groups:
        inp.append(str(len(g)))
        for u in g: inp.append(' '.join('0' if u == v else str(len(Gv[u] & Gv[v])) for v in g))
    out = subprocess.run([HK], input='\n'.join(inp), capture_output=True, text=True).stdout.strip().split('\n')
    res = []
    for g, line in zip(groups, out):
        t = list(map(int, line.split())); res.append([g[i] for i in t[1:]])
    return res

def intra_greedy(groups, Gv):
    """cheap: greedy-edge max co path inside each group"""
    res = []
    for g in groups:
        s = len(g)
        if s <= 2: res.append(list(g)); continue
        cand = sorted(((len(Gv[g[i]] & Gv[g[j]]), i, j) for i in range(s) for j in range(i + 1, s)), reverse=True)
        deg = [0] * s; d = DSU(s); nb = defaultdict(list)
        for w, i, j in cand:
            if w <= 0: break
            if deg[i] < 2 and deg[j] < 2 and d.u(i, j):
                deg[i] += 1; deg[j] += 1; nb[i].append(j); nb[j].append(i)
        seen = set(); out = []
        for st in range(s):
            if st in seen or deg[st] == 2: continue
            prev, cur = None, st
            while cur is not None:
                seen.add(cur); out.append(g[cur])
                nx = [x for x in nb[cur] if x != prev and x not in seen]
                prev, cur = cur, (nx[0] if nx else None)
        for i in range(s):
            if i not in seen: out.append(g[i])
        res.append(out)
    return res

def intra_barycenter(groups, windows_index_of_point_neighbors):
    """sort members by mean window index of windows using them (Gv)"""
    res = []
    for g in groups:
        def key(v):
            s = windows_index_of_point_neighbors[v]
            return (sum(s) / len(s)) if s else 1e18
        res.append(sorted(g, key=key))
    return res

def inter_greedy(groups, Gv):
    k = len(groups)
    ends = [(g[0], g[-1]) for g in groups]
    # candidate port pairs with co>0: index points -> windows
    port_of = defaultdict(list)
    for a in range(k):
        for e in (0, 1):
            if e == 1 and len(groups[a]) == 1: continue
            port_of[ends[a][e]].append((a, e))
    # build co among endpoint points via windows
    win_pts = defaultdict(list)
    for p in port_of:
        for w in Gv[p]: win_pts[w].append(p)
    pair = defaultdict(int)
    for w, pts in win_pts.items():
        for x, y in itertools.combinations(sorted(set(pts)), 2): pair[(x, y)] += 1
    cand = []
    for (x, y), c in pair.items():
        for a, ea in port_of[x]:
            for b, eb in port_of[y]:
                if a != b: cand.append((c, a, ea, b, eb))
    cand.sort(reverse=True)
    used = set(); d = DSU(k); link = defaultdict(list)
    def single(a): return len(groups[a]) == 1
    for c, a, ea, b, eb in cand:
        if (a, ea) in used or (b, eb) in used: continue
        if single(a) and link[a]: continue
        if single(b) and link[b]: continue
        if not d.u(a, b): continue
        used.add((a, ea)); used.add((b, eb)); link[a].append((ea, b, eb)); link[b].append((eb, a, ea))
    seen = set(); order = []
    for st in range(k):
        if st in seen or len(link[st]) == 2: continue
        out_end = 1 if not link[st] else (1 - link[st][0][0] if not single(st) else 1)
        # out_end: the end through which we leave st; we enter from the other end
        # if st has one link at end e, we must leave via e -> traverse so that e is last
        if link[st]:
            e = link[st][0][0]
            cur_seq = groups[st] if e == 1 or single(st) else groups[st][::-1]
        else:
            cur_seq = groups[st]
        cur = st; order += cur_seq; seen.add(cur)
        while True:
            nxt = [x for x in link[cur] if x[1] not in seen]
            if not nxt: break
            ea, b, eb = nxt[0]
            seq = groups[b] if (eb == 0 or single(b)) else groups[b][::-1]
            order += seq; seen.add(b); cur = b
    for st in range(k):
        if st not in seen: order += groups[st]; seen.add(st)
    return order

def dstage(order, adj, W=16, tau=None, intra='exact', inter=True):
    """D stage on AIC windows of `order` (membership fixed). Returns new full order.
    Partitioned case: kept rows reordered, residual appended in pi order (tail placement)."""
    n = len(order)
    windows, _ = layout(order, adj, W, tau, 'tail')
    resid = [] if tau is None else [v for v in order if len(adj[v]) <= tau]
    Gv = _gv(windows, adj, n)
    if intra == 'exact': groups = intra_exact(windows, Gv)
    elif intra == 'greedy': groups = intra_greedy(windows, Gv)
    elif intra == 'bary': groups = intra_barycenter(windows, [sorted(s) for s in Gv])
    else: groups = [list(w) for w in windows]
    tail_grp = []
    if groups and len(groups[-1]) < W:   # partial window must stay last to keep membership
        tail_grp = groups[-1]; groups = groups[:-1]
    if inter: kept = inter_greedy(groups, Gv) + tail_grp
    else: kept = [v for g in groups for v in g] + tail_grp
    assert sorted(kept) == sorted(v for w in windows for v in w)
    return kept + resid
