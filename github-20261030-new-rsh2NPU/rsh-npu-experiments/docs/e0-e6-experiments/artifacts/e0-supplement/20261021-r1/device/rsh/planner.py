from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import time

import numpy as np
from scipy import sparse
from scipy.sparse.csgraph import minimum_spanning_tree


@dataclass
class Matrix:
    ptr: np.ndarray
    col: np.ndarray
    val: np.ndarray
    shape: tuple[int, int]

    @classmethod
    def load(cls, path: str) -> "Matrix":
        with np.load(path) as x:
            a = sparse.csr_matrix((x['values'].astype(np.float32), x['indices'], x['indptr']), shape=tuple(x['shape']))
        a.sum_duplicates()
        a.sort_indices()
        return cls(a.indptr.astype(np.int32), a.indices.astype(np.int32), a.data.astype(np.float16), a.shape)

    def supports(self) -> list[set[int]]:
        return [set(map(int, self.col[self.ptr[r]:self.ptr[r+1]])) for r in range(self.shape[0])]


def reorder(a: Matrix, budget: int = 256, k: int = 16, refine: bool = True) -> tuple[np.ndarray, dict]:
    """Shared-column candidates, bounded kNN, minimum spanning forest and DFS.

    Frequent posting lists are sampled deterministically before the candidate
    budget is reached. This is approximate search, explicitly recorded below.
    """
    started = time.perf_counter()
    m, n = a.shape
    supports = a.supports()
    csr = sparse.csr_matrix((np.ones(len(a.col)), a.col, a.ptr), shape=a.shape)
    csc = csr.tocsc()
    degree = np.diff(csc.indptr)
    weights = np.zeros(n)
    np.divide(1., degree, out=weights, where=degree != 0)
    mass = np.array([sum(weights[list(s)]) if s else 0. for s in supports])

    @lru_cache(maxsize=65536)
    def distance(r: int, u: int) -> float:
        common = sum(weights[j] for j in supports[r].intersection(supports[u]))
        denominator = mass[r] + mass[u] - common
        return 1. - common / denominator if denominator else 1.

    edge_r, edge_u, edge_w = [], [], []
    truncated, sampled = 0, 0
    for r, support in enumerate(supports):
        candidates: set[int] = set()
        for j in sorted(support, key=lambda j: (degree[j], j)):
            posting = csc.indices[csc.indptr[j]:csc.indptr[j+1]]
            if len(posting) > budget + 1:
                # Cover the whole posting without scanning it for every row.
                positions = (np.arange(budget + 1, dtype=np.int64) * len(posting) // (budget + 1) + r) % len(posting)
                posting = posting[positions]
                sampled += 1
            for u in posting:
                if int(u) != r:
                    candidates.add(int(u))
                if len(candidates) >= budget:
                    break
            if len(candidates) >= budget:
                truncated += 1
                break
        best = sorted(((distance(r, u), u) for u in candidates))[:k]
        for d, u in best:
            edge_r.append(r); edge_u.append(u); edge_w.append(d + 1e-9)
    directed = sparse.csr_matrix((edge_w, (edge_r, edge_u)), shape=(m, m))
    graph = directed.maximum(directed.T)
    forest = minimum_spanning_tree(graph).tocsr()
    forest = forest + forest.T
    visited = np.zeros(m, dtype=bool)
    order: list[int] = []
    isolated: list[int] = []
    for root in range(m):
        if visited[root]:
            continue
        if forest.indptr[root] == forest.indptr[root+1]:
            visited[root] = True; isolated.append(root); continue
        stack = [root]
        while stack:
            r = stack.pop()
            if visited[r]:
                continue
            visited[r] = True; order.append(r)
            lo, hi = forest.indptr[r:r+2]
            neighbors = sorted(zip(forest.data[lo:hi], forest.indices[lo:hi]), reverse=True)
            stack.extend(int(u) for _, u in neighbors if not visited[u])
    order.extend(isolated)
    if refine:
        for start in range(0, len(order), 16):
            segment = order[start:start+16]
            best_delta, best_pair = 0., None
            for i in range(len(segment)):
                for j in range(i+1, len(segment)):
                    old, new = 0., 0.
                    if i:
                        old += distance(segment[i-1], segment[i]); new += distance(segment[i-1], segment[j])
                    if j+1 < len(segment):
                        old += distance(segment[j], segment[j+1]); new += distance(segment[i], segment[j+1])
                    if new-old < best_delta-1e-12:
                        best_delta, best_pair = new-old, (i, j)
            if best_pair:
                i, j = best_pair
                segment[i:j+1] = reversed(segment[i:j+1])
                order[start:start+len(segment)] = segment
    result = np.asarray(order, np.int32)
    if not np.array_equal(np.sort(result), np.arange(m)):
        raise ValueError('Reordering lost or duplicated a row')
    return result, {'seconds': time.perf_counter()-started, 'candidate_budget': budget, 'k': k,
                    'candidate_truncated_rows': truncated, 'sampled_posting_visits': sampled,
                    'isolated_rows': len(isolated), 'search': 'bounded_shared_columns',
                    'isolation_adaptation': 'forest_singletons_to_tail; no new affinity edges'}


def partition(a: Matrix, order: np.ndarray, tau_nnz: int = 4, tau_inc: int = 2, w: int = 16) -> dict:
    supports = a.supports()
    groups: list[list[int]] = []
    residual: list[int] = []
    zeros: list[int] = []
    tail: list[int] = []
    r = 0
    while r < len(order):
        if len(order)-r < w:
            tail = list(map(int, order[r:])); break
        row = int(order[r])
        if not supports[row]:
            zeros.append(row); r += 1; continue
        window = list(map(int, order[r:r+w]))
        others = set().union(*(supports[u] for u in window[1:]))
        delta = len(supports[row] - others)
        if delta < tau_inc and len(supports[row]) <= tau_nnz:
            residual.append(row); r += 1
        else:
            groups.append(window); r += w
    return {'groups': groups, 'residual': residual, 'tail': tail, 'zeros': zeros,
            'tau_nnz': tau_nnz, 'tau_inc': tau_inc, 'w': w}


def layout(a: Matrix, order: np.ndarray, split: dict, variant: str) -> dict:
    m, k = a.shape
    identity = list(range(m))
    w = split['w']
    tail = split['tail']
    valid = np.ones(m, dtype=np.uint8)
    if variant == 'V0':
        groups, rows = [], identity
    elif variant in ('V1', 'V2', 'V2-R'):
        seq = identity if variant == 'V1' else list(map(int, order))
        if variant == 'V2-R':
            removed = set(tail)
            seq = [r for r in seq if r not in removed]
            valid[tail] = 0
        groups, rows = [seq[i:i+w] for i in range(0, len(seq), w)], []
    elif variant == 'V0-R':
        removed = set(tail)
        groups, rows = [], [r for r in identity if r not in removed]
        valid[tail] = 0
    else:
        groups = [g.copy() for g in split['groups']]
        rows = split['residual'].copy()
        if variant == 'H-V':
            rows.extend(tail)
        elif variant == 'H-C':
            if tail:
                groups.append(tail.copy())
        elif variant == 'H-Skip':
            valid[tail] = 0
        else:
            raise ValueError(variant)
    ptr, refs, tiles, rowmap = [0], [], [], []
    for group in groups:
        columns = sorted(set().union(*(set(map(int, a.col[a.ptr[r]:a.ptr[r+1]])) for r in group)))
        local_col = {c:i for i,c in enumerate(columns)}
        blocks = (len(columns)+15)//16
        dense = np.zeros((blocks, 16, 16), np.float16)
        for i, r in enumerate(group):
            for p in range(a.ptr[r], a.ptr[r+1]):
                j = local_col[int(a.col[p])]
                dense[j//16, i, j%16] = a.val[p]
        pad = columns + [k]*(blocks*16-len(columns))
        refs.extend(pad)
        tiles.extend(dense)
        ptr.append(ptr[-1]+blocks)
        rowmap.extend(group + [-1]*(16-len(group)))
    coverage = [r for group in groups for r in group] + rows
    if len(set(coverage)) != len(coverage):
        raise ValueError('Duplicated output ownership')
    zero_rows = set(np.flatnonzero(np.diff(a.ptr) == 0).tolist())
    required = set(np.flatnonzero(valid).tolist()) - zero_rows
    if not required.issubset(coverage) or any(not valid[r] for r in coverage):
        raise ValueError('Missing or excluded nonzero row')
    return {'cube_ptr': np.asarray(ptr, np.int64), 'colref': np.asarray(refs, np.int32),
            'tiles': np.asarray(tiles, np.float16).reshape(-1,16,16),
            'rowmap': np.asarray(rowmap, np.int32), 'srows': np.asarray(rows, np.int32),
            'valid': valid, 'variant': variant}


def execute_cpu(a: Matrix, plan: dict, b: np.ndarray) -> np.ndarray:
    out = np.zeros((a.shape[0], b.shape[1]), np.float32)
    padded_b = np.concatenate((b.astype(np.float32), np.zeros((1, b.shape[1]), np.float32)))
    for g in range(len(plan['cube_ptr'])-1):
        lo, hi = plan['cube_ptr'][g:g+2]
        values = np.zeros((16,b.shape[1]), np.float32)
        for tile in range(lo,hi):
            js = plan['colref'][tile*16:(tile+1)*16]
            values += plan['tiles'][tile].astype(np.float32) @ padded_b[js]
        for i, r in enumerate(plan['rowmap'][g*16:(g+1)*16]):
            if r >= 0:
                out[r] = values[i]
    for r in plan['srows']:
        lo, hi = a.ptr[r:r+2]
        out[r] = a.val[lo:hi].astype(np.float32) @ b[a.col[lo:hi]].astype(np.float32)
    return out
