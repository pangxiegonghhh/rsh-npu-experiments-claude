#!/usr/bin/env python3
"""Independent re-implementation of the T23 step-0 candidates (written separately from t23_candidates.py, different data
structures, integer cross-multiplication instead of Fraction). Used only to cross-check the reference orders.

usage: python3 -I indep_t23.py <cora.mtx> <orders_t23.json>     exit 0 = every order identical, 1 = mismatch
The MTX reader here is its own (A0: symmetric, diagonal dropped, explicit zeros kept as structure).
"""
import sys, json, hashlib, math
from functools import cmp_to_key

def read_a0(path):
    with open(path) as f:
        line = f.readline()
        while line.startswith('%'): line = f.readline()
        n = int(line.split()[0])
        nb = [set() for _ in range(n)]
        for line in f:
            p = line.split()
            if len(p) < 2 or p[0].startswith('%'): continue
            i, j = int(p[0]) - 1, int(p[1]) - 1
            if i != j: nb[i].add(j); nb[j].add(i)
    return nb

W, K0, L = 16, 16, 128

def shortfix(groups_gen, full_gen_idx=None):
    """P with list-of-tuples bookkeeping."""
    full = [g for g in groups_gen if len(g) == W] if full_gen_idx is None else [groups_gen[i] for i in full_gen_idx]
    pool = [sorted(g) for g in groups_gen if len(g) < W]
    pool.sort(key=lambda g: (-len(g), g[0]))
    used = set(); made_full = []; left = []
    for ti, tg in enumerate(pool):
        if ti in used: continue
        used.add(ti); cur = list(tg)
        order = sorted([i for i in range(len(pool)) if i not in used], key=lambda i: (len(pool[i]), pool[i][0]))
        for i in order:
            if len(cur) == W: break
            if len(cur) + len(pool[i]) <= W:
                cur.extend(pool[i]); used.add(i)
        (made_full if len(cur) == W else left).append(sorted(cur))
    left.sort(key=lambda g: (-len(g), g[0]))
    return [x for g in [sorted(g) for g in full] + made_full + left for x in g]

P61 = 2 ** 61 - 1
def params():
    out = []
    for k in range(128):
        ha = hashlib.sha256(('C2-LSH|seed=0|k=%d|a' % k).encode()).digest()
        hb = hashlib.sha256(('C2-LSH|seed=0|k=%d|b' % k).encode()).digest()
        out.append((int.from_bytes(ha[:8], 'big') % (P61 - 1) + 1, int.from_bytes(hb[:8], 'big') % P61))
    return out

def c2(nb):
    n = len(nb); rows = [r for r in range(n) if nb[r]]; prm = params()
    sigs = {}
    for r in rows:
        vals = [P61] * 128
        for x in nb[r]:
            for k, (a, b) in enumerate(prm):
                h = (a * (x + 1) + b) % P61
                if h < vals[k]: vals[k] = h
        sigs[r] = vals
    seen = set()
    for band in range(32):
        tab = {}
        for r in rows: tab.setdefault(tuple(sigs[r][4 * band:4 * band + 4]), []).append(r)
        for members in tab.values():
            for x in range(len(members)):
                for y in range(x + 1, len(members)):
                    seen.add((members[x], members[y]))
    cands = []
    for r, s in seen:
        i = len(nb[r] & nb[s]); u = len(nb[r] | nb[s])
        if 5 * i >= u: cands.append((i, u, r, s))
    def cmp(p, q):
        lhs, rhs = p[0] * q[1], q[0] * p[1]          # compare J_p vs J_q
        if lhs != rhs: return -1 if lhs > rhs else 1
        return -1 if (p[2], p[3]) < (q[2], q[3]) else (1 if (p[2], p[3]) > (q[2], q[3]) else 0)
    cands.sort(key=cmp_to_key(cmp))
    label = {r: r for r in rows}; grp = {r: {r} for r in rows}; done = []
    for _, _, r, s in cands:
        a, b = label[r], label[s]
        if a == b or len(grp[a]) + len(grp[b]) > W: continue
        if len(grp[a]) < len(grp[b]) or (len(grp[a]) == len(grp[b]) and a < b): a, b = b, a
        for v in grp[b]: label[v] = a
        grp[a] |= grp.pop(b)
        if len(grp[a]) == W: done.append(a)
    gens = [sorted(grp[a]) for a in done] + [sorted(grp[a]) for a in grp if a not in set(done)]
    return shortfix(gens, list(range(len(done)))) + [r for r in range(n) if not nb[r]]

