# T23 双机分工交接：Windows 16 GB 执行端

本文件直接交给另一台电脑上的执行 agent。只执行本交接分配的 20 个案例；原 Mac 继续其余 21 个。当前组已经完整结束并留证；本机已改为按所有权清单调度。没有提交或推送。

## 1. 范围与所有权

- split_id：`T23-split-20261109`。
- 仓库：`https://github.com/pangxiegonghhh/rsh-npu-experiments-claude`。
- 冻结 commit：`3ecc8f4ae0f6a7dff556fe1ad4e888a500f3162b`。
- 冻结 tree：`54dd7a113c4ecad145e07b47d8745f9de7d56756`。
- 原计划共 409 例；分工时 368 例已有最终状态，41 例尚未完整结束。
- Windows 执行端 `hostB-windows16gb-wsl2`：20 例、488 个正式条件。
- Mac 执行端 `hostA-macos-arm64`：21 例、按完整案例计 476 个条件；其中部分阶段已经完成，不能重跑。
- 分工按完整案例数量约半分，不声称两组耗时相等。两个集合互斥、并集恰好为分工时的 41 例。
- 唯一机器可读分工是 `assignment.json`；另见 `remote-cases.json`、`local-cases.json`、`partition.csv`。

远端全部是 `ogbn-products`、`W=16`、`seed=0`，方法如下：

|组别|方法|
|---|---|
|基线与历史参照|B0、B1、B-RCM-ref、rabbit-pilot、neutron-pilot|
|P0 候选|C9-Gorder、C9-S、C10-BP、C2-LSH、C3-W1、C3-W4、C4-U、C4-T、C7-I|
|P1 候选|C3-A、C3-W4-noP、C3-W4-R、C3-A-R、C4-U-R、C4-T-R|

本机保留所有剩余 Reddit 案例，以及 products 的 C1-J、C1-H、C5、C5-U、C8-METIS、C7-I-R、C5-CN、C5-U-CN、C6-HP。远端不要执行这些案例，也不要重新跑 T22 或第一批矩阵。

## 2. 必须阅读与硬约束

先读包内 `reference_docs/T22-AGENT-README.md`、`reference_docs/T23-AGENT-README.md`，以及冻结仓库内：

1. `第一层工作区/T23派发/说明.md`。
2. `第一层工作区/首轮候选比较实验方案.md`。
3. 本包 `assignment.json` 与本文件。

以本次明确分工为执行范围；文件中历史“继续跑全部任务”的文字不是让远端扩展所有权。只用 CPU，不用 NPU；不改冻结仓库文件；工作目录、脚本、输出均在仓库外；不提交、不推送；不创建或联系其他 agent。

参数保持：A0/A1；products 的 τ=2、3；全行与方案规定 tail/tail-co、own/D-greedy 条件；co-chain 守卫 400；每方法/每 post 命令 7200 秒，排队时间另计；工作空间/进程限额 8 GiB；P-LS λ=0、seed=0、最多 10 轮，零接受可按原停止规则结束。不能为跑完而减候选数、改阈值、加内存限额、延长时限或截断输入。

每例自身评估 20 行。B0、B1 及本包中的 P0 候选还须完成两个 τ 的 post-E，共另加 8 行；三个历史参照与六个 P1 候选没有新增 post-E。488 行的完整条件集合必须保留，包括失败占位及原因。

## 3. Windows 环境

使用 WSL2 Ubuntu，建议 Ubuntu 24.04；在 Linux 文件系统（例如 `~/t23-remote-runtime`）内运行，不在 `/mnt/c` 运行大图。先记录 Windows/WSL/Linux 版本、CPU 型号、`uname -m`、物理内存、WSL 内存限制、编译器和 Python/NumPy/SciPy 版本。用户只确认 Windows、16 GB，CPU 架构尚未确认，须实测。

