# RQ3 验证实验方案（T22，v1，2026-11-06）

状态：规划方撰写；**等 T21 跑通（通过其 §8 自检并交回第一批结果）后**由用户派给执行方 agent，数据回来后由规划方分析（分工同 T21）。
2026-11-06 修订：用户确认调研 §9（全部按建议）；增 R3-H9（与 NeutronSparse 式"删后重排"的对照，数据已在 M3、M6 中，不增加运行项）。
依据：`第一层工作区/T17-空白二调研.md`（下称"调研"）。本方案只做 **CPU 结构实验**，不测 NPU 性能。
参考实现：`第一层工作区/T17-空白二试算脚本/`（Python，试算质量，已能复现调研 §8 的 Cora 数字），依赖 `T17-空白一试算脚本/`。
**尽量复用 T21 的产物：** 矩阵与预处理、行序（`orders/`）、大图移植代码（D-greedy、P-LS、BP、Gorder），不重复计算、不修改 T21 的结果目录。

---

## 0. 目的

调研在 Cora 一张矩阵上得到的 RQ3 结论需要在更多矩阵、两种对角口径、不同残余比例下复核：

| 编号 | 要验证的结论 | 调研出处 |
|---|---|---|
| R3-H1 | T_keep − T_inplace 主要是半空窗口的合并收益：平滑行序上为负；只有依赖精确对齐的行序会出现 ΣU_keep > ΣU_inplace | §1.2 |
| R3-H2 | 对齐红利 A 区分"依赖精确对齐"的行序（C10-BP、全行成员局部搜索）与平滑行序，且能预测重跑收益 | §1.2、§2.1 |
| R3-H3 | 全行名次与划分后名次中度一致（Kendall ≥ 0.6），第一名可能改变 | §1.3 |
| R3-H4 | 只重跑同一方法（T(π′)）对平滑行序几乎无益，对 C10-BP 有益 | §2.1 |
| R3-H5 | 划分感知 P-LS 抹平起点差别（T）；λ=1 比 λ=0 在末尾-co 下仍降 R | §2.2 |
| R3-H6 | 残余集合估错时，划分感知重排的收益消失或为负 | §2.3 |
| R3-H7 | 末尾-co 比末尾显著降 R，降幅随残余比例增大；A1 下同样成立 | §3.1、§3.2 |
| R3-H8 | 原位规则在读侧不优于末尾-co，写回段数远多于窗口数 | §3.3 |
| R3-H9 | 同一残余集合下，直接压 ΣU 的成员调整（P-LS）优于 NeutronSparse 式的删后重排（neutron-pilot 在剩余行上重跑） | §4.4 末 |

## 1. 硬约束

- 不改仓库已有文件；冻结项（A 行重排、W16 窗口成员、AIC/Residual 归属）不动；`candidates.md` 不改；不改 T21 的结果目录。
- 结果写入新目录 `第一层实验结果/rq3-validate-YYYYMMDD/`。
- **放置规则与 D 阶段不得改变 AIC 窗口成员**：同一"矩阵 × 口径 × 行序 × τ"下，各放置规则的窗口集合、ΣU、T 必须完全相同，否则不得报数。
- 残余集合一律按 A0 度数定（与 T21 §2 第 5 条相同），A1 用同一残余集合。
- 不得自行补自环、删边、采样非零或改值。

## 2. 输入

**矩阵与预处理：** 与 T21 §2 完全相同（第一批：cora、ogbn-arxiv、wiki-RfA、dawson5、olafu、pattern1、human_gene1），直接读 T21 的 manifest 核对 sha256。

**行序：**

| 名称 | 来源 | 优先级 |
|---|---|---|
| B0、rsh-α0、rabbit-pilot、neutron-pilot、C9-Gorder、C9-S、C10-BP | T21 的 `orders/`（缺则按 T21 §3 重算） | P0 |
| B-RCM-ref、SlashBurn | 同上 | P1 |
| LS-full(C9-Gorder)、LS-full(rsh-α0) | 全行成员局部搜索（`methods.MemberLS`，λ=0，最多 10 轮，种子 0）的输出，作"依赖精确对齐"的对照；只做 cora、ogbn-arxiv、wiki-RfA | P1 |

