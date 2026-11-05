import math, random, heapq
import numpy as np
from collections import defaultdict
import scipy.sparse as sp
from scipy.sparse.csgraph import reverse_cuthill_mckee, connected_components

def csr(adj):
    n = len(adj); r = []; c = []
    for v in range(n):
        for u in adj[v]: r.append(v); c.append(u)
    return sp.csr_matrix((np.ones(len(r), dtype=np.int8), (r, c)), shape=(n, n))

def rcm(adj):
    return list(reverse_cuthill_mckee(csr(adj), symmetric_mode=True))

def slashburn(adj, k=None):
    n = len(adj); k = k or max(1, int(0.005 * n))
    S = set(range(n)); front = []; back = []
    while len(S) > k:
        degS = {v: len(adj[v] & S) for v in S}
        hubs = sorted(S, key=lambda v: (-degS[v], v))[:k]
        front += hubs; S -= set(hubs)
        # components of induced subgraph
        comps = []; seen = set()
        for s in sorted(S):
            if s in seen: continue
            comp = []; stack = [s]; seen.add(s)
            while stack:
                x = stack.pop(); comp.append(x)
                for y in adj[x]:
                    if y in S and y not in seen: seen.add(y); stack.append(y)
            comps.append(comp)
        comps.sort(key=lambda c: -len(c))
        gcc = comps[0] if comps else []
        spokes = comps[1:]
        # spokes go to the back; larger components nearer the middle
        block = [v for c in spokes for v in c]
        back = block + back
        S = set(gcc)
    front += sorted(S, key=lambda v: -len(adj[v]))
    return front + back

def bp(adj, W=16, iters=20, seed=0):
    n = len(adj); rng = random.Random(seed)
    nbrs = [list(a) for a in adj]
    L2 = [0.0] + [math.log2(x) for x in range(1, n + 2)]
    def cost(d, size): return d * (L2[size] - L2[d + 1]) if d else 0.0
    def split(V):
        s = len(V)
        if s <= W: return [V]
        s1 = W * math.ceil(s / (2 * W)); s2 = s - s1
        V = V[:]; rng.shuffle(V)
        side = {}
        for i, v in enumerate(V): side[v] = 0 if i < s1 else 1
        inV = set(V)
        for it in range(iters):
            d = [defaultdict(int), defaultdict(int)]
            for v in V:
                for q in nbrs[v]: d[side[v]][q] += 1
            gains = {}
            for v in V:
                a = side[v]; b = 1 - a; na = s1 if a == 0 else s2; nb = s2 if a == 0 else s1
                g = 0.0
                for q in nbrs[v]:
                    da = d[a][q]; db = d[b][q]
                    g += cost(da, na) + cost(db, nb) - cost(da - 1, na) - cost(db + 1, nb)
                gains[v] = g
            S1 = sorted((v for v in V if side[v] == 0), key=lambda v: -gains[v])
            S2 = sorted((v for v in V if side[v] == 1), key=lambda v: -gains[v])
            moved = 0
            for x, y in zip(S1, S2):
                if gains[x] + gains[y] > 0:
                    side[x] = 1; side[y] = 0; moved += 1
                else: break
            if moved == 0: break
        A = [v for v in V if side[v] == 0]; B = [v for v in V if side[v] == 1]
        return split(A) + split(B)
    leaves = split(list(range(n)))
    return [v for leaf in leaves for v in leaf]

def gorder(adj, w=15, use_sn=True, hub_skip=True):
    n = len(adj); nbrs = [list(a) for a in adj]
    deg = np.array([len(a) for a in adj]); thr = math.sqrt(n)
    score = np.zeros(n, dtype=np.int64); placed = np.zeros(n, dtype=bool)
    order = []
    def upd(u, sgn):
        for x in nbrs[u]:
            if hub_skip and deg[x] > thr: continue
            for v in nbrs[x]: score[v] += sgn
        if use_sn:
            for v in nbrs[u]: score[v] += 2 * sgn
    start = int(np.argmax(deg))
    cur = start
    for step in range(n):
        order.append(cur); placed[cur] = True
        upd(cur, +1)
        if len(order) > w: upd(order[-w - 1], -1)
        if step == n - 1: break
        masked = np.where(placed, -1, score)
        best = int(np.argmax(masked))
        if masked[best] <= 0:
            cand = np.where(placed, -1, deg); best = int(np.argmax(cand))
        cur = best
    return order

