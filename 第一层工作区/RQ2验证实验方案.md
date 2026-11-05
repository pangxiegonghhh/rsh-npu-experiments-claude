# RQ2 验证实验方案（v1，2026-11-05）

状态：规划方撰写，交执行方 agent 实施；数据回来后由规划方分析（用户 2026-11-05 确认的分工）。
2026-11-06 修订：B-RCM-ref 改用确定性实现，§8 自检参考值随之更新（首次执行因 SciPy 版本差异在 RCM 一行未通过）。
依据：`第一层工作区/T17-空白一调研.md`（下称"调研"）。本方案只做 **CPU 结构实验**，不测 NPU 性能。
参考实现：`第一层工作区/T17-空白一试算脚本/`（Python，试算质量，已能复现调研 §8 的 Cora 数字）。

---

## 0. 目的

调研在 Cora 一张矩阵上得到的 RQ2 结论需要在更多矩阵、两种对角口径下复核，并补上调研环境做不了的超图划分实验：

| 编号 | 要验证的结论 | 调研出处 |
|---|---|---|
| H1 | 对称视图下 R 约等于非零 W×W 块数 Γ：做完 D 阶段后 R − Γ 很小 | §1.6 |
| H2 | D-greedy 相对自带序显著降 R，且接近精确 D 阶段 | §5 |
| H3 | U 与 Γ 在各成员之间大体同向（RCM、SlashBurn 类为例外） | §1.6、§3.1 |
| H4 | Gorder 的 S_n 项降 Γ、R，几乎不动 T | §3.2 |
| H5 | 划分感知的成员局部搜索 P-LS(λ)：λ=1 比 λ=0 降 R、T 代价小；全行上做的局部搜索收益在划分后消失 | §4.5 |
| H6 | C6-M（C6 加消息网）比 C6 降 Γ、R，U 略升 | §4.1 |
| H7 | 加自环（A+I）后 U、T 上升、Γ 几乎不变，T 的名次可能改变 | §6 第 1 条 |
| H8 | 对称约束的代价（独立视图 CBM 贪心 vs 对称视图 D 阶段）随 W 增大而增大 | §1.5 |

## 1. 硬约束

- 不改仓库已有文件；冻结项（A 行重排、W16 窗口成员、AIC/Residual 归属）不动；`candidates.md` 不改。
- 结果写入新目录 `第一层实验结果/rq2-validate-YYYYMMDD/`，不覆盖 `cora-pilot-20261104/`。
- 每个"成员 × 条件"的 D 阶段运行前后，**ΣU 与 ΣΓ 必须完全相等**（D 阶段只改顺序、不改成员），否则视为错误，不得报数。
- 不得自行补自环、删边、采样非零或改值；A0 / A1 两种口径只在下面第 2 节规定的预处理里产生。

## 2. 输入矩阵与预处理

**第一批（必做）**，与骨架 §4.3 一致：

| 矩阵 | 类别 | 备注 |
|---|---|---|
| cora | GNN | 用仓库 `第一层实验结果/cora-pilot-20261104/neutron-matrices/cora.mtx`（sha256 `f54431cb…a573856`） |
| ogbn-arxiv | GNN | T16；有向边按对称展开处理 |
| wiki-RfA | SuiteSparse，真实网络 | 下载曾失败，失败则记录并跳过 |
| dawson5、olafu | SuiteSparse，有限元带状 | |
| pattern1、human_gene1 | SuiteSparse，长行 | |

**第二批（可选，按规模上限）：** reddit、amazon-product（T16）、mycielskian15。

**预处理（每张矩阵两种口径）：**

1. 读 Matrix Market，显式零值丢弃，结构对称展开 A ∪ Aᵀ，值一律置 1。
2. **A0**：去掉全部对角元。**A1**：A0 加满对角（每个点一个自环）。
3. 记录 n、nnz(A0)、度数中位数 / 均值 / 最大值、文件 sha256。
4. **行序一律在 A0 上计算**，A0 与 A1 只在评价时区别（与调研 §6 第 1 条的做法一致）。
5. **残余集合按 A0 的度数定**：deg_A0(v) ≤ τ 的行送残余。A1 下用同一残余集合（否则两口径的残余集不同，不可比）。

参考实现：`rq2lib.load_mtx(path, selfloop)`。

## 3. 行序（成员）来源

