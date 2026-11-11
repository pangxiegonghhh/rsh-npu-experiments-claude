#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname -- "$(realpath -- "$0")")/.."
exec 9>work/hostB-products-controller.lock
flock -n 9 || { echo "The hostB controller already holds the run lock." >&2; exit 1; }
test ! -e logs/stage3-remote-split-controller.json
test ! -e logs/stage3-remote-split-complete.json
test ! -e work/stage3-cases
test -s logs/remote-readiness.json

exec > logs/hostB-products.stdout 2> logs/hostB-products.stderr
phase=preflight
trap 'status=$?; printf "phase=%s\nexit_code=%s\nended_at=%s\n" "$phase" "$status" "$(date -Iseconds)" > logs/hostB-products.exit; exit "$status"' EXIT
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export NPY_DISABLE_CPU_FEATURES=X86_V3
unset RQ3_LAYOUT_LIB
py=/root/t23-remote-runtime/.venv/bin/python

"$py" -B - <<'PY'
import hashlib
import json
import os
from pathlib import Path

import numpy as np
from scipy import __version__ as scipy_version

def read(path):
    return json.loads(Path(path).read_text())

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

assignment = read("assignment.json")
assert assignment["split_id"] == "T23-split-20261109"
remote = assignment["remote_cases"]
assert remote == read("logs/stage3-planned-cases.json")
assert len(remote) == len({r["case_id"] for r in remote}) == 20
assert {r["case_id"] for r in remote}.isdisjoint(r["case_id"] for r in assignment["local_cases"])
assert all((r["matrix"], r["W"], r["seed"]) == ("ogbn-products", 16, 0) for r in remote)
assert assignment["remote_formal_conditions"] == 488

readiness = read("logs/remote-readiness.json")
assert readiness["passed"] and readiness["fresh_remote_gates"]
assert readiness["split_id"] == assignment["split_id"]
assert readiness["host_id"] == assignment["remote_host_id"]
assert all(sha(r["path"]) == r["sha256"] for r in readiness["gate_receipts"])
assert readiness["preparation_receipt_sha256"] == sha("logs/remote-port-preparation.json")
assert read("logs/layout-port-gate.json")["passed"]
assert read("logs/remote-memory-unit-gate.json")["formal_default_limit_bytes"] == 8 * 2**30

observed = [read(path) for path in Path("logs/layout-context-backends").glob("*.json")]
for script, library in (("gate_layouts_v4.py", "v4"), ("gate_layouts.py", "v7")):
    matches = [r for r in observed if Path(r["argv"][0]).name == script]
    assert len(matches) == 1, (script, matches)
    loaded = matches[0]
    expected_path = Path(f"work/liblayouts-{library}.dylib").resolve()
    assert Path(loaded["library_path"]) == expected_path and loaded["library_sha256"] == sha(expected_path)

assert np.__version__ == "2.4.4" and scipy_version == "1.17.1"
assert np.argsort([-1, -2, 1, -1, -2]).tolist() == [1, 4, 0, 3, 2]
matrix = Path("work/matrices/ogbn-products")
for name, dtype, length in (("indptr", "int64", 2449030), ("indices", "int32", 123718024), ("degrees", "int32", 2449029)):
    a = np.load(matrix / f"{name}.npy", mmap_mode="r")
    assert a.dtype == np.dtype(dtype) and a.shape == (length,), (name, a.dtype, a.shape)
    if name == "indptr":
        assert a[0] == 0 and a[-1] == 123718024
rabbit = read("work/rabbit-coarse/ogbn-products-U-repeat0.record.json")
assert sha(rabbit["runtime_path"]) == rabbit["mapping_sha256"]
assert sha("reference_evidence/coarse-records-original/ogbn-products-U-repeat0.record.json") == rabbit["relocation"]["source_record_sha256"]
print(json.dumps(dict(assignment_sha256=sha("assignment.json"), readiness_sha256=sha("logs/remote-readiness.json"), numpy=np.__version__, scipy=scipy_version, numpy_cpu_features_disabled=os.environ["NPY_DISABLE_CPU_FEATURES"], cases=len(remote), formal_conditions=488, workspace_limit_bytes=8*2**30)), flush=True)
PY

phase=assigned
echo "HOSTB_ASSIGNED_START $(date -Iseconds)"
"$py" -B scripts/run_stage3_assigned.py --owner remote --assignment assignment.json --readiness logs/remote-readiness.json

phase=independent_and_collect
echo "HOSTB_INDEPENDENT_AND_COLLECT_START $(date -Iseconds)"
"$py" -B tools/finish_remote.py

phase=complete
echo "HOSTB_ASSIGNED_AND_VERIFIED $(date -Iseconds)"