class MemberLS:
    """swap local search on membership: minimize sumU + lam*sumGamma, exact part sizes"""
    def __init__(self, order, adj, W=16):
        self.adj = adj; n = self.n = len(adj); self.W = W
        self.groups = [list(order[i:i + W]) for i in range(0, n, W)]
        K = self.K = len(self.groups)
        self.part = np.zeros(n, dtype=np.int64)
        for p, g in enumerate(self.groups):
            for v in g: self.part[v] = p
        self.cnt = np.zeros((K, n), dtype=np.int32)
        for p, g in enumerate(self.groups):
            for v in g:
                for c in adj[v]: self.cnt[p, c] += 1
        used = self.cnt > 0
        self.U = int(used.sum())
        self.blk = np.zeros((K, K), dtype=np.int32)
        for p in range(K):
            cols = np.nonzero(used[p])[0]
            np.add.at(self.blk[p], self.part[cols], 1)
        self.G = int((self.blk > 0).sum())
    def _colmove(self, c, src, dst):
        ws = np.nonzero(self.cnt[:, c] > 0)[0]
        if len(ws) == 0: return
        b = self.blk
        before = (b[ws, src] > 0).sum() + (b[ws, dst] > 0).sum()
        b[ws, src] -= 1; b[ws, dst] += 1
        after = (b[ws, src] > 0).sum() + (b[ws, dst] > 0).sum()
        self.G += int(after - before)
    def _cntchg(self, p, c, d, skip):
        old = self.cnt[p, c]; new = old + d; self.cnt[p, c] = new
        if old == 0 and new > 0:
            self.U += 1
            if c not in skip:
                h = self.part[c]; self.blk[p, h] += 1
                if self.blk[p, h] == 1: self.G += 1
        elif old > 0 and new == 0:
            self.U -= 1
            if c not in skip:
                h = self.part[c]; self.blk[p, h] -= 1
                if self.blk[p, h] == 0: self.G -= 1
    def swap(self, u, v):
        p = int(self.part[u]); q = int(self.part[v])
        if p == q: return
        # remove column contributions of u, v
        self._colmove_remove(u); self._colmove_remove(v)
        skip = {u, v}
        for c in self.adj[u]:
            self._cntchg(p, c, -1, skip); self._cntchg(q, c, +1, skip)
        for c in self.adj[v]:
            self._cntchg(q, c, -1, skip); self._cntchg(p, c, +1, skip)
        self.part[u] = q; self.part[v] = p
        gp = self.groups[p]; gq = self.groups[q]
        gp[gp.index(u)] = v; gq[gq.index(v)] = u
        self._colmove_add(u); self._colmove_add(v)
    def _colmove_remove(self, c):
        ws = np.nonzero(self.cnt[:, c] > 0)[0]; h = self.part[c]
        if len(ws) == 0: return
        b = self.blk; before = int((b[ws, h] > 0).sum()); b[ws, h] -= 1
        self.G += int((b[ws, h] > 0).sum()) - before
    def _colmove_add(self, c):
        ws = np.nonzero(self.cnt[:, c] > 0)[0]; h = self.part[c]
        if len(ws) == 0: return
        b = self.blk; before = int((b[ws, h] > 0).sum()); b[ws, h] += 1
        self.G += int((b[ws, h] > 0).sum()) - before
    def run(self, lam=0.0, sweeps=5, cand_parts=3, seed=0, log=None):
        rng = random.Random(seed); n = self.n
        obj = lambda: self.U + lam * self.G
        for sw in range(sweeps):
            acc = 0; verts = list(range(n)); rng.shuffle(verts)
            for u in verts:
                p = int(self.part[u])
                nb = list(self.adj[u])
                if not nb: continue
                # parts whose rows already use u's columns (overlap), plus parts of u's neighbours (gamma)
                ov = self.cnt[:, nb] > 0
                score = ov.sum(axis=1).astype(float)
                score[p] = -1
                cands = list(np.argsort(-score)[:cand_parts])
                done = False
                for q in cands:
                    if score[q] <= 0: break
                    for v in list(self.groups[q]):
                        o0 = obj(); self.swap(u, v)
                        if obj() < o0 - 1e-9: acc += 1; done = True; break
                        self.swap(u, v)  # revert (swap back)
                    if done: break
            if log: log(sw, acc, self.U, self.G)
            if acc == 0: break
        return [v for g in self.groups for v in g]