def c3(nb, b, with_p=True):
    n = len(nb); made = []    # [rep, sig, rows]
    for r in range(n):
        if not nb[r]: continue
        sig = {j // b for j in nb[r]}; placed = False
        act = [g for g in made if len(g[2]) < W]
        act.sort(key=lambda g: (-len(g[2]), g[0]))
        for g in act:
            i = len(sig & g[1]); u = len(sig | g[1])
            if 5 * i >= u: g[2].append(r); placed = True; break
        if not placed: made.append([r, sig, [r]])
    gens = [g[2] for g in made]
    flat = shortfix(gens) if with_p else [x for g in gens for x in sorted(g)]
    return flat + [r for r in range(n) if not nb[r]]

def greedy_pool(nb, better):
    n = len(nb); seq = sorted([r for r in range(n) if nb[r]], key=lambda r: (min(nb[r]), r))
    taken = [False] * n; out = []
    for start in seq:
        if taken[start]: continue
        pool = []
        for r in seq:
            if not taken[r]: pool.append(r)
            if len(pool) == L: break
        grp = [pool[0]]; taken[pool[0]] = True; cols = set(nb[pool[0]]); z = len(nb[pool[0]])
        while len(grp) < W:
            best = None
            for r in pool:
                if taken[r]: continue
                inter = len(nb[r] & cols); cand = (z + len(nb[r]), len(cols) + len(nb[r]) - inter, inter, len(nb[r]), r)
                if best is None or better(cand, best): best = cand
            if best is None: break
            r = best[4]; grp.append(r); taken[r] = True; cols |= nb[r]; z += len(nb[r])
        out += grp
    return out + [r for r in range(n) if not nb[r]]

def tie(c, d):                       # longer row, then smaller id
    return c[3] > d[3] or (c[3] == d[3] and c[4] < d[4])
def better_U(c, d):
    lhs, rhs = c[0] * d[1], d[0] * c[1]
    return lhs > rhs or (lhs == rhs and tie(c, d))
def better_T(c, d):
    dc, dd = W * K0 * math.ceil(c[1] / K0), W * K0 * math.ceil(d[1] / K0)
    lhs, rhs = c[0] * dd, d[0] * dc
    return lhs > rhs or (lhs == rhs and tie(c, d))
def better_I(c, d):
    return c[2] > d[2] or (c[2] == d[2] and tie(c, d))

def main():
    nb = read_a0(sys.argv[1]); ref = json.load(open(sys.argv[2]))
    mine = {'C2-LSH': c2(nb), 'C3-W1': c3(nb, 1), 'C3-W4': c3(nb, 4), 'C3-A': c3(nb, 4 if len(nb) < 50000 else (32 if len(nb) < 100000 else 128)),
            'C3-W4-noP': c3(nb, 4, False), 'C4-U': greedy_pool(nb, better_U), 'C4-T': greedy_pool(nb, better_T), 'C7-I': greedy_pool(nb, better_I)}
    ok = True
    for k, o in mine.items():
        same = o == ref.get(k); ok &= same
        print(k, 'IDENTICAL' if same else 'DIFFERENT', hashlib.sha256(json.dumps(o).encode()).hexdigest()[:16])
    print('T23 independent check:', 'OK' if ok else 'FAILED')
    sys.exit(0 if ok else 1)

if __name__ == '__main__':
    main()
