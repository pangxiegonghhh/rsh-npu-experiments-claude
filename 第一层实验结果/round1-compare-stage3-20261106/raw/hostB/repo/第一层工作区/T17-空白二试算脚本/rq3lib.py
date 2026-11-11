"""RQ3 (blank 2, E stage) pilot: partition-aware reordering. Research pilot only, NOT the T1 evaluator.
Reference implementation for 第一层工作区/RQ3验证实验方案.md (T22). Builds on 第一层工作区/T17-空白一试算脚本 (rq2lib).
All layouts are explicit:
  windows = list of AIC row groups (each <= W rows); sigma = final numbering of all n points (sigma[pos] = point).
The residual set D is always passed explicitly (A0 degree <= tau), so A1 evaluation uses the same D.
Pure Python: fine for Cora, too slow for ogbn-arxiv-size graphs (port co_chain / inter_greedy2 / P-LS there).
"""
import math, os, sys, itertools, random
from collections import defaultdict
import numpy as np

sys.dont_write_bytecode = True   # keep the repo clean
HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(os.path.dirname(HERE), 'T17-空白一试算脚本')                       # rq2lib, methods, memberls_part
PILOT = os.path.join(os.path.dirname(os.path.dirname(HERE)), '第一层实验结果', 'cora-pilot-20261104')
for p in (REF, PILOT):
    if p not in sys.path: sys.path.insert(0, p)
from rq2lib import intra_greedy, intra_exact, inter_greedy, _gv, DSU   # noqa: E402

def runs_sorted(p):
    return (1 + sum(1 for x, y in zip(p, p[1:]) if y != x + 1)) if p else 0

def chunks(seq, W=16, offset=0):
    seq = list(seq)
    out = [seq[:offset]] if offset else []
    out += [seq[i:i + W] for i in range(offset, len(seq), W)]
    return [w for w in out if w]

def resid_set(adj0, tau):
    return set(v for v in range(len(adj0)) if len(adj0[v]) <= tau)

