# T21 补跑：pattern1 上 C6 / C6-M 的对齐修补（执行说明，2026-11-06）

状态：规划方撰写，交执行方 agent 实施。依据：`第一层工作区/RQ2验证实验方案.md` §6 J2「对齐修补」（2026-11-06 第三次修订）；
决定出处：`讨论记录/2026-11-06/2026-11-06-0922-C6对齐修补与T21补跑.md`。
本说明只补 T21 中 4 个 INCOMPLETE 的用例，不做研究分析，不改动 T21 已交付的任何文件。

---

## 0. 背景（一句话）

T21 里 pattern1 的 C6（mnc = 0）与 C6-M（mnc = 1 / 4 / 16）各有一层二分，KaHyPar 差 1 个顶点没分出精确目标大小，
按原方案整例记 INCOMPLETE（`第一层实验结果/rq2-validate-20261106/logs/pattern1-c6-failure-summary.json`）。
现在方案加了一步「对齐修补」，用改后的 `c6.py` 重跑这 4 个用例。

## 1. 本目录文件

| 文件 | 作用 |
|---|---|
| `c6.py` | T21 实际运行的 `code/runner/c6.py`（sha256 `1a46ada2d8feaca006401b4b41be16eff4a10c9ae6ea84975a45c2b9a0ae70ba`）加上对齐修补后的完整文件，**原样使用，不得再改** |
| `c6.py.diff` | 相对 T21 版 `c6.py` 的差异，供核对 |
| `check_failed_models.py` | 门 1：用 `c6.align_repair` 回放 T21 保存的 4 个失败现场，对照 `expected-repairs.json` |
| `expected-repairs.json` | 规划方用另一份独立实现算出的预期修补结果（挪哪个点、修补后的加权割、修补后标签的 sha256） |

文件 sha256 见本说明末尾 §8。

## 2. 硬约束

- **不改动 T21 的交付**：仓库里的 `第一层实验结果/rq2-validate-20261106/` 与本地完整归档 `t21-rq2-87594cc-20261106.tar.gz` 一个字节都不动；
  T21 工作目录里旧的 `checks/c6__pattern1__*` 轨迹与 `*-failed-model.json` 是失败现场的证据，**不得覆盖**。新产物一律写新目录（§6）。
- 环境与 T21 相同：KaHyPar Python 绑定 1.3.7（T21 记录的模块 sha256 `b8f5fff175a8984baffaa04bcbc2f54726df8e5ca7a27148c927260381bd14b7`）、配置 `kahypar-cut-v1.3.7.ini`
  （T21 记录的 sha256 `64ebd58a4f98b95bf87ae3de5341b2be00b09e122a0526ef65a799e39bb63dd8`）、种子 0、ε = 0、`campaign.py` 与 T21 相同（sha256 `3362199e76a42c5029c70a7b396de4cc71132dd3b7c4cbbbc5df45f5664c9314`）；**只把 `c6.py` 换成本目录的版本**。
  若环境有任何不同（例如 KaHyPar 需要重装），照常进行，但在 README 里写明差异。
- 不放宽 ε、不换种子、不改修补规则或上限 W/2、不手工挪点。修补上限内无法收口的，按 §5 记 INCOMPLETE。
- 不执行仓库 `binaries/` 下的任何文件（那些是 T21 的留痕）。
- 不提交、不推送；产物交给用户入库。

## 3. 三道门（全部通过才报数；任何一道不过，停下并把现场交回）

**门 1：回放失败现场（纯 Python，几秒钟）。**

```bash
python3 -I 第一层工作区/T21补跑-C6对齐修补/check_failed_models.py \
  第一层实验结果/rq2-validate-20261106/checks  <新目录>/checks/gate1-failed-model-replay.json
```

须输出 4 行 `MATCH` 和末行 `Gate 1 (failed-model replay): OK`，退出码 0。预期：

| 用例 | 层（part） | 原始大小 → 目标 | 挪动的全局顶点 | 加权割 |
|---|---|---|---|---|
| C6，mnc = 0 | 106 | [145, 143] → [144, 144] | 19204 | 758 → 756 |
| C6-M，mnc = 1 | 289 | [47, 33] → [48, 32] | 11425 | 806 → 804 |
| C6-M，mnc = 4 | 271 | [47, 33] → [48, 32] | 546 | 980 → 972 |
| C6-M，mnc = 16 | 272 | [49, 31] → [48, 32] | 11194 | 1750 → 1718 |

**门 2：修补不触发时与 T21 逐位相同（cora，每例约 2 秒）。** 用改后的 `c6.py` 在 cora 上重跑 C6（mnc = 0）与 C6-M（mnc = 4），须同时满足：

1. 新轨迹每一次调用的 `hypergraph_sha256`、`labels_sha256`、`actual_sizes` 与 T21 的
   `checks/c6__cora__C6__W16__0-bisections.json`、`checks/c6__cora__C6-M__W16__4-bisections.json` 逐条相同，调用次数相同（169）；
