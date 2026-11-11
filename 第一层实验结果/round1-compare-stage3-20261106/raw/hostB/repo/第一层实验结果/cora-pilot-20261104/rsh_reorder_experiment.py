#!/usr/bin/env python3
"""Structure-only experiment for the first RSH-to-NPU research layer.

The program deliberately stops at row/column reordering and W16 structure
measurement.  It does not model RS-tiles, Bitmap, Gather, ND2NZ, AIV/AIC, or
Cube execution.  Rabbit and Neutron are deterministic structural baselines;
they are useful for the proposed comparison, but are not claimed to be full
implementations of either paper.

The main entry point is ``python rsh_reorder_experiment.py``.  With no input
file it generates a deterministic synthetic matrix so that the complete
pipeline can be exercised immediately.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import heapq
import html
import json
import math
import random
import statistics
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


EPS = 1e-12
K16 = 16  # fixed column grouping used by the structural evaluator


@dataclass(frozen=True)
class SparseMatrix:
    """A small structure-aware sparse matrix representation.

    ``entries[r]`` stores ``(column, value)`` pairs with unique, sorted
    columns.  Values are retained so the output checks can verify that a
    permutation changes layout only and not matrix semantics.
    """

    n_rows: int
    n_cols: int
    entries: tuple[tuple[tuple[int, float], ...], ...]
    name: str = "matrix"

    @property
    def nnz(self) -> int:
        return sum(len(row) for row in self.entries)

    @property
    def supports(self) -> tuple[frozenset[int], ...]:
        return tuple(frozenset(col for col, _ in row) for row in self.entries)

    @property
    def values_multiset(self) -> tuple[float, ...]:
        return tuple(sorted(value for row in self.entries for _, value in row))

    @classmethod
    def from_rows(
        cls,
        rows: Sequence[Iterable[int] | Mapping[int, float] | Iterable[tuple[int, float]]],
        n_cols: int | None = None,
        name: str = "matrix",
    ) -> "SparseMatrix":
        normalized: list[tuple[tuple[int, float], ...]] = []
        maximum = -1
        for row in rows:
            accum: dict[int, float] = defaultdict(float)
            items = list(row)  # type: ignore[arg-type]
            if isinstance(row, Mapping):
                items = list(row.items())
            for item in items:
                if isinstance(item, int):
                    col, value = item, 1.0
                else:
                    col, value = item  # type: ignore[misc]
                col = int(col)
                value = float(value)
                if col < 0:
                    raise ValueError(f"negative column index: {col}")
                accum[col] += value
            clean = tuple(sorted((col, value) for col, value in accum.items() if value != 0.0))
            if clean:
                maximum = max(maximum, clean[-1][0])
            normalized.append(clean)
        inferred_cols = maximum + 1
        final_cols = inferred_cols if n_cols is None else int(n_cols)
        if final_cols < inferred_cols:
            raise ValueError("n_cols is smaller than an observed column index")
        return cls(len(normalized), final_cols, tuple(normalized), name)


def _parse_number(text: str) -> float:
    try:
        return float(text)
    except ValueError as exc:
        raise ValueError(f"cannot parse numeric value {text!r}") from exc


def load_matrix_market(path: Path) -> SparseMatrix:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        header = handle.readline().strip().lower().split()
        if len(header) < 5 or header[0] != "%%matrixmarket" or header[1] != "matrix":
            raise ValueError(f"{path} is not a Matrix Market matrix file")
        coordinate = header[2] == "coordinate"
        if not coordinate:
            raise ValueError("only Matrix Market coordinate format is supported")
        value_kind = header[3]
        symmetry = header[4]
        if value_kind not in {"pattern", "real", "integer"} or symmetry not in {"general", "symmetric"}:
            raise ValueError(f"unsupported Matrix Market field/symmetry: {value_kind} {symmetry}")
        # Entries with duplicate coordinates are summed; exact zeros are removed.
        line = handle.readline()
        while line and line.lstrip().startswith("%"):
            line = handle.readline()
        if not line:
            raise ValueError("Matrix Market file is missing dimensions")
        n_rows, n_cols, n_entries = (int(value) for value in line.split()[:3])
        entries: list[tuple[int, int, float]] = []
        for _ in range(n_entries):
            line = handle.readline()
            while line and line.lstrip().startswith("%"):
                line = handle.readline()
            if not line:
                raise ValueError("Matrix Market file ended before all entries")
            fields = line.split()
            if len(fields) < 2:
                continue
            row = int(fields[0]) - 1
            col = int(fields[1]) - 1
            value = 1.0 if value_kind == "pattern" else _parse_number(fields[2])
            entries.append((row, col, value))
            if symmetry == "symmetric" and row != col:
                entries.append((col, row, value))
        rows: list[dict[int, float]] = [defaultdict(float) for _ in range(n_rows)]
        for row, col, value in entries:
            rows[row][col] += value
        return SparseMatrix.from_rows(rows, n_cols=n_cols, name=path.stem)


def load_json_matrix(path: Path) -> SparseMatrix:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("JSON matrix must be an object")
    raw_rows = data.get("rows")
    if raw_rows is None:
        raise ValueError("JSON matrix must contain a rows field")
    rows: list[Any] = []
    for row in raw_rows:
        if isinstance(row, dict) and "columns" in row:
            columns = row["columns"]
            values = row.get("values", [1.0] * len(columns))
            rows.append(list(zip(columns, values)))
        else:
            rows.append(row)
    n_cols = data.get("n_cols")
    return SparseMatrix.from_rows(rows, n_cols=n_cols, name=data.get("name", path.stem))


def load_csv_matrix(path: Path) -> SparseMatrix:
    rows_raw: list[tuple[int, int, float]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for fields in csv.reader(handle):
            if not fields or fields[0].strip().startswith("#"):
                continue
            if fields[0].strip().lower() in {"row", "r"}:
                continue
            if len(fields) < 2:
                continue
            row, col = int(fields[0]), int(fields[1])
            value = float(fields[2]) if len(fields) >= 3 else 1.0
            rows_raw.append((row, col, value))
    n_rows = max((row for row, _, _ in rows_raw), default=-1) + 1
    n_cols = max((col for _, col, _ in rows_raw), default=-1) + 1
    rows: list[dict[int, float]] = [defaultdict(float) for _ in range(n_rows)]
    for row, col, value in rows_raw:
        rows[row][col] += value
    return SparseMatrix.from_rows(rows, n_cols=n_cols, name=path.stem)


def load_npz_matrix(path: Path) -> SparseMatrix:
    try:
        import numpy as np  # type: ignore
    except ImportError as exc:
        raise ValueError("loading .npz requires numpy") from exc
    data = np.load(path, allow_pickle=False)
    if {"indptr", "indices"}.issubset(data.files):
        indptr = data["indptr"].tolist()
        indices = data["indices"].tolist()
        values = data["data"].tolist() if "data" in data.files else [1.0] * len(indices)
        shape = tuple(int(x) for x in data["shape"].tolist()) if "shape" in data.files else None
        n_rows = len(indptr) - 1
        n_cols = shape[1] if shape else (max(indices, default=-1) + 1)
        rows = []
        for row in range(n_rows):
            rows.append(list(zip(indices[indptr[row] : indptr[row + 1]], values[indptr[row] : indptr[row + 1]])))
        return SparseMatrix.from_rows(rows, n_cols=n_cols, name=path.stem)
    if "rows" in data.files:
        rows_array = data["rows"].tolist()
        n_cols = int(data["n_cols"].item()) if "n_cols" in data.files else None
        return SparseMatrix.from_rows(rows_array, n_cols=n_cols, name=path.stem)
    raise ValueError("npz must contain CSR arrays (indptr, indices[, data, shape])")


def load_sparse_matrix(path: str | Path) -> SparseMatrix:
    path = Path(path)
    suffixes = [suffix.lower() for suffix in path.suffixes]
    if suffixes[-2:] == [".mtx", ".gz"] or path.suffix.lower() == ".mtx":
        return load_matrix_market(path)
    if path.suffix.lower() == ".json":
        return load_json_matrix(path)
    if path.suffix.lower() == ".csv":
        return load_csv_matrix(path)
    if path.suffix.lower() == ".npz":
        return load_npz_matrix(path)
    raise ValueError(f"unsupported matrix format: {path.suffix}; use .mtx, .json, .csv, or .npz")


def synthetic_matrix(n_rows: int = 192, n_cols: int = 192, seed: int = 0, name: str = "synthetic") -> SparseMatrix:
    """Create repeatable overlapping column communities for smoke experiments."""
    rng = random.Random(seed)
    rows: list[list[tuple[int, float]]] = []
    community_count = max(1, n_rows // 32)
    community_width = max(8, n_cols // community_count)
    for row in range(n_rows):
        community = row % community_count
        start = (community * community_width) % n_cols
        support: set[int] = set()
        # A local block, a small overlap with the following community, and a
        # deterministic amount of noise expose both row and column locality.
        for offset in range(8):
            support.add((start + offset) % n_cols)
        next_start = ((community + 1) * community_width) % n_cols
        for offset in range(2):
            support.add((next_start + offset) % n_cols)
        for _ in range(2 + (row % 3)):
            support.add(rng.randrange(n_cols))
        rows.append([(col, float((row + col) % 7 + 1)) for col in sorted(support)])
    return SparseMatrix.from_rows(rows, n_cols=n_cols, name=name)


def _column_degrees(matrix: SparseMatrix) -> list[int]:
    degrees = [0] * matrix.n_cols
    for support in matrix.supports:
        for col in support:
            degrees[col] += 1
    return degrees


def _weights(matrix: SparseMatrix, alpha: float) -> list[float] | None:
    if abs(alpha) <= EPS:
        return None
    degrees = _column_degrees(matrix)
    return [degree ** (-alpha) if degree > 0 else 0.0 for degree in degrees]


def _weights_for_supports(supports: Sequence[frozenset[int]], alpha: float) -> list[float] | None:
    if abs(alpha) <= EPS:
        return None
    n_cols = max((max(support) for support in supports if support), default=-1) + 1
    degrees = [0] * n_cols
    for support in supports:
        for col in support:
            degrees[col] += 1
    return [degree ** (-alpha) if degree > 0 else 0.0 for degree in degrees]


def support_similarity(a: frozenset[int] | set[int], b: frozenset[int] | set[int], weights: Sequence[float] | None = None) -> float:
    union = a | b
    if not union:
        return 1.0
    if weights is None:
        return len(a & b) / len(union)
    numerator = sum(weights[col] for col in a & b)
    denominator = sum(weights[col] for col in union)
    return numerator / denominator if denominator else 0.0


def _pair_similarity(
    row_a: int,
    row_b: int,
    supports: Sequence[frozenset[int]],
    weights: Sequence[float] | None,
    cache: dict[tuple[int, int], float],
) -> float:
    key = (row_a, row_b) if row_a < row_b else (row_b, row_a)
    if key not in cache:
        cache[key] = support_similarity(supports[key[0]], supports[key[1]], weights)
    return cache[key]


def _path_edge_cost(a: int, b: int, supports: Sequence[frozenset[int]], weights: Sequence[float] | None, cache: dict[tuple[int, int], float]) -> float:
    return 1.0 - _pair_similarity(a, b, supports, weights, cache)


def _local_two_opt(
    order: list[int],
    supports: Sequence[frozenset[int]],
    weights: Sequence[float] | None,
    cache: dict[tuple[int, int], float],
    passes: int = 2,
    max_span: int = 8,
) -> list[int]:
    """Deterministic bounded 2-opt path refinement.

    The span is a fixed algorithm parameter and is intentionally independent
    of the evaluation W16.  It captures the local sequence refinement stage
    without turning this experiment into the later row-window algorithm.
    """
    result = list(order)
    for _ in range(max(0, passes)):
        changed = False
        for i in range(len(result) - 2):
            for j in range(i + 1, min(len(result) - 1, i + max_span)):
                left = result[i - 1] if i else None
                right = result[j + 1] if j + 1 < len(result) else None
                old = 0.0
                new = 0.0
                if left is not None:
                    old += _path_edge_cost(left, result[i], supports, weights, cache)
                    new += _path_edge_cost(left, result[j], supports, weights, cache)
                if right is not None:
                    old += _path_edge_cost(result[j], right, supports, weights, cache)
                    new += _path_edge_cost(result[i], right, supports, weights, cache)
                if new + EPS < old:
                    result[i : j + 1] = reversed(result[i : j + 1])
                    changed = True
        if not changed:
            break
    return result


def _connected_components(graph: Mapping[int, set[int]], n_nodes: int) -> list[list[int]]:
    remaining = set(range(n_nodes))
    components: list[list[int]] = []
    while remaining:
        root = min(remaining)
        queue = [root]
        remaining.remove(root)
        component: list[int] = []
        while queue:
            node = queue.pop()
            component.append(node)
            for neighbor in sorted(graph.get(node, set())):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    queue.append(neighbor)
        components.append(sorted(component))
    return components


def _maximum_spanning_dfs(component: Sequence[int], graph: Mapping[int, Mapping[int, float]]) -> list[int]:
    root = min(component)
    tree: dict[int, list[tuple[float, int]]] = {node: [] for node in component}
    visited = {root}
    frontier: list[tuple[float, int, int]] = []
    for neighbor, weight in graph.get(root, {}).items():
        frontier.append((-weight, neighbor, root))
    heapq.heapify(frontier)
    while frontier:
        neg_weight, node, parent = heapq.heappop(frontier)
        if node in visited:
            continue
        visited.add(node)
        weight = -neg_weight
        tree[parent].append((weight, node))
        tree[node].append((weight, parent))
        for neighbor, edge_weight in graph.get(node, {}).items():
            if neighbor not in visited:
                heapq.heappush(frontier, (-edge_weight, neighbor, node))
    # A connected component should be fully covered.  This fallback is only
    # relevant if a caller supplies an incomplete graph.
    for node in component:
        if node not in visited:
            tree[root].append((0.0, node))
            tree[node].append((0.0, root))
    order: list[int] = []

    stack: list[tuple[int, int | None]] = [(root, None)]
    while stack:
        node, parent = stack.pop()
        order.append(node)
        neighbors = sorted(tree[node], key=lambda item: (-item[0], item[1]))
        stack.extend((neighbor, node) for _, neighbor in reversed(neighbors) if neighbor != parent)
    return order


def rsh_reorder(
    matrix: SparseMatrix,
    *,
    k: int = 8,
    weighted_alpha: float = 0.0,
    refine_passes: int = 2,
    refine_span: int = 8,
) -> tuple[list[int], None, dict[str, Any], dict[tuple[int, int], float]]:
    """Simplified implementation of the RSH row-reordering stages.

    It follows support features → inverted index → top-k undirected graph →
    maximum-spanning-tree DFS → bounded local refinement.  The paper leaves
    several engineering choices unspecified; these parameters are fixed
    globally by the CLI and are recorded in every result.
    """
    supports = matrix.supports
    weights = _weights(matrix, weighted_alpha)
    inverted: dict[int, set[int]] = defaultdict(set)
    for row, support in enumerate(supports):
        for col in support:
            inverted[col].add(row)
    similarity_cache: dict[tuple[int, int], float] = {}
    graph: dict[int, dict[int, float]] = {row: {} for row in range(matrix.n_rows)}
    directed_candidate_edges = 0
    for row, support in enumerate(supports):
        candidate_rows: set[int] = set()
        for col in support:
            candidate_rows.update(inverted[col])
        candidate_rows.discard(row)
        ranked = heapq.nsmallest(max(0, int(k)),
            ((-support_similarity(support, supports[other], weights), other) for other in candidate_rows))
        directed_candidate_edges += len(ranked)
        for negative_similarity, other in ranked:
            similarity = -negative_similarity
            if similarity <= 0.0:
                continue
            graph[row][other] = max(graph[row].get(other, 0.0), similarity)
            graph[other][row] = max(graph[other].get(row, 0.0), similarity)
    unweighted = {row: set(neighbors) for row, neighbors in graph.items()}
    components = _connected_components(unweighted, matrix.n_rows)
    components.sort(key=lambda component: (-len(component), min(component)))
    order: list[int] = []
    for component in components:
        if any(graph[node] for node in component):
            order.extend(_maximum_spanning_dfs(component, graph))
        else:
            order.extend(sorted(component))
    max_similarity = {
        row: max(graph[row].values(), default=0.0) for row in range(matrix.n_rows)
    }
    isolated = sorted(row for row, similarity in max_similarity.items() if similarity <= 0.0)
    if isolated:
        isolated_set = set(isolated)
        order = [row for row in order if row not in isolated_set] + isolated
    order = _local_two_opt(order, supports, weights, similarity_cache, passes=refine_passes, max_span=refine_span)
    graph_edges = sum(len(neighbors) for neighbors in graph.values()) // 2
    stats = {
        "graph_type": "row_support_knn",
        "candidate_edges_directed": directed_candidate_edges,
        "graph_edges_undirected": graph_edges,
        "graph_components": len(components),
        "isolated_rows": len(isolated),
        "average_degree": (2.0 * graph_edges / matrix.n_rows) if matrix.n_rows else 0.0,
        "maximum_degree": max((len(neighbors) for neighbors in graph.values()), default=0),
    }
    config = {
        "feature": "nonzero_column_support_set",
        "similarity": "jaccard" if weights is None else "weighted_jaccard",
        "weighted_alpha": weighted_alpha,
        "k": int(k),
        "local_refinement": "bounded_2opt",
        "refine_passes": int(refine_passes),
        "refine_span": int(refine_span),
        "rsh_variant": "support-set simplified reproduction",
    }
    return order, None, {**stats, "config": config}, similarity_cache


def _bipartite_components(matrix: SparseMatrix) -> int:
    col_to_rows: dict[int, set[int]] = defaultdict(set)
    supports = matrix.supports
    for row, support in enumerate(supports):
        for col in support:
            col_to_rows[col].add(row)
    unseen_rows = set(range(matrix.n_rows))
    unseen_cols = set(range(matrix.n_cols))
    count = 0
    while unseen_rows or unseen_cols:
        if unseen_rows:
            root = ("r", min(unseen_rows))
        else:
            root = ("c", min(unseen_cols))
        queue = deque([root])
        count += 1
        while queue:
            kind, node = queue.popleft()
            if kind == "r":
                if node not in unseen_rows:
                    continue
                unseen_rows.remove(node)
                for col in supports[node]:
                    if col in unseen_cols:
                        queue.append(("c", col))
            else:
                if node not in unseen_cols:
                    continue
                unseen_cols.remove(node)
                for row in col_to_rows[node]:
                    if row in unseen_rows:
                        queue.append(("r", row))
    return count


def rabbit_reorder(matrix: SparseMatrix) -> tuple[list[int], list[int], dict[str, Any]]:
    """Deterministic bipartite traversal baseline inspired by Rabbit Order."""
    supports = matrix.supports
    col_to_rows: dict[int, set[int]] = defaultdict(set)
    for row, support in enumerate(supports):
        for col in support:
            col_to_rows[col].add(row)
    row_degree = [len(support) for support in supports]
    col_degree = [len(col_to_rows[col]) for col in range(matrix.n_cols)]
    unseen = set(range(matrix.n_rows))
    seen_columns: set[int] = set()
    row_order: list[int] = []
    col_order: list[int] = []
    while unseen:
        root = min(unseen, key=lambda row: (-row_degree[row], row))
        queue: deque[int] = deque([root])
        while queue:
            row = queue.popleft()
            if row not in unseen:
                continue
            unseen.remove(row)
            row_order.append(row)
            columns = sorted(supports[row], key=lambda col: (-col_degree[col], col))
            for col in columns:
                if col not in seen_columns:
                    seen_columns.add(col)
                    col_order.append(col)
                neighbors = sorted(col_to_rows[col], key=lambda other: (-row_degree[other], other))
                for neighbor in neighbors:
                    if neighbor in unseen:
                        queue.append(neighbor)
    col_order.extend(sorted((col for col in range(matrix.n_cols) if col not in seen_columns), key=lambda col: (-col_degree[col], col)))
    graph_edges = matrix.nnz
    stats = {
        "graph_type": "row_column_bipartite",
        "graph_edges_bipartite": graph_edges,
        "bipartite_components": _bipartite_components(matrix),
        "average_row_degree": (graph_edges / matrix.n_rows) if matrix.n_rows else 0.0,
        "average_column_degree": (graph_edges / matrix.n_cols) if matrix.n_cols else 0.0,
    }
    return row_order, col_order, stats


def neutron_reorder(
    matrix: SparseMatrix,
    *,
    w16: int = 16,
    cluster_windows: int = 8,
) -> tuple[list[int], list[int], dict[str, Any]]:
    """Simplified Neutron-style global cluster plus local row windows."""
    coarse_rows, col_order, rabbit_stats = rabbit_reorder(matrix)
    supports = matrix.supports
    cluster_target = max(1, int(w16) * int(cluster_windows))
    final_order: list[int] = []
    cluster_sizes: list[int] = []
    local_window_sizes: list[int] = []
    coarse_rank = {row: index for index, row in enumerate(coarse_rows)}
    for offset in range(0, len(coarse_rows), cluster_target):
        cluster = coarse_rows[offset : offset + cluster_target]
        cluster_sizes.append(len(cluster))
        remaining = list(cluster)
        while remaining:
            anchor = remaining.pop(0)
            window = [anchor]
            while remaining and len(window) < max(1, int(w16)):
                best = min(
                    remaining,
                    key=lambda row: (
                        -support_similarity(supports[anchor], supports[row]),
                        coarse_rank[row],
                        row,
                    ),
                )
                remaining.remove(best)
                window.append(best)
            local_window_sizes.append(len(window))
            final_order.extend(window)
    stats = {
        **rabbit_stats,
        "graph_type": "bipartite_global_local_simplified",
        "cluster_target_rows": cluster_target,
        "cluster_target_windows": int(cluster_windows),
        "cluster_count": len(cluster_sizes),
        "cluster_sizes": cluster_sizes,
        "local_window_sizes": local_window_sizes,
        "global_stage": "bipartite coarse traversal",
        "local_stage": "anchor Jaccard grouping within each cluster",
    }
    return final_order, col_order, stats


def inverse_permutation(permutation: Sequence[int]) -> list[int]:
    inverse = [0] * len(permutation)
    for new_index, old_index in enumerate(permutation):
        inverse[old_index] = new_index
    return inverse


def _validate_row_permutation(matrix: SparseMatrix, row_perm: Sequence[int], inverse: Sequence[int]) -> dict[str, bool]:
    is_bijection = sorted(row_perm) == list(range(matrix.n_rows))
    inverse_ok = is_bijection and all(inverse[old] == new for new, old in enumerate(row_perm))
    reordered_entries = [matrix.entries[old] for old in row_perm]
    restored = [reordered_entries[inverse[old]] for old in range(matrix.n_rows)] if inverse_ok else []
    original_entries = list(matrix.entries)
    values_preserved = tuple(sorted(value for row in reordered_entries for _, value in row)) == matrix.values_multiset
    nnz_preserved = sum(len(row) for row in reordered_entries) == matrix.nnz
    columns_preserved = sorted(col for row in reordered_entries for col, _ in row) == sorted(col for row in matrix.entries for col, _ in row)
    return {
        "row_perm_is_bijection": is_bijection,
        "inverse_restores_rows": inverse_ok and restored == original_entries,
        "nnz_preserved": nnz_preserved,
        "values_preserved": values_preserved,
        "original_column_ids_preserved": columns_preserved,
    }


def _validate_native_permutation(matrix: SparseMatrix, row_perm: Sequence[int], col_perm: Sequence[int]) -> bool:
    if sorted(col_perm) != list(range(matrix.n_cols)):
        return False
    inverse_rows = inverse_permutation(row_perm)
    inverse_cols = inverse_permutation(col_perm)
    transformed: list[tuple[int, int, float]] = []
    for new_row, old_row in enumerate(row_perm):
        for old_col, value in matrix.entries[old_row]:
            transformed.append((new_row, inverse_cols[old_col], value))
    # row_perm maps a transformed row back to its original row.
    restored = sorted((row_perm[new_row], col_perm[new_col], value) for new_row, new_col, value in transformed)
    original = sorted((row, col, value) for row, entries in enumerate(matrix.entries) for col, value in entries)
    return restored == original


def _remapped_supports(matrix: SparseMatrix, col_perm: Sequence[int] | None) -> tuple[frozenset[int], ...]:
    if col_perm is None:
        return matrix.supports
    new_index = {old: new for new, old in enumerate(col_perm)}
    return tuple(frozenset(new_index[col] for col in support) for support in matrix.supports)


def adjacency_metrics(order: Sequence[int], supports: Sequence[frozenset[int]], weighted_alpha: float = 0.0, matrix: SparseMatrix | None = None) -> dict[str, float | int]:
    weights = _weights_for_supports(supports, weighted_alpha) if weighted_alpha else None
    similarities = [support_similarity(supports[order[i]], supports[order[i + 1]], weights) for i in range(max(0, len(order) - 1))]
    if not similarities:
        return {
            "adjacent_pair_count": 0,
            "average_adjacent_similarity": 0.0,
            "average_adjacent_dissimilarity": 0.0,
            "cumulative_adjacent_dissimilarity": 0.0,
            "minimum_adjacent_similarity": 0.0,
            "maximum_adjacent_similarity": 0.0,
            "adjacent_overlap_fraction": 0.0,
            "high_similarity_adjacent_fraction": 0.0,
        }
    high = sum(similarity >= 0.5 for similarity in similarities)
    overlap = sum(similarity > 0.0 for similarity in similarities)
    average = statistics.fmean(similarities)
    return {
        "adjacent_pair_count": len(similarities),
        "average_adjacent_similarity": average,
        "average_adjacent_dissimilarity": 1.0 - average,
        "cumulative_adjacent_dissimilarity": sum(1.0 - similarity for similarity in similarities),
        "minimum_adjacent_similarity": min(similarities),
        "maximum_adjacent_similarity": max(similarities),
        "adjacent_overlap_fraction": overlap / len(similarities),
        "high_similarity_adjacent_fraction": high / len(similarities),
    }


def _runs(columns: Sequence[int]) -> tuple[int, float, int]:
    if not columns:
        return 0, 0.0, 0
    run_count = 1
    current = 1
    maximum = 1
    for previous, current_col in zip(columns, columns[1:]):
        if current_col == previous + 1:
            current += 1
        else:
            run_count += 1
            maximum = max(maximum, current)
            current = 1
    maximum = max(maximum, current)
    return run_count, len(columns) / run_count, maximum


def window_metrics(
    order: Sequence[int],
    supports: Sequence[frozenset[int]],
    *,
    w16: int,
    n_cols: int,
    k16_width: int = K16,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    windows: list[dict[str, Any]] = []
    for window_id, start in enumerate(range(0, len(order), max(1, int(w16)))):
        rows = list(order[start : start + max(1, int(w16))])
        union = set().union(*(supports[row] for row in rows)) if rows else set()
        columns = sorted(union)
        run_count, average_run_length, maximum_run_length = _runs(columns)
        k16 = math.ceil(len(columns) / max(1, int(k16_width))) if columns else 0
        nnz = sum(len(supports[row]) for row in rows)
        capacity = len(rows) * k16 * max(1, int(k16_width))
        windows.append(
            {
                "window_id": window_id,
                "start": start,
                "row_count": len(rows),
                "rows": rows,
                "nnz": nnz,
                "unique_columns": len(columns),
                "column_union": columns,
                "k16_count": k16,
                "padded_columns": k16 * max(1, int(k16_width)) - len(columns),
                "occupancy": (nnz / capacity) if capacity else 0.0,
                "column_span": (columns[-1] - columns[0] + 1) if columns else 0,
                "run_count": run_count,
                "average_run_length": average_run_length,
                "maximum_run_length": maximum_run_length,
                "normalized_union": (len(columns) / n_cols) if n_cols else 0.0,
                "column_reuse": (nnz / len(columns)) if columns else 0.0,
            }
        )
    unions = [set(window["column_union"]) for window in windows]
    transitions = [support_similarity(frozenset(unions[i]), frozenset(unions[i + 1])) for i in range(len(unions) - 1)]
    def avg(field: str) -> float:
        values = [float(window[field]) for window in windows]
        return statistics.fmean(values) if values else 0.0
    summary: dict[str, Any] = {
        "window_count": len(windows),
        "window_height": max(1, int(w16)),
        "k16_width": max(1, int(k16_width)),
        "mean_unique_columns": avg("unique_columns"),
        "median_unique_columns": statistics.median([window["unique_columns"] for window in windows]) if windows else 0.0,
        "mean_k16_count": avg("k16_count"),
        "mean_occupancy": avg("occupancy"),
        "mean_run_count": avg("run_count"),
        "mean_average_run_length": avg("average_run_length"),
        "mean_maximum_run_length": avg("maximum_run_length"),
        "mean_column_span": avg("column_span"),
        "mean_column_reuse": avg("column_reuse"),
        "mean_window_transition_similarity": statistics.fmean(transitions) if transitions else 0.0,
        "mean_window_transition_dissimilarity": (1.0 - statistics.fmean(transitions)) if transitions else 0.0,
    }
    return windows, summary


def _method_base_results(matrix: SparseMatrix, *, w16: int, k: int, weighted_alpha: float, seed: int, neutron_cluster_windows: int, refine_passes: int) -> dict[str, dict[str, Any]]:
    started = time.perf_counter()
    original_order = list(range(matrix.n_rows))
    original_time = time.perf_counter() - started
    base: dict[str, dict[str, Any]] = {
        "original": {
            "row_perm": original_order,
            "col_perm": None,
            "preprocessing_time_seconds": original_time,
            "graph_statistics": {"graph_type": "identity", "graph_edges": 0, "graph_components": matrix.n_rows},
            "method_config": {"description": "original row order", "seed": seed},
        }
    }
    started = time.perf_counter()
    rsh_rows, _, rsh_stats, _ = rsh_reorder(
        matrix, k=k, weighted_alpha=weighted_alpha, refine_passes=refine_passes
    )
    base["rsh"] = {
        "row_perm": rsh_rows,
        "col_perm": None,
        "preprocessing_time_seconds": time.perf_counter() - started,
        "graph_statistics": {key: value for key, value in rsh_stats.items() if key != "config"},
        "method_config": {"description": "RSH support-set simplified reproduction", "seed": seed, **rsh_stats["config"], "w16_role": "evaluation only"},
    }
    started = time.perf_counter()
    rabbit_rows, rabbit_cols, rabbit_stats = rabbit_reorder(matrix)
    base["rabbit"] = {
        "row_perm": rabbit_rows,
        "col_perm": rabbit_cols,
        "preprocessing_time_seconds": time.perf_counter() - started,
        "graph_statistics": rabbit_stats,
        "method_config": {"description": "Rabbit-inspired deterministic bipartite traversal baseline", "seed": seed, "simplification": "coarse bipartite traversal; not full paper implementation"},
    }
    started = time.perf_counter()
    neutron_rows, neutron_cols, neutron_stats = neutron_reorder(matrix, w16=w16, cluster_windows=neutron_cluster_windows)
    base["neutron"] = {
        "row_perm": neutron_rows,
        "col_perm": neutron_cols,
        "preprocessing_time_seconds": time.perf_counter() - started,
        "graph_statistics": neutron_stats,
        "method_config": {"description": "Neutron-inspired deterministic global-local baseline", "seed": seed, "simplification": "bipartite coarse clusters plus local Jaccard windows", "cluster_target_windows": neutron_cluster_windows, "cluster_target_rows": neutron_cluster_windows * w16},
    }
    return base


def run_experiment(
    matrix: SparseMatrix,
    *,
    w16: int = 16,
    k: int = 8,
    weighted_alpha: float = 0.0,
    seed: int = 0,
    neutron_cluster_windows: int = 8,
    refine_passes: int = 2,
) -> dict[str, Any]:
    if w16 <= 0:
        raise ValueError("w16 must be positive")
    base_results = _method_base_results(
        matrix,
        w16=w16,
        k=k,
        weighted_alpha=weighted_alpha,
        seed=seed,
        neutron_cluster_windows=neutron_cluster_windows,
        refine_passes=refine_passes,
    )
    outputs: list[dict[str, Any]] = []
    for method, base in base_results.items():
        for view in ("row_only", "native"):
            row_perm = list(base["row_perm"])
            native_col_perm = base["col_perm"] if base["col_perm"] is not None else list(range(matrix.n_cols))
            col_perm = None if view == "row_only" else list(native_col_perm)
            supports = _remapped_supports(matrix, col_perm)
            inverse = inverse_permutation(row_perm)
            adjacency = adjacency_metrics(row_perm, supports, weighted_alpha=weighted_alpha, matrix=matrix if weighted_alpha else None)
            windows, window_summary = window_metrics(row_perm, supports, w16=w16, n_cols=matrix.n_cols, k16_width=K16)
            correctness = _validate_row_permutation(matrix, row_perm, inverse)
            correctness["native_row_column_semantics_preserved"] = _validate_native_permutation(matrix, row_perm, native_col_perm)
            payload = {
                "matrix": matrix.name,
                "matrix_shape": [matrix.n_rows, matrix.n_cols],
                "matrix_nnz": matrix.nnz,
                "method": method,
                "view": view,
                "row_perm": row_perm,
                "inverse_row_perm": inverse,
                "optional_col_perm": col_perm,
                "method_config": {**base["method_config"], "view": view, "column_reordering_applied": view == "native" and base["col_perm"] is not None},
                "adjacency_metrics": adjacency,
                "W16_window_metrics": {"summary": window_summary, "windows": windows},
                "preprocessing_time_seconds": base["preprocessing_time_seconds"],
                "graph_statistics": base["graph_statistics"],
                "correctness": correctness,
            }
            outputs.append(payload)
    return {
        "experiment": "RSH row reordering structure experiment",
        "scope": "row/column order and W16 structural metrics only",
        "matrix": {"name": matrix.name, "n_rows": matrix.n_rows, "n_cols": matrix.n_cols, "nnz": matrix.nnz},
        "config": {"w16": w16, "k16": K16, "rsh_k": k, "weighted_alpha": weighted_alpha, "seed": seed, "neutron_cluster_windows": neutron_cluster_windows, "rsh_refine_passes": refine_passes, "methods": ["original", "rsh", "rabbit", "neutron"], "views": ["row_only", "native"]},
        "outputs": outputs,
    }


def _flatten_method_row(output: Mapping[str, Any]) -> dict[str, Any]:
    adjacency = output["adjacency_metrics"]
    summary = output["W16_window_metrics"]["summary"]
    graph = output["graph_statistics"]
    return {
        "matrix": output["matrix"],
        "method": output["method"],
        "view": output["view"],
        "preprocessing_time_seconds": output["preprocessing_time_seconds"],
        "average_adjacent_similarity": adjacency["average_adjacent_similarity"],
        "average_adjacent_dissimilarity": adjacency["average_adjacent_dissimilarity"],
        "cumulative_adjacent_dissimilarity": adjacency["cumulative_adjacent_dissimilarity"],
        "adjacent_overlap_fraction": adjacency["adjacent_overlap_fraction"],
        "high_similarity_adjacent_fraction": adjacency["high_similarity_adjacent_fraction"],
        "window_count": summary["window_count"],
        "mean_unique_columns": summary["mean_unique_columns"],
        "mean_k16_count": summary["mean_k16_count"],
        "mean_run_count": summary["mean_run_count"],
        "mean_average_run_length": summary["mean_average_run_length"],
        "mean_occupancy": summary["mean_occupancy"],
        "graph_components": graph.get("graph_components", graph.get("bipartite_components", 0)),
        "graph_edges": graph.get("graph_edges_undirected", graph.get("graph_edges_bipartite", 0)),
        "correct": all(output["correctness"].values()),
    }


def _svg_bar_chart(path: Path, title: str, labels: Sequence[str], series: Mapping[str, Sequence[float]], y_label: str) -> None:
    width, height = 1080, 560
    left, right, top, bottom = 80, 30, 70, 130
    plot_width, plot_height = width - left - right, height - top - bottom
    all_values = [float(value) for values in series.values() for value in values]
    maximum = max(all_values, default=1.0)
    maximum = maximum if maximum > 0 else 1.0
    colors = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd"]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">']
    parts.append('<rect width="100%" height="100%" fill="white"/>')
    parts.append(f'<text x="{width/2:.1f}" y="32" text-anchor="middle" font-family="Arial" font-size="20" font-weight="bold">{html.escape(title)}</text>')
    parts.append(f'<text x="20" y="{top + plot_height/2:.1f}" transform="rotate(-90 20 {top + plot_height/2:.1f})" text-anchor="middle" font-family="Arial" font-size="13">{html.escape(y_label)}</text>')
    for tick in range(6):
        value = maximum * tick / 5
        y = top + plot_height - (plot_height * value / maximum)
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left+plot_width}" y2="{y:.1f}" stroke="#e5e7eb"/>')
        parts.append(f'<text x="{left-8}" y="{y+4:.1f}" text-anchor="end" font-family="Arial" font-size="11">{value:.2f}</text>')
    parts.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+plot_height}" stroke="#374151"/>')
    parts.append(f'<line x1="{left}" y1="{top+plot_height}" x2="{left+plot_width}" y2="{top+plot_height}" stroke="#374151"/>')
    category_count = max(1, len(labels))
    series_items = list(series.items())
    group_width = plot_width / category_count
    bar_width = group_width / max(1, len(series_items) + 1)
    for index, label in enumerate(labels):
        base_x = left + index * group_width
        for series_index, (series_name, values) in enumerate(series_items):
            value = float(values[index]) if index < len(values) else 0.0
            bar_height = plot_height * value / maximum
            x = base_x + (series_index + 0.35) * bar_width
            y = top + plot_height - bar_height
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(2, bar_width*0.75):.1f}" height="{bar_height:.1f}" fill="{colors[series_index % len(colors)]}"/>')
        label_x = base_x + group_width / 2
        parts.append(f'<text x="{label_x:.1f}" y="{top+plot_height+20}" text-anchor="middle" font-family="Arial" font-size="10" transform="rotate(35 {label_x:.1f} {top+plot_height+20})">{html.escape(label)}</text>')
    legend_x = left
    for series_index, series_name in enumerate(series):
        x = legend_x + series_index * 190
        parts.append(f'<rect x="{x}" y="{height-35}" width="12" height="12" fill="{colors[series_index % len(colors)]}"/>')
        parts.append(f'<text x="{x+18}" y="{height-25}" font-family="Arial" font-size="12">{html.escape(series_name)}</text>')
    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def write_outputs(result: Mapping[str, Any], output_dir: str | Path) -> Path:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    matrix_name = result["matrix"]["name"]
    for payload in result["outputs"]:
        filename = f"{matrix_name}__{payload['method']}__{payload['view']}.json"
        (output / filename).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    method_rows = [_flatten_method_row(payload) for payload in result["outputs"]]
    method_fields = list(method_rows[0]) if method_rows else ["matrix", "method", "view"]
    with (output / "method_metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=method_fields)
        writer.writeheader()
        writer.writerows(method_rows)
    window_fields = ["matrix", "method", "view", "window_id", "start", "row_count", "nnz", "unique_columns", "k16_count", "padded_columns", "occupancy", "column_span", "run_count", "average_run_length", "maximum_run_length", "normalized_union", "column_reuse"]
    with (output / "window_metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=window_fields)
        writer.writeheader()
        for payload in result["outputs"]:
            for window in payload["W16_window_metrics"]["windows"]:
                writer.writerow({field: window.get(field, "") for field in window_fields} | {"matrix": payload["matrix"], "method": payload["method"], "view": payload["view"]})
    (output / "manifest.json").write_text(json.dumps({key: value for key, value in result.items() if key != "outputs"}, ensure_ascii=False, indent=2), encoding="utf-8")
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in method_rows:
        grouped[(row["method"], row["view"])].append(row)
    labels = [f"{row['method']}\n{row['view']}" for row in method_rows]
    adjacency_values = [float(row["average_adjacent_similarity"]) for row in method_rows]
    union_values = [float(row["mean_unique_columns"]) for row in method_rows]
    run_values = [float(row["mean_run_count"]) for row in method_rows]
    _svg_bar_chart(output / "row_order_structure_comparison.svg", "Adjacent row similarity by method and view", labels, {"average similarity": adjacency_values}, "Jaccard similarity")
    _svg_bar_chart(output / "W16_window_nonzero_union.svg", "W16 window nonzero-column union", labels, {"mean unique columns": union_values}, "columns")
    _svg_bar_chart(output / "continuous_run_distribution.svg", "W16 window continuous-column runs", labels, {"mean run count": run_values}, "runs per window")
    (output / "experiment_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def write_batch_outputs(results: Sequence[Mapping[str, Any]], output_dir: str | Path) -> Path:
    """Write per-matrix artifacts plus method×matrix aggregate tables."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    matrix_dirs: list[str] = []
    used_names: set[str] = set()
    for index, result in enumerate(results):
        raw_name = str(result["matrix"]["name"])
        safe_name = "".join(char if char.isalnum() or char in "._-" else "_" for char in raw_name).strip("._") or f"matrix_{index}"
        candidate = safe_name
        suffix = 1
        while candidate in used_names:
            suffix += 1
            candidate = f"{safe_name}_{suffix}"
        used_names.add(candidate)
        matrix_dirs.append(candidate)
        write_outputs(result, output / candidate)
    method_rows = [_flatten_method_row(payload) for result in results for payload in result["outputs"]]
    method_fields = list(method_rows[0]) if method_rows else ["matrix", "method", "view"]
    with (output / "method_metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=method_fields)
        writer.writeheader()
        writer.writerows(method_rows)
    window_fields = ["matrix", "method", "view", "window_id", "start", "row_count", "nnz", "unique_columns", "k16_count", "padded_columns", "occupancy", "column_span", "run_count", "average_run_length", "maximum_run_length", "normalized_union", "column_reuse"]
    with (output / "window_metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=window_fields)
        writer.writeheader()
        for result in results:
            for payload in result["outputs"]:
                for window in payload["W16_window_metrics"]["windows"]:
                    writer.writerow({field: window.get(field, "") for field in window_fields} | {"matrix": payload["matrix"], "method": payload["method"], "view": payload["view"]})
    labels = [f"{row['matrix']}/{row['method']}\n{row['view']}" for row in method_rows]
    _svg_bar_chart(output / "row_order_structure_comparison.svg", "Adjacent row similarity by matrix, method, and view", labels, {"average similarity": [float(row["average_adjacent_similarity"]) for row in method_rows]}, "Jaccard similarity")
    _svg_bar_chart(output / "W16_window_nonzero_union.svg", "W16 window nonzero-column union", labels, {"mean unique columns": [float(row["mean_unique_columns"]) for row in method_rows]}, "columns")
    _svg_bar_chart(output / "continuous_run_distribution.svg", "W16 window continuous-column runs", labels, {"mean run count": [float(row["mean_run_count"]) for row in method_rows]}, "runs per window")
    manifest = {
        "experiment": "RSH row reordering structure experiment",
        "matrix_count": len(results),
        "matrix_output_dirs": matrix_dirs,
        "matrices": [result["matrix"] for result in results],
        "configs": [result["config"] for result in results],
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "batch_experiment_result.json").write_text(json.dumps({"manifest": manifest, "results": list(results)}, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the RSH row-reordering structure experiment.")
    parser.add_argument("--input", action="append", help="Matrix Market (.mtx/.mtx.gz), JSON, CSV edge list, or CSR NPZ input; repeat for a batch.")
    parser.add_argument("--output-dir", default="rsh-reorder-results", help="Directory for JSON, CSV, SVG, and manifest outputs.")
    parser.add_argument("--w16", type=int, default=16, help="Evaluation window height (default: 16).")
    parser.add_argument("--rsh-k", type=int, default=8, help="Fixed RSH candidate graph degree (default: 8).")
    parser.add_argument("--weighted-alpha", type=float, default=0.0, help="Fixed support-weight exponent; 0 selects ordinary Jaccard.")
    parser.add_argument("--seed", type=int, default=0, help="Recorded global seed for reproducibility.")
    parser.add_argument("--neutron-cluster-windows", type=int, default=8, help="Neutron simplified cluster target in W16 windows (default: 8).")
    parser.add_argument("--rsh-refine-passes", type=int, default=2, help="Fixed bounded local refinement passes (default: 2).")
    parser.add_argument("--synthetic-rows", type=int, default=192, help="Synthetic rows when --input is omitted.")
    parser.add_argument("--synthetic-cols", type=int, default=192, help="Synthetic columns when --input is omitted.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    matrices = [load_sparse_matrix(path) for path in args.input] if args.input else [synthetic_matrix(args.synthetic_rows, args.synthetic_cols, args.seed)]
    results = [
        run_experiment(
            matrix,
            w16=args.w16,
            k=args.rsh_k,
            weighted_alpha=args.weighted_alpha,
            seed=args.seed,
            neutron_cluster_windows=args.neutron_cluster_windows,
            refine_passes=args.rsh_refine_passes,
        )
        for matrix in matrices
    ]
    output = write_outputs(results[0], args.output_dir) if len(results) == 1 else write_batch_outputs(results, args.output_dir)
    correctness = all(all(payload["correctness"].values()) for result in results for payload in result["outputs"])
    print(json.dumps({"output_dir": str(output), "matrices": [result["matrix"] for result in results], "all_correct": correctness, "output_count": sum(len(result["outputs"]) for result in results)}, ensure_ascii=False))
    return 0 if correctness else 2


if __name__ == "__main__":
    raise SystemExit(main())
