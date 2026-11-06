import numpy as np, random
from methods import MemberLS
class MemberLSPart(MemberLS):
    """membership LS on post-partition AIC windows; residual points fixed at tail blocks"""
    def __init__(self, order, adj, tau, W=16):
        self.adj = adj; n = self.n = len(adj); self.W = W
        kept = [v for v in order if len(adj[v]) > tau]
        resid = [v for v in order if len(adj[v]) <= tau]
        self.groups = [kept[i:i + W] for i in range(0, len(kept), W)]
        self.resid = resid
        K = self.K = len(self.groups)
        nb_tail = (len(resid) + W - 1) // W
        # blocks are positions//W in layout kept+resid; kept groups align with blocks 0..K-1 only if len(kept)%W==0
        self.part = np.zeros(n, dtype=np.int64)
        layout = kept + resid
        for i, v in enumerate(layout): self.part[v] = i // W
        self.NB = (len(layout) + W - 1) // W
        self.movable = set(kept)
        self.cnt = np.zeros((K, n), dtype=np.int32)
        for p, g in enumerate(self.groups):
            for v in g:
                for c in adj[v]: self.cnt[p, c] += 1
        used = self.cnt > 0
        self.U = int(used.sum())
        self.blk = np.zeros((K, self.NB), dtype=np.int32)
        for p in range(K):
            cols = np.nonzero(used[p])[0]
            np.add.at(self.blk[p], self.part[cols], 1)
        self.G = int((self.blk > 0).sum())
        self.gid = {}
        for p, g in enumerate(self.groups):
            for v in g: self.gid[v] = p
    def swap(self, u, v):
        # swap two kept points between AIC groups p,q; column blocks = group index (kept part aligned since groups start at 0)
        p = self.gid[u]; q = self.gid[v]
        if p == q: return
        self._colmove_remove(u); self._colmove_remove(v)
        skip = {u, v}
        for c in self.adj[u]:
            self._cntchg(p, c, -1, skip); self._cntchg(q, c, +1, skip)
        for c in self.adj[v]:
            self._cntchg(q, c, -1, skip); self._cntchg(p, c, +1, skip)
        # column block of u,v: their positions swap -> blocks swap
        bu, bv = self.part[u], self.part[v]
        self.part[u] = bv; self.part[v] = bu
        self.gid[u] = q; self.gid[v] = p
        gp = self.groups[p]; gq = self.groups[q]
        gp[gp.index(u)] = v; gq[gq.index(v)] = u
        self._colmove_add(u); self._colmove_add(v)
    def run(self, lam=0.0, sweeps=5, cand_parts=3, seed=0, log=None):
        rng = random.Random(seed)
        obj = lambda: self.U + lam * self.G
        for sw in range(sweeps):
            acc = 0; verts = list(self.movable); rng.shuffle(verts)
            for u in verts:
                p = self.gid[u]; nb = list(self.adj[u])
                ov = self.cnt[:, nb] > 0
                score = ov.sum(axis=1).astype(float); score[p] = -1
                done = False
                for q in list(np.argsort(-score)[:cand_parts]):
                    if score[q] <= 0: break
                    for v in list(self.groups[q]):
                        o0 = obj(); self.swap(u, v)
                        if obj() < o0 - 1e-9: acc += 1; done = True; break
                        self.swap(u, v)
                    if done: break
            if log: log(sw, acc, self.U, self.G)
            if acc == 0: break
        return [v for g in self.groups for v in g] + self.resid
