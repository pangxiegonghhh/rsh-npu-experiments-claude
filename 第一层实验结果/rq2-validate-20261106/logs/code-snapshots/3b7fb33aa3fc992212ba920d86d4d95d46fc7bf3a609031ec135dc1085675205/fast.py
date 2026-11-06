from __future__ import annotations
import ctypes as C
import math, os, random
from pathlib import Path
import numpy as np

BASE = Path(__file__).resolve().parents[1]
DEFAULT_LIB = next((BASE/'work'/name for name in ('librq2-v4.dylib','librq2-v3.dylib','librq2-v2.dylib','librq2.dylib') if (BASE/'work'/name).exists()))
LIB = C.CDLL(os.environ.get('RQ2_NATIVE_LIB',str(DEFAULT_LIB)))
PTR = C.c_void_p
I = C.POINTER(C.c_int32)
L = C.POINTER(C.c_int64)
D = C.POINTER(C.c_double)
LIB.rq_graph.argtypes = [C.c_int, L, I]; LIB.rq_graph.restype = PTR
LIB.rq_free_graph.argtypes = [PTR]
LIB.rq_order.argtypes = [PTR, C.c_int, C.c_int, C.c_double, I]
LIB.rq_bp_split.argtypes = [PTR, I, C.c_int, C.c_int, C.c_int, D, I]
LIB.rq_ls.argtypes = [PTR, I, C.c_int, C.c_int]; LIB.rq_ls.restype = PTR
LIB.rq_ls_sweep.argtypes = [PTR, I, C.c_int, C.c_double]; LIB.rq_ls_sweep.restype = C.c_int
LIB.rq_ls_get.argtypes = [PTR, I, L]
LIB.rq_free_ls.argtypes = [PTR]

def ip(a: np.ndarray): return a.ctypes.data_as(I)

class FastGraph:
    def __init__(self, adj: list[set[int]]) -> None:
        self.n = len(adj); self.adj = adj
        self.indptr = np.zeros(self.n + 1, dtype=np.int64)
        self.indptr[1:] = np.cumsum([len(x) for x in adj])
        self.indices = np.fromiter((v for row in adj for v in row), dtype=np.int32, count=int(self.indptr[-1]))
        self.ptr = LIB.rq_graph(self.n, self.indptr.ctypes.data_as(L), ip(self.indices))
    def close(self) -> None:
        if self.ptr: LIB.rq_free_graph(self.ptr); self.ptr = None
    def order(self, method: str, W: int = 16, beta: float = 1.) -> list[int]:
        out = np.empty(self.n, dtype=np.int32)
        LIB.rq_order(self.ptr, {'gorder': 0, 'rsh': 1, 'rabbit': 2, 'neutron': 3}[method], W, beta, ip(out))
        return out.tolist()
    def bp(self, W: int = 16, seed: int = 0) -> list[int]:
        rng = random.Random(seed)
        logs = np.asarray([0.] + [math.log2(x) for x in range(1, self.n + 2)], dtype=np.float64)
        def split(vertices: list[int]) -> list[int]:
            if len(vertices) <= W: return vertices
            size = len(vertices); s1 = W * math.ceil(size / (2 * W))
            vertices = vertices[:]; rng.shuffle(vertices)
            arr = np.asarray(vertices, dtype=np.int32); side = np.empty(size, dtype=np.int32)
            LIB.rq_bp_split(self.ptr, ip(arr), size, s1, 20, logs.ctypes.data_as(D), ip(side))
            return split([v for i, v in enumerate(vertices) if side[i] == 0]) + split([v for i, v in enumerate(vertices) if side[i] == 1])
        return split(list(range(self.n)))
    def ls(self, order: list[int], W: int, tau: int | None, lam: float, seed: int, sweeps: int = 10) -> tuple[list[int], dict]:
        arr = np.asarray(order, dtype=np.int32); state = LIB.rq_ls(self.ptr, ip(arr), W, -1 if tau is None else tau)
        movable = list(range(self.n)) if tau is None else list(set(v for v in order if len(self.adj[v]) > tau))
        rng = random.Random(seed); history = []
        try:
            for sweep in range(sweeps):
                vertices = movable[:]; rng.shuffle(vertices); seq = np.asarray(vertices, dtype=np.int32)
                accepted = LIB.rq_ls_sweep(state, ip(seq), len(seq), lam)
                out = np.empty(self.n, dtype=np.int32); ug = np.empty(2, dtype=np.int64)
                LIB.rq_ls_get(state, ip(out), ug.ctypes.data_as(L))
                history.append({'sweep': sweep, 'accepted': accepted, 'sumU': int(ug[0]), 'sumGamma': int(ug[1])})
                print('LS', tau, lam, seed, history[-1], flush=True)
                if not accepted: break
            return out.tolist(), {'sweeps_done': len(history), 'accepted_swaps': sum(h['accepted'] for h in history),
                                  'tracked_sumU': int(ug[0]), 'tracked_sumGamma': int(ug[1]), 'history': history,
                                  'tie_rule': 'overlap descending, group index ascending; within-group current order',
                                  'rng': 'Python random.Random(seed); reference range(n) or list(set(kept)) before each shuffle'}
        finally: LIB.rq_free_ls(state)