def win_metrics(windows, adj, sigma=None, W=16):
    """U, T over windows; if sigma given also R, Gamma(=distinct pos//W), write runs of window rows."""
    pos = None
    if sigma is not None:
        pos = np.empty(len(sigma), dtype=np.int64); pos[np.array(sigma)] = np.arange(len(sigma))
    U = T = R = G = WR = 0; Rs = []
    for w in windows:
        cols = set().union(*(adj[v] for v in w))
        U += len(cols); T += math.ceil(len(cols) / 16)
        if pos is not None:
            p = sorted(int(pos[c]) for c in cols)
            r = runs_sorted(p); R += r; Rs.append(r)
            G += len({x // W for x in p})
            WR += runs_sorted(sorted(int(pos[v]) for v in w))
    k = len(windows)
    d = dict(k=k, sumU=U, U=U / k, T=T)
    if pos is not None:
        Rs.sort()
        d.update(sumR=R, R=R / k, G=G / k, write_runs_aic=WR,
                 p90=Rs[min(k - 1, int(0.9 * k))], max=Rs[-1])
    return d

def resid_write_runs(sigma, D):
    pos = {v: i for i, v in enumerate(sigma)}
    return runs_sorted(sorted(pos[v] for v in D)) if D else 0

# ---------------- four numbers (skeleton §4.2 RQ3) ----------------
def four_numbers(order, adj, D, W=16):
    """T_full, T_inplace, T_keep for order (all points) and residual set D (no reorder)."""
    full = chunks(order, W)
    inpl = [[v for v in w if v not in D] for w in full]; inpl = [w for w in inpl if w]
    keep = chunks([v for v in order if v not in D], W)
    f = win_metrics(full, adj); i = win_metrics(inpl, adj); k = win_metrics(keep, adj)
    return dict(T_full=f['T'], U_full=f['sumU'], k_full=f['k'],
                T_inplace=i['T'], U_inplace=i['sumU'], k_inplace=i['k'],
                T_keep=k['T'], U_keep=k['sumU'], k_keep=k['k'])

def phase_T(order, adj, W=16):
    """mean T over cut offsets 1..W-1 (no rows removed): sensitivity of an order to the exact window cut."""
    ts = [win_metrics(chunks(order, W, s), adj)['T'] for s in range(1, W)]
    us = [win_metrics(chunks(order, W, s), adj)['sumU'] for s in range(1, W)]
    return sum(ts) / len(ts), sum(us) / len(us)

# ---------------- placements of residual points (P10 and new) ----------------
def place_tail(korder, D_in_pi):
    return list(korder) + list(D_in_pi)

def place_inplace(korder, pi, D):
    """D keep their positions in pi; kept points fill the other slots in korder order."""
    it = iter(korder); out = []
    for v in pi:
        out.append(v if v in D else next(it))
    return out

def co_chain(points, Gv):
    """greedy-edge max-co chain over `points` (TSP greedy-edge); co = |Gv[x] & Gv[y]|"""
    pts = list(points); idx = {v: i for i, v in enumerate(pts)}
    by_win = defaultdict(list)
    for v in pts:
        for w in Gv[v]: by_win[w].append(v)
    pair = defaultdict(int)
    for w, vs in by_win.items():
        if len(vs) > 400: continue   # guard; never hit on Cora residual sets
        for x, y in itertools.combinations(sorted(vs), 2): pair[(x, y)] += 1
    cand = sorted(((c, x, y) for (x, y), c in pair.items()), reverse=True)
    deg = defaultdict(int); d = DSU(len(pts)); nb = defaultdict(list)
    for c, x, y in cand:
        if deg[x] < 2 and deg[y] < 2 and d.u(idx[x], idx[y]):
            deg[x] += 1; deg[y] += 1; nb[x].append(y); nb[y].append(x)
    seen = set(); out = []
    # chains: start from endpoints; order chains by first appearance in `points`
    for s in pts:
        if s in seen or deg[s] == 2: continue
        prev, cur = None, s
        while cur is not None:
            seen.add(cur); out.append(cur)
            nx = [x for x in nb[cur] if x != prev and x not in seen]
            prev, cur = cur, (nx[0] if nx else None)
    for s in pts:
        if s not in seen: out.append(s)
    return out

def dstage_groups(windows, adj, n, intra='greedy'):
    """D-greedy on AIC windows (membership fixed); returns ordered list of groups (each a list), partial last group kept last."""
    Gv = _gv(windows, adj, n)
    groups = intra_greedy(windows, Gv) if intra == 'greedy' else intra_exact(windows, Gv)
    return groups, Gv

def inter_greedy2(groups, Gv):
    """Inter-group greedy linking where singleton groups (residual points) have two ports, so they can sit between
    two AIC groups. Same greedy-edge rule as rq2lib.inter_greedy (co from largest, no cycles, whole-group flips)."""
    k = len(groups)
    port_of = defaultdict(list)
    for a, g in enumerate(groups):
        port_of[g[0]].append((a, 0)); port_of[g[-1]].append((a, 1))
    win_pts = defaultdict(set)
    for p in port_of:
        for w in Gv[p]: win_pts[w].add(p)
    pair = defaultdict(int)
    for w, pts in win_pts.items():
        for x, y in itertools.combinations(sorted(pts), 2): pair[(x, y)] += 1
    cand = []
    for (x, y), c in pair.items():
        for a, ea in port_of[x]:
            for b, eb in port_of[y]:
                if a != b: cand.append((c, a, ea, b, eb))
    cand.sort(reverse=True)
    used = set(); d = DSU(k); link = defaultdict(dict)
    for c, a, ea, b, eb in cand:
        if (a, ea) in used or (b, eb) in used: continue
        if not d.u(a, b): continue
        used.add((a, ea)); used.add((b, eb)); link[a][ea] = (b, eb); link[b][eb] = (a, ea)
    seen = set(); order = []
    for st in range(k):
        if st in seen or len(link[st]) == 2: continue
        if link[st]:
            e = next(iter(link[st]))
            seq = groups[st] if e == 1 else groups[st][::-1]
        else:
            e = None; seq = groups[st]
        order += seq; seen.add(st); cur, out_port = st, e
        while out_port is not None and out_port in link[cur]:
            b, eb = link[cur][out_port]
            if b in seen: break
            order += groups[b] if eb == 0 else groups[b][::-1]
            seen.add(b); cur, out_port = b, 1 - eb
    for st in range(k):
        if st not in seen: order += groups[st]; seen.add(st)
    return order

def layout_D(windows, adj, n, D_in_pi, rule='tail', W=16, pi=None, intra='greedy'):
    """D stage on AIC windows + residual placement rule. Returns sigma.
    rules: tail (P10), tail-co (tail, residual region ordered by co chain), gap (residual points are singleton clusters
    that inter-group greedy may put between AIC groups; AIC groups stay contiguous), inplace (P10, D at pi positions)."""
    groups, Gv = dstage_groups(windows, adj, n, intra)
    tail_grp = []
    if groups and len(groups[-1]) < W:
        tail_grp = groups[-1]; groups = groups[:-1]
    if rule == 'gap':
        allg = groups + [[v] for v in D_in_pi]
        korder = inter_greedy2(allg, Gv) + tail_grp
        return korder
    korder = inter_greedy(groups, Gv) + tail_grp
    if rule == 'snap':
        # inplace snapped to window boundaries: each residual point follows the AIC window that holds the last kept
        # row before it in pi (points before the first kept row go with the first window); AIC windows stay contiguous
        Dset = set(D_in_pi); win_of = {}
        for gi, w in enumerate(windows):
            for v in w: win_of[v] = gi
        owner = defaultdict(list); last = windows[0][0]
        for v in pi:
            if v in Dset: owner[win_of[last]].append(v)
            else: last = v
        # walk korder window by window (korder is a concatenation of whole windows)
        out = []; i = 0
        while i < len(korder):
            gi = win_of[korder[i]]; sz = len(windows[gi])
            out += korder[i:i + sz] + owner[gi]; i += sz
        return out
    if rule == 'tail': return korder + list(D_in_pi)
    if rule == 'tail-co': return korder + co_chain(D_in_pi, Gv)
    if rule == 'inplace': return place_inplace(korder, pi, set(D_in_pi))
    raise ValueError(rule)

# ---------------- reruns on the kept rows (T(pi')) ----------------
def gorder_sub(adj, K, w=15, use_sn=True, hub_skip=True):
    """Gorder on rows K x all columns: S_s via shared columns (incl. residual columns), S_n via kept-kept adjacency."""
    K = list(K); Kset = set(K); n = len(adj)
    rows_of = [[v for v in adj[x] if v in Kset] for x in range(n)]
    deg = {v: len(adj[v]) for v in K}; thr = math.sqrt(len(K))
    score = defaultdict(int); placed = set(); order = []
    def upd(u, sgn):
        for x in adj[u]:
            if hub_skip and len(rows_of[x]) > thr: continue
            for v in rows_of[x]: score[v] += sgn
        if use_sn:
            for v in adj[u]:
                if v in Kset: score[v] += 2 * sgn
    cur = max(K, key=lambda v: (deg[v], -v))
    for step in range(len(K)):
        order.append(cur); placed.add(cur); upd(cur, +1)
        if len(order) > w: upd(order[-w - 1], -1)
        if step == len(K) - 1: break
        best = None; bs = 0
        for v, s in score.items():
            if v not in placed and (s > bs or (s == bs and best is not None and v < best)):
                if s > 0: best, bs = v, s
        if best is None:
            best = max((v for v in K if v not in placed), key=lambda v: (deg[v], -v))
        cur = best
    return order

def bp_sub(adj, K, W=16, iters=20, seed=0):
    """C10-BP with data vertices = K, queries = all columns."""
    n = len(adj); rng = random.Random(seed)
    L2 = [0.0] + [math.log2(x) for x in range(1, n + 2)]
    def cost(d, size): return d * (L2[size] - L2[d + 1]) if d else 0.0
    def split(V):
        s = len(V)
        if s <= W: return [V]
        s1 = W * math.ceil(s / (2 * W)); s2 = s - s1
        V = V[:]; rng.shuffle(V)
        side = {v: (0 if i < s1 else 1) for i, v in enumerate(V)}
        for it in range(iters):
            d = [defaultdict(int), defaultdict(int)]
            for v in V:
                for q in adj[v]: d[side[v]][q] += 1
            gains = {}
            for v in V:
                a = side[v]; b = 1 - a; na = s1 if a == 0 else s2; nb = s2 if a == 0 else s1
                g = 0.0
                for q in adj[v]:
                    da = d[a][q]; db = d[b][q]
                    g += cost(da, na) + cost(db, nb) - cost(da - 1, na) - cost(db + 1, nb)
                gains[v] = g
            S1 = sorted((v for v in V if side[v] == 0), key=lambda v: -gains[v])
            S2 = sorted((v for v in V if side[v] == 1), key=lambda v: -gains[v])
            moved = 0
            for x, y in zip(S1, S2):
                if gains[x] + gains[y] > 0: side[x] = 1; side[y] = 0; moved += 1
                else: break
            if moved == 0: break
        return split([v for v in V if side[v] == 0]) + split([v for v in V if side[v] == 1])
    return [v for leaf in split(sorted(K)) for v in leaf]

def induced(adj, K):
    K = sorted(K); idx = {v: i for i, v in enumerate(K)}
    return K, [set(idx[u] for u in adj[v] if u in idx) for v in K]

def pilot_sub(adj, K, which):
    """rerun the Cora-pilot rsh / rabbit / neutron implementation on rows K x all columns"""
    import rsh_reorder_experiment as pil
    K = sorted(K)
    M = pil.SparseMatrix.from_rows([sorted(adj[v]) for v in K], n_cols=len(adj))
    if which == 'rsh': o = pil.rsh_reorder(M, k=8, weighted_alpha=0.0, refine_passes=2)[0]
    elif which == 'rabbit': o = pil.rabbit_reorder(M)[0]
    elif which == 'neutron': o = pil.neutron_reorder(M, w16=16, cluster_windows=8)[0]
    return [K[i] for i in o]