rabbit-pilot、neutron-pilot、rsh-α0 是先导脚本的简化实现，报数时原样标注（骨架 P7）。

## 3. 划分（τ）

- 对每张矩阵先算 A0 度数下 τ = 2、3 的残余比例 resid_frac。
- **若 τ = 3 时 resid_frac ≥ 10%**：用 τ ∈ {2, 3}（与 T21 一致）。
- **否则**（预计 dawson5、olafu、pattern1、human_gene1 属此类【推，按平均度数估计】）：改用分位数 τ——取最小的 τ 使 resid_frac ≥ 20%，记 τ_q20；同理 τ_q40。
  这是"删去一部分行之后结构还剩多少"的压力测试，不代表这些矩阵在 NPU 上真会把这么长的行送 AIV（骨架 P6：第一层的划分规则方向中性）。
- 每个 τ 记录 resid_frac 与残余行的非零占比。

## 4. 测量

**M1 四个数（A0、A1）：** T 与 ΣU 各四个：full（π 全部行每 W 行切窗）、inplace（π 切窗后删去残余行、窗口留空不前移，空窗不计）、keep（π_K 切窗）、
rerun（在 K 上重跑同一方法得 π′ 再切窗）。另报 inplace 的非空窗口数。参考实现：`rq3lib.four_numbers`。

**M2 对齐红利（A0，全行）：** T_full^φ = 切口平移 s = 1, …, W−1 行（首窗只含 s 行，其后每 W 行一窗）后 T 的平均；A = T_full^φ − T_full。
大图若超时，可只取 s ∈ {2, 4, 6, 8, 10, 12, 14} 并注明。参考实现：`rq3lib.phase_T`。

**M3 重跑 π′：** 输入为 A[K, :]（K 的行、全部列；残余点仍作为列）。C9-Gorder、C9-S：`rq3lib.gorder_sub`；C10-BP：`rq3lib.bp_sub`；
rsh-α0、rabbit-pilot、neutron-pilot：先导实现的 Python 函数直接吃矩形矩阵（`rq3lib.pilot_sub`）；B-RCM-ref、SlashBurn：诱导子图 A[K, K]（`rq3lib.induced`）；
B0：π_K。LS-full 不重跑（报 "—"）。**自检：** K = 全部点时，各重跑须与原行序逐位相同。

**M4 名次一致性：** 每张矩阵、每个口径、每个 τ，按 T 计算 Kendall τ_b：full vs keep、keep vs rerun、keep vs after-E（M6 的 P-LS(0) 后）；另报去掉 B0 的版本。

**M5 放置规则（A0、A1；W=16）：** 在 π_K 的窗口上：

| 规则 | D 阶段 | 说明 |
|---|---|---|
| tail | own、D-greedy | P10 末尾：K 的序 + 残余点按 π 相对顺序 |
| inplace | own、D-greedy | P10 原位：残余点留在 π 中的位置 |
| snap | own、D-greedy | 就近：每个残余点接在"π 中它前面最近的 K 点"所在窗口之后 |
| **tail-co** | D-greedy | 末尾-co：残余区按 co 贪心链（greedy-edge，co 只按 AIC 窗口计） |
| gap | D-greedy | 间隙：残余点作为单点簇参与组间贪心（单点有两个端口，可夹在两个 AIC 组之间） |

另在 rerun 的窗口上做 tail、tail-co、gap（D-greedy）。每格报 meanR、R_p90、R_max、**AIC 写回段数**（各窗口 W 个输出行在 σ 中的连续段数之和）、
**残余写回段数**（残余点在 σ 中的连续段数）。参考实现：`rq3lib.layout_D(windows, adj, n, D_in_pi, rule, W, pi)`、`rq3lib.win_metrics`、`rq3lib.resid_write_runs`。
A1 下 D-greedy 与 co 用 A1 的邻接计算。

