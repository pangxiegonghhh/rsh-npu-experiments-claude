# 给 T23 实验 agent 的说明（推送 agent 完成之后）

1. 拉取最新 main：`git pull`。确认 `git rev-parse HEAD^{tree}` 为 `54dd7a113c4ecad145e07b47d8745f9de7d56756`（或其后的提交）。
2. 先通读 `第一层工作区/T23派发/说明.md`，再读 `第一层工作区/首轮候选比较实验方案.md`。要点：
   - **分两次交回**：阶段 1–2（第一批矩阵上的 P0 候选，含外部工具与「后处理之后」一套）→ `第一层实验结果/round1-compare-YYYYMMDD/`；
     阶段 3（P1、P2、W 敏感性、第二批矩阵）→ `第一层实验结果/round1-compare-stage3-YYYYMMDD/`。
   - 144 个行序按 `第一层工作区/T23派发/orders-index.csv` 复用（140 个在用户本机的 T21 完整归档，pattern1 的 C6 / C6-M 4 个在仓库补跑目录），用前逐个核对 sha256；C6-RB、C6-M 用 T21 口径，不重跑。
   - 报数前过全部自检（说明 §7）：T21 / T22 的 Cora 复现、`第一层工作区/T23参考实现/reproduce_cora_t23.py`（8 个行序 SHA-256）、
     `第一层工作区/T23派发/conditions_ref.py --cora-selfcheck`（评价器 40 行逐字段相等）、外部工具可复现、独立复核、与 T21 的一致性。
   - Rabbit 在 macOS 上可能编不了：先试 Linux 容器或虚拟机，仍不行就把 C5 系与全部 -R 变体记 INCOMPLETE，不得顶替。
   - 主口径为 tail-co + D-greedy，但每种放置都同时输出 own 与 D-greedy 两行（规划方判读时做 D 阶段守门）。
3. 每次交回：README（状态表、τ 实算表、工具版本、复用 / 新算个数、co_chain 守卫触发次数）+ SHA256SUMS，打 tar.gz 交给用户。不改已有结果目录，不提交、不推送。