| 名称 | 来源 | 参数 | 优先级 |
|---|---|---|---|
| B0 | 原始序 | — | P0 |
| rsh-α0、rabbit-pilot、neutron-pilot | 仓库 `cora-pilot-20261104/rsh_reorder_experiment.py`（`--input` 支持任意 mtx），取输出 JSON 的 `row_perm` | 默认参数（与 Cora 先导一致） | P0 |
| C9-Gorder、C9-S | 参考实现 `methods.gorder(adj, w=15, use_sn=True/False)` | w = W−1；hub 跳过阈值 √n | P0 |
| C9-β（S_n 权重扫描） | 同上，打分 S_s + β·S_n | β ∈ {0.5, 2, 4}（β=0 即 C9-S，β=1 即 C9） | P1 |
| C10-BP | 参考实现 `methods.bp(adj, W)`；二分左侧取 W 的倍数，递归到 W 点 | 每层 20 轮，随机初始划分，种子 0 | P0 |
| B-RCM-ref | 参考实现 `methods.rcm(adj)`（确定性实现；**不要用** SciPy 的 `reverse_cuthill_mckee`，其平局处理随版本 / 平台变化，2026-11-06 自检因此失败） | 只在 dawson5、olafu 上报，其余矩阵可报作参考 | P1 |
| SlashBurn | 参考实现 `methods.slashburn(adj)` | k = 0.5% n | P2 |
| C6 / C6-M | 超图划分器（KaHyPar 或 PaToH）递归二分到 k = ⌈n/W⌉ 组、每组恰 W 点；C6-M 在每步加消息网（第 6 节） | 时间上限同 C6，超时记 INCOMPLETE | P2 |
| B-RSH-ref、B-Neutron-ref | T4、T2 完成后补上 | — | 有则做 |

rabbit-pilot、neutron-pilot、rsh-α0 是先导脚本的简化实现，报数时须原样标注（骨架 P7）。

## 4. 评价条件

- **主条件：** W = 16，对称视图（列序 = 行序）。
- **划分：** 全行；以及 τ ∈ {2, 3}（第 2 节第 5 条的残余集）。划分后剩余行按行序重新每 W 行切窗。
- **残余点放置（骨架 P10）：** 原位、末尾两种都报。D 阶段只在"末尾"下做（调研 §5 第 3 条；"原位"下的 D 阶段留空白二）。
- **对角口径：** A0、A1 都报。
- **W 敏感性（P1）：** W ∈ {32, 64, 128}，只做 cora、ogbn-arxiv、dawson5、wiki-RfA，只做全行与 τ = 3，只用 B0、rsh-α0、C9-Gorder、C10-BP。

## 5. D 阶段规则

成员不变（窗口集合不变），只改编号顺序：

| 名称 | 规则 | 适用 |
|---|---|---|
| own | 不排，用行序自带的顺序 | 全部 |
| D-greedy | 组内：按 co 从大到小连边、不成环、度数 ≤ 2（TSP greedy-edge），得一条链；组间：以各组首尾两点为端口按 co 从大到小连接、不成环、允许整组翻转；**不满 W 点的末组固定在最后** | 全部（主） |
| D-exact | 组内 Held–Karp 精确最大权 Hamilton 路（端点自由）+ 组间同上 | 只 W = 16；k 很大时可只在 cora、dawson5、olafu 上做 |
| indep-first | 独立视图参照：列号按"逐窗扫描、首次出现"的顺序编号 | 全行，P1 |
| indep-CBM | 独立视图参照：全部点上按 co 的 greedy-edge 链 | 全行，P1；co 对数过多（> 5×10⁷）时跳过并记录 |

co(u, v) = 同时用到列 u、v 的窗口数（窗口的列并集同时含 u 与 v）。划分后，co 只按 AIC 窗口算；残余点作为列，参与 co 与 R，
但不属于任何组，位置按放置规则固定。参考实现：`rq2lib.dstage(order, adj, W, tau, intra='greedy'|'exact')`。

## 6. 联合成组实验

**J1：P-LS(λ)，划分感知的成员局部搜索（P1）。** 先按 τ 删去残余行，在剩余行的窗口上反复尝试两点互换（保持每组恰 W 点；
不满 W 的末组参与互换但位置不动），接受使 ΣU + λ·ΣΓ 下降的互换；候选：对每个点取与它列重叠最多的 3 个组、逐一试换；
最多 10 轮、某轮无接受即停；种子 0（cora、ogbn-arxiv 另跑种子 1、2 看方差）。起点：C9-Gorder、rsh-α0、rabbit-pilot；
λ ∈ {0, 0.5, 1, 2}；τ ∈ {2, 3}；之后接 D-greedy，末尾放置。另在 cora、ogbn-arxiv 上跑一次**全行**版（不删残余行）再划分评价，
作对照。参考实现：`memberls_part.MemberLSPart`、`methods.MemberLS`（纯 Python，ogbn-arxiv 规模需移植或加速）。
增量维护的 ΣU、ΣΓ 须在结束时与全量重算一致。

**J2：C6 vs C6-M（P2，需超图划分器）。** column-net 超图（网 = 列，管脚 = 该列有非零的行；对称视图下顶点同时是该点对应的列的拥有者）。
递归二分到 k 组、每组恰 W 点（目标块重设为 W 的倍数）。C6-M：按 Selvitopi 等（IEEE TPDS 28(2), 2017）Algorithm 1，在每个非根二分步
为当前部分与每个其他部分加 send / receive 消息网（对称 A 下二者管脚相同），消息网代价 mnc ∈ {1, 4, 16}（通信量网代价 1；mnc = 0 即 C6）。
报 U、T、Γ、R（own 与 D-greedy）、划分耗时。