**M6 划分感知后处理（A0，A1 只报 T）：** P-LS(λ)（`memberls_part.MemberLSPart`，与 T21 J1 相同的规则；最多 10 轮，种子 0）：

- 起点：P0 全部行序 + C10-BP 的 rerun；λ ∈ {0, 1}（B0、rabbit-pilot、neutron-pilot 只做 λ=0）；
- 之后接 D-greedy，报 tail、tail-co、gap 三种放置下的 R；
- 记录 sweeps_done、accepted_swaps、耗时；增量维护的 ΣU、ΣΓ 须在结束时与全量重算一致。
- 若 T21 的 J1 已在相同起点、τ、λ 上跑过 P-LS，直接复用其输出的行序，只补 tail-co、gap 的评价。

**M7 跨 τ：** 对 C9-Gorder、rsh-α0、C10-BP、SlashBurn：σ_a = π′(τ_a) + 残余点(τ_a) 按 π 相对顺序；在 τ_b 下划分（取 T_keep）。τ 组合取本矩阵所用两档 τ 的两个方向。
同时报 T_keep(π, τ_b) 与 T(π′(τ_b))。

**W 敏感性（P1）：** 只做 cora、ogbn-arxiv，W ∈ {32, 64}，只做 M1、M2、M5（tail、tail-co），行序取 B0、rsh-α0、C9-Gorder、C10-BP。

## 5. 输出

- `results.csv`：每行一个"矩阵 × 口径 × 行序 × W × τ × 来源（keep / rerun / pls-λ）× 放置规则 × D 规则"：
  `matrix, diag, member, W, tau, tau_rule(fixed|q20|q40), resid_frac, resid_nnz_frac, source, lambda, placement, d_rule, k_windows, sumU, T, meanR, R_p90, R_max,
  write_runs_aic, write_runs_resid, sec, status(OK|INCOMPLETE|SKIPPED), note`
- `four_numbers.csv`：`matrix, diag, member, W, tau, T_full, T_inplace, T_keep, T_rerun, U_full, U_inplace, U_keep, U_rerun, k_inplace, T_full_phase, align_premium, offsets_used`
- `kendall.csv`、`cross_tau.csv`、`pls.csv`（含 sweeps_done、accepted_swaps）
- `manifest.json`（矩阵 sha256 与来源，代码文件 sha256，全部参数，机器信息）；`orders/` 只放本实验新产生的行序（rerun、LS-full、P-LS 输出），T21 已有的用路径引用。

## 6. 自检（报数前必须通过）

1. **Cora 复现：** 在一个空目录运行 `python3 第一层工作区/T17-空白二试算脚本/reproduce_cora_rq3.py`，输出须含 `RQ3 Table 1/2 self-check: OK` 且退出码为 0
   （调研 §8 表 1 的 18 组四个数、表 2 的 18 组 R 全部吻合，容差 0.01）。若改写或移植了实现，用移植版在 cora 上重出表 1、表 2，须吻合。
2. **独立复核：** 用 `verify/indep_check_rq3.py`（不依赖 rq2lib、rq3lib）在 cora 和至少另一张矩阵上，对至少 3 个行序复算四个数与对齐红利、
   对至少 3 个 σ（含 tail-co、gap）复算 U、T、R 与写回段数，须与主实现一致。
3. **不变量：** 每个行序、每个 σ 都是 0..n−1 的排列；同一"矩阵 × 行序 × τ"下各放置规则的窗口集合、ΣU、T 相同；tail、tail-co、gap、snap 的 AIC 写回段数
   等于窗口数；K = 全部点时重跑与原行序逐位相同；A0 与 A1 的残余集合相同。