2. `alignment_repair.calls_repaired = 0`；
3. 16 个评价条件的 `sumU、T、sumGamma、sumR、R_p50、R_p90、R_max` 与 T21 `joint.csv` 中对应行（matrix = cora，member、mnc 相同）逐个相等；
4. 若本地完整归档在手，行序与 T21 `orders/` 中对应文件相同（可选，做了就报）。

结果写 `checks/gate2-cora-noop.json`。

**门 3：pattern1 前缀可复现（在主运行中顺带做）。** 对每个用例，新轨迹中**旧失败层之前**的每次调用，`hypergraph_sha256`、`labels_sha256` 须与 T21 旧轨迹
（`checks/c6__pattern1__<成员>__W16__<mnc>-bisections.json`）逐条相同；旧失败层本身，新轨迹的原始 `labels_sha256` 须与旧轨迹相同，
且其 `align_repair` 的挪动顶点、`weighted_cut_after`、`final_labels_sha256` 须与 `expected-repairs.json` 相同。
不相同时**不停**：照常跑完，在 `checks/gate3-pattern1-prefix.json` 里记 `reproduced: false` 与第一处不同的调用序号，README 里显著标出。

## 4. 主运行

- 用例 4 个，规格与 T21 完全相同（T21 工作目录 `work/specs/` 下）：
  `c6__pattern1__C6__W16__0`、`c6__pattern1__C6-M__W16__1`、`c6__pattern1__C6-M__W16__4`、`c6__pattern1__C6-M__W16__16`。
- 每例上限 7200 秒，同时最多 2 个（与 T21 的 c6 阶段相同）。耗时参考：T21 中这几例在失败前约 1 分钟走完 107–290 次调用（共需约 1202 次）；
  同为长行的 human_gene1 每例约 22 分钟【推：pattern1 应在此量级以内】。
- 每例跑完后，按 T21 对 c6 的做法评价同样的 16 个条件（A0 / A1 × {全行 own、全行 D-greedy、τ = 2 / 3 的原位 own、末尾 own、末尾 D-greedy}），
  同样的不变量检查（行序是排列；D 阶段前后 ΣU、ΣΓ 相等；A0 / A1 窗口集合相同；组大小除末组外全为 16）。
- `member_params` 在 T21 原有字段之外带上 `alignment_repair`（修补规则、上限、修补次数、挪动点数、最大 |d|、加权割变化合计），
  `note` 指向新的行序文件与轨迹。

## 5. 失败的处理

| 情况 | 记法 |
|---|---|
| 某层 |d| > 8 | `INCOMPLETE`，轨迹状态 `INCOMPLETE_ALIGN_REPAIR_CAP`，保留该层 `*-failed-model.json` |
| 超时（7200 秒） | `INCOMPLETE`，注明超时 |
| 其他报错 | `INCOMPLETE`，保留完整 stderr |

都不重试、不换参数；未完成的不得解释为通过（与 T21 相同）。

## 6. 交回内容

新目录 `第一层实验结果/rq2-c6align-YYYYMMDD/`（YYYYMMDD 为运行日期，北京时间），内含：

| 路径 | 内容 |
|---|---|
| `results-c6align.csv` | 64 行（4 个用例 × 16 个条件），列与 T21 `results.csv` 完全相同（26 列、同序） |
| `joint-c6align.csv` | 64 行，列与 T21 `joint.csv` 完全相同（32 列、同序） |
| `checks/` | 4 个新轨迹 `c6__pattern1__*-bisections.json`（含每次修补的 `align_repair` 记录）、门 1 / 2 / 3 的 json、不变量记录；若有失败，失败现场 |
| `orders/` | 新行序（`row_perm[新位置] = 原编号`）；合计不超过 20 MiB 则一并交回入库，超过则只留本地并在 README 写明大小与 sha256 |
| `code/` | 实际运行的 `c6.py`（应与本目录同一 sha256）及调用它的脚本 |
| `logs/` | 每例的命令、开始 / 结束时间、退出码、stdout / stderr，环境记录（Python、KaHyPar 模块 sha256、配置 sha256） |
| `README.md` | 一张表：每例的状态、二分调用次数、修补次数、挪动点数、最大 \|d\|、加权割变化合计、划分耗时；门 1 / 2 / 3 结果；与 T21 环境的任何差异 |
| `SHA256SUMS` | 覆盖本目录全部文件（自身除外） |

**不要改 T21 的 `results.csv`、`joint.csv`、`matrix-method-status.*`**：两份结果的合并由规划方在分析时做
（按 matrix、diag、member、mnc、W、tau、placement、d_rule 用新行替换那 64 行 INCOMPLETE）。

## 7. 一句话复述（给执行方核对理解）

用本目录的 `c6.py` 重跑 pattern1 上 4 个 C6 / C6-M 用例；先过三道门；每层若 KaHyPar 差 d ≤ 8 个点，就按「挪一个点、加权割增加最少、并列取局部编号最小」
逐个挪齐，并全部记下来；结果写新目录，不碰 T21 的任何文件，不提交、不推送。

## 8. 本目录文件的 sha256

见包十五的 `pkg15-sha256-after.txt`；应用后可用 `shasum -a 256 第一层工作区/T21补跑-C6对齐修补/*` 核对。