16 GB 主机可把 WSL 内存上限设为约 12 GB，给 Windows 保留空间；实验单进程 8 GiB 门槛保持不变。同机保留两个普通槽位、大图串行、一线程环境变量，不擅自同时运行两个 products 大图。

参考安装：

```bash
sudo apt-get update
sudo apt-get install -y python3-venv python3-dev g++ gcc make
python3 -m venv .venv
. .venv/bin/activate
python -m pip install numpy==2.4.4 scipy==1.17.1
```

如果指定版本无法安装，先保存真实报错和环境，不伪造版本或门禁结果；可评估兼容版本，但必须记录差异并重新通过全部相关 Cora 门禁。分配的 20 例不需要安装 PyNNDescent、METIS、KaHyPar，也不需要启动 Rabbit VM。

## 4. 传输材料与目录

两个传输包解到同一个 `t23-remote-runtime/`：源码包与输入包。收到后先核验随包 SHA256SUMS。

```text
t23-remote-runtime/
  assignment.json
  scripts/                 # 本轮加速实现与调度器源码
  repo/                    # 冻结仓库导出，保持只读
  reference_docs/          # 两份 AGENT README
  reference_evidence/      # Mac 上已验证证据，仅供参考，不算远端新 PASS
  logs/matrices-and-taus.json
  logs/reused-orders.json
  work/matrices/cora/      # Cora 门禁输入
  work/matrices/ogbn-products/
  work/rabbit-coarse/      # genuine products-U 缓存及原始来源记录
  native_sources/accelerate-v8.cpp
```

products A0：n=2,449,029，nnz=123,718,024，空行 48,421；原始边文件含 128 个对角条目，按 A0 定义去掉。不要为匹配论文条目数改图；A1 加 I，D 集按 A0 度固定。τ=2、3，τ=3 的残余比例约 12.756%。实际精确值以包内矩阵元数据为准。

CSR 类型必须保持：indptr int64；indices int32；degrees int32。结构按存储条目定义，显式零保留；不以数值非零筛边。

输入来源与原始 SHA：

- `products-edge.csv.gz`：`a012950cc853f8262d5bbc9d93ca393e978e1e8f34bcf639125585dc3b515341`。
- `products-num-nodes.csv.gz`：`59a706d20daab9a2612b81fb6a99902a086e4d4c861776df69abea69ffeea2e1`。
- 下载 URL、ZIP member/CRC、缓存 CSR 的逐文件 SHA 见输入清单及原始下载记录；没有完整下载的 ZIP 不得编造整包 SHA。

## 5. Linux 移植与编译

包内 `.cpp/.c` 是源码；Mac 的 Mach-O 动态库不能在 WSL 使用。重新编译 Linux ELF 动态库。现有 Python 用 `.dylib` 文件名，Linux `ctypes.CDLL` 可以加载同名 ELF；不要把 Mac 二进制复制过去冒充编译成功。

编译使用 C++17、O3、`-ffp-contract=off -shared -fPIC`。对应关系：

|输出文件|源码|
|---|---|
|work/liblayouts-v7.dylib|scripts/layouts_flatco.cpp|
|work/liblayouts-v4.dylib（门禁参照）|scripts/layouts_cached.cpp|
|work/libcandidates-v2.dylib|scripts/candidates.cpp|
|work/librect.dylib|scripts/rect.cpp|
|work/liblarge-rcm.dylib|scripts/large_rcm.cpp|
|work/librabbit-local.dylib（-R 导入依赖）|scripts/rabbit_local.cpp|
|work/libindependent-sorted.dylib|scripts/independent_sorted.cpp|
|work/t21/librq2-v8.dylib|native_sources/accelerate-v8.cpp|
|work/libslashburn.dylib（Cora 表格门禁依赖）|scripts/t21/slashburn.cpp|
|work/libmemory-guard.dylib|scripts/memory_guard.c（gcc、pthread）|