## 7. 结果怎么读（预先登记，规划方分析时对照）

| 编号 | 预测 | 不成立时的含义 |
|---|---|---|
| R3-H1 | resid_frac ≥ 20% 时，A/T_full ≤ 2% 的行序 T_keep − T_inplace < 0（全部矩阵）；ΣU_keep > ΣU_inplace 只出现在 A/T_full ≥ 5% 的行序上 | T_inplace 口径在该矩阵上可直接读作成员平移；或切散不只来自精确对齐 |
| R3-H2 | GNN 图上 C10-BP、LS-full 的 A/T_full ≥ 5%，其余 P0 行序 ≤ 2%；各矩阵上 A/T_full 与 T(π′)/T_keep 的 Spearman ≤ −0.5 | 对齐红利不是成员平移的好代理 |
| R3-H3 | GNN 图上 Kendall(full, keep) ≥ 0.6；至少一张图上 T 的第一名改变 | 全行名次可直接用，或全行评价不可用 |
| R3-H4 | 平滑行序（rsh-α0、rabbit-pilot、neutron-pilot、C9、C9-S）的 T(π′)/T_keep − 1 在 ±3% 内；C10-BP ≤ −3% | "先分后排"在更多矩阵上有普遍收益，RQ3 结论要改 |
| R3-H5 | P-LS(0) 后各起点 T 的极差 / 最小值 ≤ 10%（P-LS 前通常 > 20%）；P-LS(1) 对 P-LS(0)：tail-co 下 R 降 5%–15%，T 变化在 ±3% 内 | 第一层名次在后处理之后仍重要（Q4 不普遍） |
| R3-H6 | 假定的残余集合偏大（τ_a > τ_b）时，T(σ_a) ≥ T_keep(π, τ_b) 在过半"矩阵 × 行序"上成立 | 划分感知重排对残余集合不敏感，可放进第一层 |
| R3-H7 | tail-co（+D-greedy）对 tail（+D-greedy）：resid_frac ≈ 40% 时降 R ≥ 5%、≈ 60% 时 ≥ 15%，降幅随 resid_frac 单调增大；A1 与 A0 的降幅相差 ≤ 3 个百分点 | 残余区的排序不是主要杠杆，或依赖图类型 |
| R3-H8 | inplace 的 AIC 写回段数 ≥ 3 × 窗口数；R(inplace, own) ≥ R(tail-co, D-greedy) 在全部"矩阵 × 行序 × τ"上成立 | 原位规则在某类矩阵上有读侧优势，须保留为候选 |
| R3-H9 | GNN 图上 P-LS(0)（起点 neutron-pilot）的 T ≤ 0.9 × neutron-pilot 的 T(π′)（Cora：295 对 376） | 直接压 U 的成员调整相对 NeutronSparse 式分组无明显优势，P-LS 只作工程部件 |

## 8. 规模与时限

- 纯 Python 参考实现在 Cora 上：表 1–4 约 10–20 秒；P-LS 每次 20–55 秒。ogbn-arxiv 规模下 co_chain、inter_greedy2、P-LS、重跑的 BP / Gorder 需移植
  （优先复用 T21 的移植版本），或给出时限后记 INCOMPLETE。
- 单个"矩阵 × 行序 × τ"的重跑上限建议 2 小时；P-LS 单次上限 2 小时，超时记 INCOMPLETE 并报已完成轮数下的结果。
- pattern1、human_gene1 的非零数很大，M2 的 15 个切口可降为 7 个（注明）。

## 9. 交回规划方的内容

`results.csv`、`four_numbers.csv`、`kendall.csv`、`cross_tau.csv`、`pls.csv`、`manifest.json`、`orders/`、运行日志、自检输出（第 6 节三项），以及"矩阵 × 行序 × τ"的
状态表（OK / INCOMPLETE / SKIPPED 及原因）。规划方据第 7 节分析，结论写回调研文档并更新骨架。