**J3：S_n 权重扫描（P1）。** 见第 3 节 C9-β。

## 7. 指标与输出

每个"矩阵 × 口径（A0/A1）× 成员 × W × τ（全行记 none）× 放置 × D 规则"一行，写 `results.csv`：

`matrix, diag(A0|A1), member, member_params, W, tau, placement(none|inplace|tail), d_rule, n, k_windows, resid_frac,
sumU, meanU, T, sumGamma, meanGamma, sumR, meanR, R_p50, R_p90, R_max, sumR_minus_Gamma, order_sec, d_sec, status(OK|INCOMPLETE|SKIPPED), note`

- T = Σ⌈U_w / 16⌉（K 方向块宽固定 16，与 W 无关）。
- Γ_w = 窗口 w 的列在最终编号下落入的不同 ⌊位置 / W⌋ 的个数（全行与末尾放置下即非零 W×W 块数）。
- R_w = 窗口 w 的列在最终编号下的连续段数。
- J1、J2 另写 `joint.csv`：在上表列之外加 `start, lambda 或 mnc, seed, sweeps_done, accepted_swaps`。
- `manifest.json`：矩阵 sha256、代码版本（文件 sha256）、全部参数、机器信息；`orders/` 下保存每个行序（JSON，row_perm[新位置] = 原编号）。

## 8. 自检（报数前必须通过）

1. **Cora 复现：** 在一个空目录运行 `python3 第一层工作区/T17-空白一试算脚本/reproduce_cora.py`，输出首行须为 `Table A self-check: OK`
   （调研 §8 表 A 的 9 种成员的 U、T、Γ、自带序 R、D 后 R 全部吻合，容差 0.01），且退出码为 0（自检失败时退出码为 1）。
   若改写或移植了实现，用移植版在 cora 上重出表 A，须吻合。
2. **独立复核：** 用 `verify/indep_check.py`（不依赖 rq2lib 的 numpy/scipy 实现）对至少 3 个行序复算 U、T、Γ、R，须与主实现一致。
3. 每个行序是 0..n−1 的排列；D 阶段前后 ΣU、ΣΓ 相等；划分后残余集合与第 2 节规定一致；A0 与 A1 的窗口集合相同。

## 9. 结果怎么读（预先登记，规划方分析时对照）

| 编号 | 预测 | 不成立时的含义 |
|---|---|---|
| H1 | 全行、D-exact（或 D-greedy）后 meanR − meanΓ ≤ 1.5（各矩阵、各成员） | 块内碎片或交界不可忽略，D 阶段的重要性上升 |
| H2 | D-greedy 相对 own 降 R ≥ 10%（B0、C9 等自带序已较好的成员可能较小），并取得 D-exact 收益的 ≥ 80% | 需要更强的 D 阶段（2-opt、精确 DP） |
| H3 | 每张图上各成员的 meanU 与 meanΓ 的 Spearman ≥ 0.7；带状矩阵上 B-RCM-ref 的 U、Γ 都不差 | U 与 R 冲突，联合优化更必要 |
| H4 | GNN 图上 C9 对 C9-S：Γ 降 ≥ 5%，T 变化在 ±2% 内；β 增大 Γ 单调下降、T 先平后升 | S_n 不是廉价的 R 杠杆 |
| H5 | P-LS(1) 对 P-LS(0)：τ = 2、3 下 R 降 5%–15%，T 变化在 ±3% 内；全行版收益在划分后 ≤ 2% | 联合成组无须划分感知，或收益太小 |
| H6 | C6-M（mnc = 4）对 C6：Γ 降、U 升 ≤ 5%；划分耗时增幅可能超过文献的 7%–48% | 消息网在小分区、大 K 下失效 |
| H7 | A1 对 A0：meanU 升 10%–25%，meanΓ 变化 < 3%；至少一张矩阵上 T 的第一名改变 | 自环问题不影响名次，可只报一种 |
| H8 | (indep-CBM 的 R) / (对称 D-greedy 的 R) 随 W 增大而下降 | 对称约束代价与 W 无关 |

## 10. 规模与时限

- 纯 Python 参考实现在 Cora 上：表 A、B 约 1–2 分钟；J1 每次约 0.5–1.5 分钟。ogbn-arxiv（约 17 万点）规模下 D-greedy、P-LS、BP、Gorder
  需移植到 C++ 或 numba，或给出时限后记 INCOMPLETE。
- 单个"矩阵 × 方法"的行序计算上限建议 2 小时；C6 / C6-M 用 C6 已定的上限。
- D-exact 每组约 1.7×10⁷ 次运算（W = 16），k 过万时只做小矩阵。

## 11. 交回规划方的内容

`results.csv`、`joint.csv`、`manifest.json`、`orders/`、运行日志、自检输出（第 8 节三项），以及一张"矩阵 × 成员"的状态表（OK / INCOMPLETE / SKIPPED 及原因）。
规划方据第 9 节分析，结论写回调研文档并更新骨架。
