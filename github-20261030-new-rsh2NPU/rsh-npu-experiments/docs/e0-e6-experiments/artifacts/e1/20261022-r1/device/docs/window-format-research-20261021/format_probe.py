"""CPU semantic/layout probe for the proposed W16 formats, not a device benchmark.

Run from any directory: python3 /absolute/path/to/format_probe.py
Only synthetic fixed windows are constructed; no row reordering or routing runs.
"""
from pathlib import Path
import hashlib
import json
import struct
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SEED = 20261021
KINDS = {"dense": 0, "bitmap": 1, "local_index": 2, "dense_tail": 3}
DESC = struct.Struct("<QHBBI")  # offset, nnz, kind, valid K, payload bytes


def align32(n):
    return (n + 31) // 32 * 32


def encode(tiles, kind, valid_ks=None):
    payload, descriptors = bytearray(), bytearray()
    for tile_id, tile in enumerate(tiles):
        flat = np.asarray(tile, dtype="<f2").reshape(256)
        assert np.isfinite(flat).all()
        valid_k = 16 if valid_ks is None else int(valid_ks[tile_id])
        assert 1 <= valid_k <= 16
        assert not np.any(flat.reshape(16, 16)[:, valid_k:])
        ids = np.flatnonzero(flat != 0)
        values = flat[ids].tobytes()
        if kind == "dense":
            raw = flat.tobytes()
        elif kind == "bitmap":
            masks = [sum(1 << k for k in range(16) if flat[r * 16 + k] != 0)
                     for r in range(16)]
            raw = np.asarray(masks, dtype="<u2").tobytes() + values
        elif kind == "local_index":
            # Keep the FP16 value stream two-byte aligned inside the byte payload.
            raw = ids.astype(np.uint8).tobytes() + bytes(len(ids) % 2) + values
        else:
            raw = flat.reshape(16, 16)[:, :valid_k].copy().tobytes()
        descriptors.extend(DESC.pack(len(payload), len(ids), KINDS[kind], valid_k, len(raw)))
        payload.extend(raw)
        payload.extend(bytes(align32(len(payload)) - len(payload)))
    return bytes(descriptors), bytes(payload)


def decode(descriptors, payload):
    result = []
    for offset, nnz, kind, valid_k, size in DESC.iter_unpack(descriptors):
        assert 1 <= valid_k <= 16 and offset % 32 == 0 and nnz <= 256
        assert offset + size <= len(payload)
        raw = payload[offset:offset + size]
        flat = np.zeros(256, np.float16)
        if kind == KINDS["dense"]:
            assert size == 512
            flat[:] = np.frombuffer(raw, dtype="<f2")
        elif kind == KINDS["bitmap"]:
            assert size == 32 + 2 * nnz
            masks = np.frombuffer(raw[:32], dtype="<u2")
            ids = [r * 16 + k for r in range(16) for k in range(16)
                   if int(masks[r]) & (1 << k)]
            assert len(ids) == nnz
            flat[ids] = np.frombuffer(raw[32:], dtype="<f2")
        elif kind == KINDS["local_index"]:
            prefix = nnz + nnz % 2
            assert size == prefix + 2 * nnz
            ids = np.frombuffer(raw[:nnz], dtype=np.uint8).astype(np.int32)
            assert np.all(np.diff(ids) > 0)
            flat[ids] = np.frombuffer(raw[prefix:], dtype="<f2")
        else:
            assert kind == KINDS["dense_tail"] and size == 32 * valid_k
            flat.reshape(16, 16)[:, :valid_k] = np.frombuffer(raw, dtype="<f2").reshape(16, valid_k)
        assert np.count_nonzero(flat) == nnz
        assert not np.any(flat.reshape(16, 16)[:, valid_k:])
        result.append(flat.reshape(16, 16))
    return np.asarray(result, np.float16).reshape(-1, 16, 16)


