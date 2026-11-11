"""T23 step 0: pure-Python reference implementations of C2-LSH, C3-W1 / C3-W4 / C3-A (+ C3-W4 without P), C4-U, C4-T, C7-I.

Specs: 其他AI的算法调研/调研结果/第二版(补充2026文献)/candidates.md §2 (P), §4 (C2), §5 (C3), §6 (C4), §11 (C7);
候选规格补充-T20.md §0 (A0 input, empty points last). Every gap the spec leaves open is fixed here and listed in README.md
("规划方补全"); executors must reproduce these orders bit for bit on Cora before porting.

Input: adj = list of sets (A0, symmetric, no diagonal), as returned by rq2lib.load_mtx(path).
S_r = adj[r] (original column ids). Output: row_perm (new position -> old point), covering every point once,
plus a dict of diagnostics. Pure Python, research quality: fine for Cora, port for large matrices.
"""
import hashlib, math
from fractions import Fraction

W_DEFAULT = 16
K0 = 16

# ----------------------------------------------------------------------------------------------------------------
# common helpers
# ----------------------------------------------------------------------------------------------------------------
def nonempty_and_empty(adj):
    ne = [r for r in range(len(adj)) if adj[r]]
    em = [r for r in range(len(adj)) if not adj[r]]
    return ne, em

def check_perm(order, n):
    assert len(order) == n and sorted(order) == list(range(n)), 'not a permutation'
    return order

def postprocess_P(groups, W=W_DEFAULT, complete_order=None):
    """candidates.md §2 'C2/C3 共用短组后处理 P'.
    groups: row lists in generation order; complete_order: optional generation order of the complete (size W) groups,
    as indices into `groups` (default: their order in `groups`). Returns (flat order without empty points, stats).
    Planner completions (README §2): for each target (short groups sorted size desc, min row asc) the other remaining
    short groups are scanned in (size asc, min row asc) order and merged whole while the sum stays <= W; the scan stops
    when the target reaches W; an absorbed group is never a target; every group is emitted with rows ascending."""
    assert all(0 < len(g) <= W for g in groups)
    full_idx = [i for i, g in enumerate(groups) if len(g) == W]
    if complete_order is not None:
        assert sorted(complete_order) == sorted(full_idx); full_idx = list(complete_order)
    full_groups = [sorted(groups[i]) for i in full_idx]
    short = sorted((sorted(g) for g in groups if len(g) < W), key=lambda g: (-len(g), g[0]))
    n_short_before = len(short)
    absorbed = [False] * len(short)
    new_full, remaining, merges = [], [], 0
    for t in range(len(short)):
        if absorbed[t]: continue
        absorbed[t] = True
        target = list(short[t])
        cands = sorted((i for i in range(len(short)) if not absorbed[i]), key=lambda i: (len(short[i]), short[i][0]))
        for i in cands:
            if len(target) + len(short[i]) <= W:
                target += short[i]; absorbed[i] = True; merges += 1
                if len(target) == W: break
        (new_full if len(target) == W else remaining).append(sorted(target))
    remaining.sort(key=lambda g: (-len(g), g[0]))
    out_groups = full_groups + new_full + remaining
    flat = [v for g in out_groups for v in g]
    # cut count: groups (after P) that span more than one W-row evaluation window
    cuts, pos = 0, 0
    for g in out_groups:
        if pos // W != (pos + len(g) - 1) // W: cuts += 1
        pos += len(g)
    stats = dict(groups_full_before=len(full_groups), short_before=n_short_before, P_merges=merges,
                 P_new_full=len(new_full), short_after=len(remaining), groups_cut_by_windows=cuts)
    return flat, stats


def flatten_no_P(groups):
    """C3-W4 ablation: groups in generation order, rows ascending within a group (README §2)."""
    return [v for g in groups for v in sorted(g)]

