# E0 standalone probes

Scope: Ascend910B2 / CANN9.0.0, FP16 operands, FP32 accumulation. This is a
correctness harness; its elapsed host times are not performance results.

`normal.cpp` and `direct.cpp` build independent single-entry artifacts.
`dual.cpp` deliberately reproduces two kernel entries in one translation unit.
`direct_dual.cpp` plus `normal.cpp` build the controlled split artifact. Keep
this failing diagnostic separate from the usable normal/direct artifacts.

The host wraps every GM payload with 1024-byte guards, rejects unsafe shapes
and B indices before ACL initialization, records synchronized results and actual
Mmad parameters written by the device. Nonzero payload initialization detects
an unexecuted kernel. `E0_GUARD_BYTE=0x36` changes the finite guard pattern for
read-sensitivity tests. Repeated runs rotate A and B signs independently.

From the project root, on the target instance:

```sh
python scripts/e0_supplement.py selfcheck
python scripts/e0_supplement.py prepare inputs
cmake -S npu/e0_probe -B build -DASCEND_CANN_PACKAGE_PATH=/usr/local/Ascend/cann-9.0.0 -DSOC_VERSION=Ascend910B2
cmake --build build -j4
python scripts/e0_supplement.py run inputs build results/normal-all
```

Platform query (target installation ABI and logging library matter):

```sh
g++ -std=c++17 -D_GLIBCXX_USE_CXX11_ABI=0 npu/e0_probe/resources.cpp -I/usr/local/Ascend/cann-9.0.0/aarch64-linux/include -I/usr/local/Ascend/cann-9.0.0/aarch64-linux/asc/include -L/usr/local/Ascend/cann-9.0.0/aarch64-linux/lib64 -ltiling_api -lplatform -lascendcl -lunified_dlog -ldl -o resource_query
./resource_query
```

Full integrated restore/padding checks use `npu/runner_guarded.cpp`, target
`rsh_guarded` in `npu/CMakeLists.txt`, and `scripts/e0_integrated_prepare.py`.
The ordinary production runner retains its original validation behavior.