def run():
    rng = np.random.default_rng(SEED)
    semantic_checks = layout_checks = 0
    # Probe every occupancy including z=0 and z=256 (uint16 nnz is necessary).
    for z in range(257):
        a = np.zeros(256, np.float16)
        ids = rng.choice(256, z, replace=False)
        a[ids] = rng.choice([-2, -1, .5, 1, 2], z)
        for kind in KINDS:
            desc, data = encode(a.reshape(1, 16, 16), kind)
            np.testing.assert_array_equal(decode(desc, data), a.reshape(1, 16, 16))
            semantic_checks += 1

    cases = []
    for u in [0, 1, 15, 16, 17, 31, 32, 37, 48, 63]:
        cols = np.sort(rng.choice(4099, u, replace=False)).astype(np.int32)
        t = (u + 15) // 16
        for density in [.0625, .25, .75, 1.]:
            compact = rng.integers(-8, 9, (16, u)).astype(np.float16) / 4
            compact[rng.random((16, u)) > density] = 0
            for j in range(u):
                compact[j % 16, j] = 1  # Every column really belongs to the union.
            original = np.zeros((16, 4099), np.float16)
            original[:, cols] = compact
            padded = np.zeros((16, t * 16), np.float16)
            padded[:, :u] = compact
            tiles = padded.reshape(16, t, 16).transpose(1, 0, 2).copy()
            refs = np.full(t * 16, 4099, np.int32)
            refs[:u] = cols
            for n in [1, 16, 17, 32, 33, 64]:
                npad = (n + 15) // 16 * 16
                b = rng.integers(-8, 9, (4099, n)).astype(np.float16) / 4
                bp = np.zeros((4100, npad), np.float16)
                bp[:4099, :n] = b
                gold = original.astype(np.float64) @ b.astype(np.float64)
                for kind in KINDS:
                    valid_ks = [min(16, u-j*16) for j in range(t)]
                    desc, data = encode(tiles, kind, valid_ks)
                    restored = decode(desc, data)
                    accum = np.zeros((16, npad), np.float32)
                    for j in range(t):
                        accum += restored[j].astype(np.float32) @ bp[refs[j*16:j*16+16]].astype(np.float32)
                    np.testing.assert_array_equal(accum[:, :n], gold)
                    np.testing.assert_array_equal(accum[:, n:], 0)
                    semantic_checks += 1
                cases.append(dict(unique_columns=u, n=n, density_requested=density, tiles=t))

    # Mathematical physical-layout checks: not an emulation of LoadData timing.
    for q in [1, 2, 3, 4, 8]:
        for npad in [16, 32, 64, 128]:
            a = np.arange(16 * 16 * q).reshape(16, 16 * q)
            anz = a.reshape(1, 16, q, 16).transpose(2, 0, 1, 3).reshape(-1)
            azz = a.reshape(1, 16, q, 16).transpose(0, 2, 1, 3).reshape(-1)
            np.testing.assert_array_equal(anz, azz)  # Only because M1=1.
            b = np.arange(16 * q * npad).reshape(16 * q, npad)
            bnz = b.reshape(q, 16, npad // 16, 16).transpose(2, 0, 1, 3).copy()
            bzn = b.reshape(q, 16, npad // 16, 16).transpose(0, 2, 3, 1).copy()
            transformed = np.empty_like(bzn)
            for kt in range(q):
                for nt in range(npad // 16):
                    transformed[kt, nt] = bnz[nt, kt].T
                    # Independent element-address formula for the L1 layout.
                    for k in range(16):
                        for ni in range(16):
                            off = ((nt * q + kt) * 16 + k) * 16 + ni
                            assert bnz.ravel()[off] == b[kt * 16 + k, nt * 16 + ni]
            np.testing.assert_array_equal(transformed, bzn)
            if q > 1 and npad > 16:
                k_major_panels = bnz.transpose(1, 0, 2, 3).reshape(-1)
                assert not np.array_equal(k_major_panels, bnz.reshape(-1))
            layout_checks += 1

    costs = []
    for z in [0, 16, 32, 64, 128, 192, 224, 239, 240, 256]:
        costs.append(dict(nnz=z, density=z/256, dense_payload=512,
                          bitmap_raw=32+2*z, bitmap_padded=align32(32+2*z),
                          index_raw=3*z+z%2, index_padded=align32(3*z+z%2),
                          descriptor=16, common_colmap_padded=64))
    inventory = []
    for path in sorted((ROOT / "inputs").glob("*.npz")):
        with np.load(path, allow_pickle=False) as x:
            inventory.append(dict(file=str(path.relative_to(ROOT)), shape=x["shape"].tolist(),
                                  stored_values=int(x["values"].size),
                                  sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    refs = ["rsh/planner.py", "npu/work.h", "scripts/prepare_d3.py"]
    result = dict(scope="CPU synthetic fixed-window semantics, physical-layout algebra and byte model only",
                  seed=SEED, numpy=np.__version__, semantic_checks=semantic_checks,
                  layout_checks=layout_checks, window_cases=len(cases),
                  all_checks_passed=True, max_absolute_error=0.0,
                  probe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  code_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in refs},
                  frozen_paths={p:(ROOT/p).exists() for p in ["results/v2/orders", "results/d3/plans", "cases_d3"]},
                  inputs=inventory, costs=costs, cases=cases)
    (HERE / "probe-results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps({k:result[k] for k in ["scope", "semantic_checks", "layout_checks", "window_cases", "all_checks_passed", "max_absolute_error"]}))


if __name__ == "__main__":
    run()