# ----------------------------------------------------------------------------------------------------------------
# C2-LSH (candidates.md §4)
# ----------------------------------------------------------------------------------------------------------------
MERSENNE61 = (1 << 61) - 1

def _minhash_params(num_perm=128, seed=0):
    """Deterministic, platform-independent hash parameters (README §3): a_k, b_k from SHA-256."""
    ps = []
    for k in range(num_perm):
        a = int.from_bytes(hashlib.sha256(f'C2-LSH|seed={seed}|k={k}|a'.encode()).digest()[:8], 'big') % (MERSENNE61 - 1) + 1
        b = int.from_bytes(hashlib.sha256(f'C2-LSH|seed={seed}|k={k}|b'.encode()).digest()[:8], 'big') % MERSENNE61
        ps.append((a, b))
    return ps

def minhash_signature(S, params):
    return tuple(min(((a * (x + 1) + b) % MERSENNE61) for x in S) for a, b in params)

def c2_lsh(adj, W=W_DEFAULT, num_perm=128, bands=32, rows_per_band=4, j_min=Fraction(1, 5), seed=0):
    assert bands * rows_per_band == num_perm
    n = len(adj); ne, em = nonempty_and_empty(adj)
    params = _minhash_params(num_perm, seed)
    sig = {r: minhash_signature(adj[r], params) for r in ne}
    buckets = {}
    for r in ne:                       # ne is ascending, so each bucket list is ascending
        s = sig[r]
        for j in range(bands):
            buckets.setdefault((j, s[j * rows_per_band:(j + 1) * rows_per_band]), []).append(r)
    pairs = set()
    for rows in buckets.values():
        for i in range(len(rows)):
            for k in range(i + 1, len(rows)):
                pairs.add((rows[i], rows[k]))
    cand = []
    for r, s in pairs:
        inter = len(adj[r] & adj[s]); union = len(adj[r]) + len(adj[s]) - inter
        J = Fraction(inter, union)
        if J >= j_min: cand.append((-J, r, s))
    cand.sort()
    parent = {r: r for r in ne}; members = {r: [r] for r in ne}; completed = []
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    merged = rejected_capacity = 0
    for _, r, s in cand:
        a, b = find(r), find(s)
        if a == b: continue
        if len(members[a]) + len(members[b]) > W: rejected_capacity += 1; continue
        if (len(members[a]), a) < (len(members[b]), b): a, b = b, a     # union by size, deterministic
        parent[b] = a; members[a] += members.pop(b); merged += 1
        if len(members[a]) == W: completed.append(a)
    roots = sorted(members, key=lambda x: min(members[x]))          # generation order of non-complete groups: min row
    groups = [members[x] for x in completed] + [members[x] for x in roots if x not in set(completed)]
    flat, st = postprocess_P(groups, W, complete_order=list(range(len(completed))))
    order = check_perm(flat + em, n)
    st.update(candidate_pairs_lsh=len(pairs), candidate_pairs_kept=len(cand), merges=merged,
              rejected_capacity=rejected_capacity, buckets=len(buckets))
    return order, st

# ----------------------------------------------------------------------------------------------------------------
# C3 (candidates.md §5): BlockSmith-style signature width b and online clustering
# ----------------------------------------------------------------------------------------------------------------
def c3_width_adaptive(shape):
    D = max(shape)
    return 4 if D < 50000 else (32 if D < 100000 else 128)

