"""Prepare deterministic, coordinate-labelled inputs for E0 on Ascend 910B2.

This exports the existing V1 Cube route without invoking row reordering or routing.
K in a case name is the compressed window width; original B row numbers are spaced
three apart so a sequential-row gather cannot accidentally pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rsh.planner import Matrix, execute_cpu
from rsh.prepare import export


def make_case(root: Path, m: int, compressed_k: int, n: int) -> dict:
    original_cols = np.arange(compressed_k, dtype=np.int32) * 3 + 1
    global_k = int(original_cols[-1]) + 1
    a_values = np.fromfunction(
        lambda row, k: ((row * 11 + k * 7) % 17 - 8) / 8,
        (m, compressed_k), dtype=int,
    ).astype(np.float16)
    b = np.fromfunction(
        lambda row, col: ((row * 13 + col * 5) % 19 - 9) / 8,
        (global_k, n), dtype=int,
    ).astype(np.float16)
    ptr = np.arange(m + 1, dtype=np.int32) * compressed_k
    cols = np.tile(original_cols, m)
    a = Matrix(ptr, cols, a_values.reshape(-1), (m, global_k))

    group_count = (m + 15) // 16
    k_tiles = (compressed_k + 15) // 16
    tiles = np.zeros((group_count * k_tiles, 16, 16), dtype=np.float16)
    refs = np.full((group_count * k_tiles, 16), global_k, dtype=np.int32)
    rowmap = np.full((group_count, 16), -1, dtype=np.int32)
    for group in range(group_count):
        for local_row in range(16):
            row = group * 16 + local_row
            if row < m:
                rowmap[group, local_row] = row
                for tile in range(k_tiles):
                    lo = tile * 16
                    hi = min(lo + 16, compressed_k)
                    tiles[group * k_tiles + tile, local_row, : hi - lo] = a_values[row, lo:hi]
        refs[group * k_tiles : (group + 1) * k_tiles].reshape(-1)[:compressed_k] = original_cols

    plan = {
        "variant": "V1",
        "cube_ptr": np.arange(group_count + 1, dtype=np.int64) * k_tiles,
        "colref": refs.reshape(-1),
        "tiles": tiles,
        "rowmap": rowmap.reshape(-1),
        "srows": np.empty(0, dtype=np.int32),
        "valid": np.ones(m, dtype=np.uint8),
    }
    golden = (a_values.astype(np.float64) @ b[original_cols].astype(np.float64)).astype(np.float32)
    np.testing.assert_array_equal(execute_cpu(a, plan, b), golden)

    name = f"M{m}_K{compressed_k}_N{n}"
    out = root / name / "V1"
    export(a, plan, b, golden, out, {
        "experiment": "E0",
        "compressed_k": compressed_k,
        "original_col_rule": "3*j+1",
        "coordinate_values": "A=((row*11+j*7)%17-8)/8; B=((global_row*13+n*5)%19-9)/8",
        "group_count": group_count,
        "padding_k_slots_per_group": 16 * k_tiles - compressed_k,
        "reference_arithmetic": "FP16 inputs, FP64 matmul, FP32 output",
    })
    return {
        "name": name,
        "m": m,
        "compressed_k": compressed_k,
        "global_k": global_k,
        "n": n,
        "group_count": group_count,
        "k_tiles_per_group": k_tiles,
        "case_dir": f"{name}/V1",
        "max_abs_golden": float(np.max(np.abs(golden))),
        "files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir()) if p.is_file()},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    cases = [make_case(args.out, 16, k, n) for k in (16, 32, 48)
             for n in (16, 17, 32, 33, 64)]
    cases.append(make_case(args.out, 30, 70, 40))
    manifest = {"schema": "rsh-e0-input-v1", "cases": cases}
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Prepared {len(cases)} E0 V1 cases at {args.out}")


if __name__ == "__main__":
    main()