源码包中的准备脚本只做路径迁移、Linux 内存单位适配和编译；本文件不声称已在 Windows/WSL 上执行验证。执行 agent 必须检查构建 stderr/返回码、源码/ELF SHA 和实际加载路径，再跑下一节门禁。

特别注意：macOS 的 `ru_maxrss` 是 bytes，Linux 是 KiB。Python 报表里的 `/2**20` 要按平台正确换算 MiB，保留原源码、改动 diff 与 SHA；不能让 Linux 内存报表缩小 1024 倍。C 内存守卫已有非 Apple 的 ×1024 分支，不能再乘一次。此适配只改报表单位，不改 8 GiB 实验门槛或数值算法。

`-R` 必须使用随包 genuine Rabbit-U 映射。`parent.runtime_path` 的 Mac 绝对路径需要迁移到解包后的实际路径；先字节保存原记录，再创建明确标注的迁移记录，保留原记录 SHA、映射 SHA、author ref、原 coarse_seconds 和原主机来源。不得重跑粗排后混用旧计时，不得以 BFS/pilot 替代 genuine Rabbit。

Rabbit 没有种子接口，重复编号 0 只是 requested replica label，actual seed=null；候选/P-LS 本身的 seed=0 按原实现执行。继承的 coarse_seconds 与本机新阶段耗时分开记录；历史 coarse 内存不是本机进程峰值。

## 6. 在远端重新通过门禁后才能开跑

Mac 的历史 PASS 不算 WSL 的新门禁。先在仓库外的新空目录运行参考自检，保留命令、cwd、stdout/stderr、退出码、源码 SHA：

1. T21 `reproduce_cora.py`：首行 `Table A self-check: OK`、退出码 0。
2. T22 `reproduce_cora_rq3.py`：Table 1/2 自检通过。
3. T23 `reproduce_cora_t23.py`：首行 `T23 Cora self-check: OK`、8 个行序 SHA 匹配。
4. 官方 `conditions_ref.py --cora-selfcheck`：40 条条件通过；toy 与独立参照按原 README 执行。
5. 候选、Rect、LS 全行/空行、v7 布局、独立 sorted 计数门禁全部通过。原脚本入口包括 `gate_candidates.py`、`gate_rect.py`、`gate_ls_full.py`、`gate_layouts_v7.py`、`gate_independent_sorted.py`。
6. v7 相对于 v4 的指定库选择必须真实生效；v7 相关门禁对子进程设置 `RQ3_LAYOUT_LIB` 为本机 `work/liblayouts-v7.dylib`，不能把参照也偷偷指向候选。
7. 检查 Linux RSS 单位与原生 8 GiB 守卫能真实工作。合成小限额夹具不能当作正式矩阵实验；不在正式任务中保留小限额。

可用 `scripts/run_reference_gates.py` 编排参考门禁。Cora 的 C4-U 输入及其他门禁输入按源脚本需要从参考结果生成；不修改官方 expected 文件来消除差异。若跨标准库造成行序不同，应查明并修复忠实移植后重新过门禁，不能只凭指标接近放行。

成功后写 `logs/remote-readiness.json`，记录 `passed=true`、`fresh_remote_gates=true`、host_id、split_id 和真实新门禁证据。`gate_receipts` 每项含 category、相对 path、sha256；必须覆盖：`reference_tables`、`official40`、`candidate_equivalence`、`layout_v7`、`LS_full`、`independent_sorted`、`memory_guard_units`。不得先填 PASS 再跑实验。

随包提供以下入口；脚本只有真实完成检查后才写 readiness：

```bash
python -B tools/prepare_wsl.py
python -B tools/run_fresh_gates.py
```

这两个入口尚未在本次 Windows 电脑执行，必须由接手 agent 核验实际退出码与日志。若门禁失败，停在该门禁，不启动 products，也不修改 expected。