def c3(adj, b, W=W_DEFAULT, use_P=True, shape=None):
    n = len(adj); ne, em = nonempty_and_empty(adj)
    F = {r: frozenset(j // b for j in adj[r]) for r in ne}
    groups = []          # generation (creation) order; each: dict(rep=row, F=sig, rows=[...])
    active = []          # indices into groups with size < W
    comparisons = 0
    for r in ne:
        fr = F[r]; chosen = None
        for gi in sorted(active, key=lambda i: (-len(groups[i]['rows']), groups[i]['rep'])):
            comparisons += 1
            fg = groups[gi]['F']; inter = len(fr & fg); union = len(fr) + len(fg) - inter
            if 5 * inter >= union:                 # Jaccard distance <= 0.8  <=>  J >= 0.2 (exact)
                chosen = gi; break
        if chosen is None:
            groups.append(dict(rep=r, F=fr, rows=[r])); chosen = len(groups) - 1; active.append(chosen)
        else:
            groups[chosen]['rows'].append(r)
        if len(groups[chosen]['rows']) == W: active.remove(chosen)
    rows = [g['rows'] for g in groups]
    if use_P: flat, st = postprocess_P(rows, W)
    else:
        flat = flatten_no_P(rows)
        st = dict(groups_full_before=sum(len(g) == W for g in rows), short_before=sum(len(g) < W for g in rows), P='off')
    order = check_perm(flat + em, n)
    st.update(b=b, groups=len(rows), comparisons=comparisons)
    return order, st

# ----------------------------------------------------------------------------------------------------------------
# C4 (candidates.md §6) and C7-I (§11): bounded-pool greedy
# ----------------------------------------------------------------------------------------------------------------
def _pool_greedy(adj, score, W=W_DEFAULT, L=128):
    """score(z_new, U_new, inter, rowlen) -> comparable key (larger is better); ties: longer row, then smaller id."""
    n = len(adj); ne, em = nonempty_and_empty(adj)
    seq = sorted(ne, key=lambda r: (min(adj[r]), r))
    assigned = set(); groups = []; evals = 0; ptr = 0
    while True:
        while ptr < len(seq) and seq[ptr] in assigned: ptr += 1
        if ptr >= len(seq): break
        pool = []
        i = ptr
        while i < len(seq) and len(pool) < L:
            if seq[i] not in assigned: pool.append(seq[i])
            i += 1
        seed = pool[0]
        grp = [seed]; assigned.add(seed); Uset = set(adj[seed]); z = len(adj[seed])
        while len(grp) < W:
            best = None
            for r in pool:
                if r in assigned: continue
                evals += 1
                Sr = adj[r]; inter = len(Sr & Uset); Unew = len(Uset) + len(Sr) - inter
                key = (score(z + len(Sr), Unew, inter, len(Sr)), len(Sr), -r)
                if best is None or key > best[0]: best = (key, r)
            if best is None: break                 # pool exhausted (only near the end of the input)
            r = best[1]; grp.append(r); assigned.add(r); Uset |= adj[r]; z += len(adj[r])
        groups.append(grp)
    order = check_perm([v for g in groups for v in g] + em, n)
    return order, dict(groups=len(groups), short_groups=sum(len(g) < W for g in groups), score_evaluations=evals, L=L)

def c4(adj, variant, W=W_DEFAULT, L=128, K=K0):
    if variant == 'U':
        score = lambda z, U, inter, ln: Fraction(z, U)
    elif variant == 'T':
        score = lambda z, U, inter, ln: Fraction(z, W * K * math.ceil(U / K))
    else:
        raise ValueError(variant)
    return _pool_greedy(adj, score, W, L)

def c7_i(adj, W=W_DEFAULT, L=128):
    return _pool_greedy(adj, lambda z, U, inter, ln: inter, W, L)

# ----------------------------------------------------------------------------------------------------------------
CANDIDATES = {
    'C2-LSH':    lambda adj: c2_lsh(adj),
    'C3-W1':     lambda adj: c3(adj, 1),
    'C3-W4':     lambda adj: c3(adj, 4),
    'C3-A':      lambda adj: c3(adj, c3_width_adaptive((len(adj), len(adj)))),
    'C3-W4-noP': lambda adj: c3(adj, 4, use_P=False),
    'C4-U':      lambda adj: c4(adj, 'U'),
    'C4-T':      lambda adj: c4(adj, 'T'),
    'C7-I':      lambda adj: c7_i(adj),
}