## 7. 唯一正式执行入口

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMBA_NUM_THREADS=1 MKL_NUM_THREADS=1 \
PYTHONDONTWRITEBYTECODE=1 python -B scripts/run_stage3_assigned.py \
  --owner remote --assignment assignment.json --readiness logs/remote-readiness.json
```

**不要运行 `scripts/run_stage3.py` 的 main，它会提交完整 409 例。** 分工入口只过滤所有权，内部仍调用原 `run_stage3.run`，不改算法、候选数、τ、种子、停止规则或时间/内存限额。

已有某阶段真实完整记录时按原恢复规则复用；新的实验/修复使用新目录并保留旧证据。失败、超时、内存估算拒绝、实际 RSS 守卫、未测必须区分。生成 record.status=OK 不等于整例通过；必须检查 20 行自身评估及应有 8 行 post-E。

P-LS 超时只保留最后完整轮次检查点；没有最终布局的行仍为 INCOMPLETE。独立回收的计算用时另记，不冒充原 P-LS 时间；不重跑 LS/D 来补成 PASS。不要把检查点 status 原文改成 OK。

完成远端 20 例后，执行 products 至少 3 个有效行序的独立计数核验，保留具体行序、条件、输入 SHA、核验源码与日志。该要求不是“每个新候选都重新测一遍”，也不能声称窄抽样核验覆盖了所有布局。

随包 `python -B tools/finish_remote.py` 会执行该独立核验，并收集/检查 20 例、488 行条件；失败状态保持原样。返回材料按下一节整理。它不会创建全局完成标记或封存整个项目。

## 8. 交回内容与合并边界

交回以下材料，保持相对目录结构；先生成逐文件 SHA256SUMS，再独立读回压缩包核验：

- assignment/split_id、20 个 case_id 的阶段与正式条件状态表（488 行完整条件集合）。
- `work/stage3-cases/<case_id>/record.json`；对应生成、评估、诊断、post-E 原始目录与 catalog。
- 全部 command/stdout/stderr、退出码、排队/实际用时、RSS 守卫、原始 CP、pre-repair/阶段记录（如有）。
- 新门禁、独立核验、环境/版本/CPU/WSL 配置、源码、Linux ELF 及 SHA、内存单位适配 diff。
- 所有新行序的路径、大小、SHA 与来源。行序合计超过 50 MiB 时，正式结果包只放清单；将行序目录另行通过文件夹传输交回，不能把“没有复制的本地路径”写成已回收。
- `logs/stage3-remote-split-complete.json`。不得写全局 `stage3-run-complete.json`，也不要执行全局 build/seal。

原始记录里的 WSL 绝对路径保持原文。主机 A 导入时会创建有明确来源的本地路径投影并保留远端原件；不得直接覆写 Mac 原结果。CPU 用时按执行主机分别标注，不混成同一环境的性能结论。

本机只有在远端 20 例原件、行序和哈希均回收核验后才创建 `remote-split-import-verified.json`；所有 409 例真实终止记录齐备后才释放旧 finalizer。不会创建 DELEGATED/SKIPPED 假实验记录来凑 409，也不会在远端尚未交回时封存最终结果。

## 9. 当前本机状态与下一位 agent 的第一条操作

本机原调度器在当前 τ=53 数值组与已排队诊断正常结束后退役。两个尚未取得 CPU 槽位的后续进程被行政取消，原命令和空 stdout/stderr 已原样备份；不记科学失败，不重跑已完成数值阶段。临时准入控制代码已恢复原字节。新本机调度器只领本机 21 例；远端 20 例已验证从未启动。

本机已继续 C5-U τ=153；后续本机案例继续自动执行。两份已封存的 T22/第一阶段 T23 归档保持不变。

远端第一条操作：确认 WSL2 与实际架构/内存，核验两个传输包 SHA，读本文件和两份 AGENT README；随后检查源码与 Linux 适配，重新执行第 6 节门禁。门禁通过后只运行第 7 节的 assigned 入口。
