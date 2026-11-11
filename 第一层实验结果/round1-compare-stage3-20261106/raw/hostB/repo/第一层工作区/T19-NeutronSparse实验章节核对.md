# T19：NeutronSparse 实验章节与相关方法细节核对

状态：2026-11-06（北京时间）规划方完成；**同日更正**：用户上传 Ascend-SpMM 原文后核对，§4 原推断作废并重写，新增 §7（开源的 NeutronSparseLite），§6 待拍板已答复。读的是仓库 `文献pdf/` 中的 NeutronSparse 全文（arXiv 2606.22482v1，2026-06-21，28 页），
本次通读 §5.1–§5.3、§6.1–§6.2、§7、§8.1–§8.6，此前只读过 §5.2.2、§6.1、§6.2.1、§8 的部分段落。
标注：**★** = 本次亲读原文（节号、表号）；**【推】** = 规划方推断；**【待核】** = 未核实。

代办 T19 原列三问（Ascend-SpMM 图 8、列抽取的写冲突、是否带对角），空白二另转来一问（删后的分组细节）。另有三项顺带发现（§5）。

---

## 结论摘要

1. **对角（骨架 P12）：GNN 图上 NeutronSparse 的 SpMM 矩阵不带对角。** Table 2 中 cora 为 10,556 个非零，等于本项目 A0（2×5,278 条无向边，无自环）；
   ogbn-arxiv 为 2,315,598，等于 1,166,243 条引用边对称化后的条目数，若加自环应为 2,484,941。SuiteSparse 矩阵则按原文件条目计（如 dawson5 1,010,777）。
   → 与 NeutronSparse 比较（G1a）时，**A0 是与它一致的口径**。
2. **列抽取的写冲突：原文没写。** AIV 用 ScatterAdd 把结果累加进输出行（§5.1、§7 图 13），AIC 按行窗口整块写回（§6.2.2）；被列抽取拆开的行由两种引擎
   各算一部分，二者如何排序或做原子加，原文未说明，也没有测这部分开销。运行时迁移（§5.3）把 AIC 的整块拆成向量交给 AIV，同样产生这种情形。【待核代码】
3. **删后的分组：** 先按行长抽走短行，被抽走的行"完全跳过重排"（§8.6）；剩下的行做二部图 Rabbit 粗聚类（簇数刻意限制，未给具体数），再在每个簇内按
   **M = 128 行**窗口做 anchor-Jaccard 重组（每个 anchor 取 127 个最相似的未分配行），只排行、不改列序，最后列压缩成 (M, N, K) = (128, 256, 64) 的块（§6.1、§6.2.2）。
   与空白二 §4.4 末的描述一致；补充一点：它的窗口高 128 行，本项目先导里的 neutron 用的是 16 行（已标为简化实现）。
4. **Ascend-SpMM 图 8（NeutronSparse 与 Naive CSR 同档）与 NeutronSparse 自报结果差距很大，大概率因为 Ascend-SpMM 测的是开源的 NeutronSparseLite【推】。**
   Ascend-SpMM 称用了 NeutronSparse 的"latest open-source implementations"、每项测试预热后连续跑 10 次（其 §4.1），所以**不是**只测单次调用（初版的推断作废）；
   它没给代码链接，公开代码只找到 `iDC-NEU/NeutronSparseLite`，而 Lite 用 MindSpore 现成算子串行计算、没有论文中的定制核、并发流水与运行时迁移（§7）。
   引用 Ascend-SpMM 对 NeutronSparse 的数字时，注明对比对象很可能是 Lite，并优先引其 Table 6（同一内核只换划分，1.23–1.36×）。
5. **顺带发现：** (a) "amazon-product" 在 Table 2 中是 2,449,029 行（即 ogbn-products 的规模），在 Table 4 中却是 1,569,960 行（PyG AmazonProducts 的规模），
   原文前后不一，T16 备数据时须按 Table 2 取 ogbn-products；(b) NeutronSparse 的默认阈值在 Cora 上相当于 τ = 5（84.6% 的行初始进 AIV），本项目第一层用的
   τ = 2、3 对应其扫描范围的低端；(c) 它有逐 epoch 的运行时迁移（按执行时间搬整块 / 整向量）；motivation 已据此删去"划分不再回头调整"半句（用户 2026-11-06 确认，§6）。

---

## 1. 是否带对角（骨架 P12）

| 数据集 | NeutronSparse Table 2 的 NNZ | 对照 | 判读 |
|---|---|---|---|
| cora | 10,556 | 本项目 Cora A0：10,556（2 × 5,278 条无向边，无对角） | 不带对角 ★ |
| ogbn-arxiv | 2,315,598 | 1,166,243 条有向引用边，对称化去重后为 2,315,598（arXiv 2309.11341 表 1 也报此数为无向化后的边数）；加 169,343 个自环应为 2,484,941 | 不带对角【推，数值吻合】 |
| reddit | 114,615,892 | 与 PyG Reddit 的边数相同；是否含自环未核 | 【待核】 |
| amazon-product | 123,718,152（2,449,029 行） | ogbn-products 有 61,859,140 条无向边，2 倍为 123,718,280，差 128，可能是去掉了 64 个自环 | 不带对角【推】 |
| wiki-RfA | 362,053 | SuiteSparse 原文件 188,077 个条目、非对称；362,053 说明它做了对称化 | 对称化；对角未知。T21 的 nnz(A0) 出来后可对照：若同为 362,053，说明预处理与它一致 |
| dawson5、olafu、pattern1、human_gene1 等 | 1,010,777、1,015,156、9,323,432、24,669,643 | 与 SuiteSparse 官方条目数一致 | 按原文件（有限元矩阵自带对角） |

另：§8.6 的端到端是 200 epoch 的 GCN 训练（Table 3），原文没有说 GCN 传播矩阵是否另加自环；内核评测用的就是 Table 2 的矩阵。

**对 P12 的含义（建议，待拍板）：** 与 NeutronSparse 的比较（G1a）以 A0 为主口径；A1 继续并列，代表"把 I 并进稀疏矩阵"的 GCN 实现（如 PyG 的 GCNConv 默认先加自环再归一化）。
目标流水线属于哪种仍未定，所以 P12 不改为单一口径，只把"与 NeutronSparse 比较时用 A0"写明。

## 2. 列抽取的写冲突

- **原文事实 ★：** AIV 执行 Gather 后"accumulated into the output via ScatterAdd"（§5.1）；向量块合并后"performs one ScatterAdd to the target output row"（§7）。
  AIC 以行窗口为单位整块计算，输出按行主序写回（§6.2.2 "Write-back Preference"）。两阶段抽取先按行、再在 AIC 子矩阵里按列抽（§5.2.2、图 9）：
  A1 中被抽走短列的行，一部分非零在 A11（AIC），一部分在 A12（AIV）。
- **原文没有的：** 两种引擎写同一输出行时如何排序、是否原子、开销多少。AIC 侧窗口迁移带来"one extra write to reconcile the migrated windows with their original
  output locations"（§7），说的是 AIC 内部负载均衡，不是 AIC/AIV 之间的冲突。
- **对照：** Ascend-SpMM 实测同一目的区被两种核写时多 14.9% 开销（其 §2.3、图 3(a)），并因此限制块级拆分；它在 Table 6 的说明中称 NeutronSparse 的划分与块级拆分
  "neglect the atomic write conflicts on output matrix"（其 §4.4）——这是他方观点，NeutronSparse 论文本身没有讨论。开源的 Lite 用 `TensorScatterAdd` 合并各部分结果（§7）。
- **对本项目：** 与 T6 现有备注一致——默认整行划分（每个输出行只由一种引擎算），列抽取作为备选须抵过冲突代价。NeutronSparse 的具体做法待读其代码（可与 T10 合并）【待核】。

## 3. 删后的分组细节（空白二转来）

| 步骤 | 原文 ★ | 本项目先导里的 neutron（简化版） |
|---|---|---|
| 划分 | 按 Len(v) ≤ α·K 先抽行、再在 AIC 子矩阵里抽列（§5.2.2）；抽走的部分"completely bypassing reordering"（§8.6） | 先导不做划分（全行排序） |
| 全局阶段 | 二部图 Rabbit Order，对行、列都重编号；"intentionally limit the number of clusters"，簇数未给（§6.1） | 二部图 BFS 近似（不是真 Rabbit），每 8 个窗口（128 行）一个粗范围 |
| 局部阶段 | 每个簇按 M = 128 切行窗口；每窗取一行作 anchor，为每个 anchor 选 M − 1 = 127 个 Jaccard 最相似的未分配行重建窗口；只排行、不改全局列序（§6.1） | anchor + 15 行，窗口 16 行 |
| 成块 | 列压缩后形成 (M, N, K) = (128, 256, 64) 的块（§6.2.2）；局部重排时记录每块密度，供运行时迁移选块（§5.3） | — |
| 运行时 | 逐 epoch 计时，偏差超过 5% 时迁移：AIC 慢则把较稀的块拆成向量给 AIV，AIV 慢则把较稠的向量拼成块给 AIC（§5.3、式 6–7） | — |

**对本项目：**

- `candidates.md` §1 已规定 B-Neutron-ref 按原生 M128 实现，另记 `B-Neutron-ref-W16`；本次读原文确认这一点。T2 实现时：局部阶段用 M = 128，评价时按 W16 与 W128 各算一次。
- 空白二 §4.4 末"同一残余集合下，P-LS 比 NeutronSparse 式重排低 22%"的对照用的是先导的 16 行简化版，**不是**它的 128 行原生做法；T22 的 R3-H9 与 T23 都应在 B-Neutron-ref 完成后补上原生版对照。

## 4. Ascend-SpMM 图 8 与 NeutronSparse 自报结果（2026-11-06 据 Ascend-SpMM 原文重写）

| 项 | NeutronSparse 自报 ★ | Ascend-SpMM 中的 NeutronSparse ★（用户上传全文） |
|---|---|---|
| 用的是什么 | 论文中的完整设计 | "We evaluate the latest open-source implementations of these methods as strong baselines"（§4.1）；只引论文，未给代码链接 |
| 矩阵 | 4 个 GNN 图 + 16 张 SuiteSparse（Table 2） | 820 张 SuiteSparse（≥10K 行列、≥100K nnz）（§4.1） |
| NPU 基线 | MindSporeGL（主要用 AIV）、作者重实现的 AIC 内核 | Naive CSR、Moustafa（Ascend-SpMM 作者自实现）、NeutronSparse |
| 设备与软件 | 910B（24 AI Core），CANN 8.0.1 | Atlas 800I A2（20 AIC + 40 AIV），CANN 8.5.0（§4.1、Table 2） |
| 计时 | 逐 epoch，迁移约 7–10 个 epoch 收敛，收敛后比初始划分快 3.83×（§8.3、图 17、图 18） | "run ten consecutive times with warm-ups … using msprof"（§4.1） |
| 结果 | 对 MindSporeGL 平均 3.48×，对 AIC 内核 3.25×（§8.2）；对 AIV-only 3.71×（§8.3） | 图 8：与 Naive CSR 同处低位，部分点 OOM；Table 6 只换划分策略时比 NeutronSparse 的划分快 1.23–1.36× |

**判读：**

1. 初版"Ascend-SpMM 只测单次调用、NeutronSparse 停在初始划分"的推断**作废**：它预热后连续跑 10 次。
2. 公开可得的 NeutronSparse 代码只找到 `iDC-NEU/NeutronSparseLite`（§7）。Lite 用 MindSpore 现成算子在 Python 循环里串行计算，没有论文中的定制核、两引擎并发与运行时迁移；
   若 Ascend-SpMM 测的是它，图 8 落到与 Naive CSR 相近的低位并不意外，逐窗口转稠密块也可能是 OOM 点的来源【推】。
3. Table 6 中"NeutronSparse 的划分"是按论文（α·K）还是按 Lite 的阈值实现，原文未说【待核】。
4. **引用纪律：** 说 NeutronSparse 时以论文为准；引用 Ascend-SpMM 对 NeutronSparse 的比较时注明"对比对象很可能是开源的 Lite 版"，优先引 Table 6，不引图 8 的十几倍。
   本项目 G1 比的是结构指标（相同 AIC nnz 占比下的 T、ΣU），不受此影响。

## 5. 顺带发现

1. **amazon-product 的身份（影响 T16）。** Table 2 是 2,449,029 行、123,718,152 个非零（ogbn-products 的规模）；Table 4 是 1,569,960 行（PyG AmazonProducts 的规模），
   且 Table 4 正文说比较的是"cora、ogbn-arxiv 和 reddit"，与表中所列不符。内核评测以 Table 2 为准，T16 备数据时取 **ogbn-products**。
2. **阈值换算（影响 T22、T23 的 τ）。** Thres = α·K，K 为列数（§5.2.2 式 5）；默认 α = 2×10⁻³（§8.3），扫描范围 1–10 ×10⁻³。Cora（K = 2,708）上默认阈值 5.4，
   即非零 ≤ 5 的行初始进 AIV，占 84.6% 的行、59.4% 的非零；本项目 τ = 2、3 相当于 α ≈ 0.7×10⁻³、1.1×10⁻³。大图上 α·K 很大（ogbn-arxiv 约 339），按它的规则几乎所有行
   都初始进 AIV，故其最终划分主要由运行时迁移决定。第一层用的 nz_r ≤ τ 仍是方向中性的替身（P6），不追随它的阈值。
3. **运行时迁移与 motivation 措辞（已处理）。** 原文 §5.3 有逐 epoch 的负载迁移：AIC 慢时把较稀的整块拆成向量交给 AIV，AIV 慢时把较稠的向量拼成块交给 AIC，
   依据是两引擎的执行时间差。`流程图.md` motivation 中"划分不再回头调整"半句因此删去（用户 2026-11-06 确认）；运行时迁移在相关工作中如实写明，**不与本项目对比**——
   本项目尚未设计两引擎的负载均衡（T6 备注：待第 5、6 层后设计），不能暗示本项目"按窗口结构做负载调整"。
4. **它自己的消融（可供引用）：** 重排使块密度平均提高 10.06×（全局 3.44×，再加局部）（§8.4、图 21）；重排带来 2.17× 加速，块复用再 1.42×（图 20）；
   默认块形 (128, 256, 64) 比 (16, 16, 16) 快 3.39×（图 22）；预处理（划分 + 重排）约占 200 epoch GCN 总时间的 5.9%（Table 3）。

## 6. 待拍板（超出 T19 的部分）——2026-11-06 均已答复

| 条 | 内容 | 用户决定 |
|---|---|---|
| 1 | P12 补一句：与 NeutronSparse 比较（G1a）时以 A0 为主口径；A1 仍并列，主口径仍待目标流水线定 | 同意 |
| 2 | motivation 措辞：初版建议改为"划分之后只按执行时间搬整块 / 整向量，不按窗口结构调整行的去留"——用户指出此句暗含"本项目的负载均衡按窗口结构调整"，而本项目尚未研究负载均衡。改为**只删去"划分不再回头调整"半句**，运行时迁移在相关工作中如实写明 | 同意（修正后） |
| 3 | T16：amazon-product 按 NeutronSparse 正文主表（Table 2）取 ogbn-products（2,449,029 点） | 同意 |
| 4 | T2：B-Neutron-ref 按论文实现（局部阶段 M = 128，评价报 W16 与 W128），不按开源的 Lite | 确认（属 T2 规格，与 `candidates.md` §1 一致） |
| 5 | 由第 2 条引出：T6 的"逐行取小者"只在两引擎串行时成立；两引擎并行时目标是较慢者的完成时间。用户认为负载均衡应在第 5、6 层完成后再设计，规划方同意，只在 T6 加备注 | 同意加备注 |

## 7. 开源的 NeutronSparseLite（2026-11-06 补）

来源：`https://github.com/iDC-NEU/NeutronSparseLite`（NeutronSparse 作者所在的东北大学 iDC-NEU 组织；最近提交 2026-06-14，早于 arXiv v1 的 2026-06-21）。只读未运行。
NeutronSparse 论文与第一作者主页都没有代码链接；组织页面可见的仓库中只有它与 NeutronSparse 相关（48 个仓库只显示了 10 个，其余未核）【待核】。

| 方面 | 论文 | Lite（代码 ★） |
|---|---|---|
| 计算实现 | 自写 AIC / AIV 核（MatMul、Gather + ScatterAdd、双缓冲、向量块合并） | MindSpore 现成算子：A11 每窗口 `COOTensor.to_dense` 后 `ops.matmul`；A12、A2 用 `TensorScatterAdd`；PyNative 模式，Python 循环逐窗口 |
| 两引擎并行 | 并发、协同流水 | `forward` 依次算 A11、A12、A2，再合并 |
| 运行时迁移 | 有（§5.3） | 无 |
| 阈值 | α·K，α 由微基准得到（默认 2×10⁻³） | `max(4, int(平均度 × a))`，a 按稀疏度分档（0.25 / 0.55 / 1.0 / 1.8）；Cora 上为 4（约 74% 的行进 AIV） |
| 抽取顺序 | 先行后列 | 先列后行 |
| 重排 | 二部图 Rabbit + 簇内 128 行 anchor-Jaccard；抽走的行不重排 | 划分**之前**对整张图跑 Rabbit；anchor-Jaccard 的 C++ 代码整段被注释 |
| 块形 | (128, 256, 64) | 行窗口 2048 行（默认 8192）、列块宽 32 |
| AIC 侧格式 | BitMap | COO → 稠密块，不用 Bitmap |
| L2 预置 | 有 | 无 |

**对本项目：** (1) T2 按论文实现，不按 Lite；(2) T10 的部分答案：Lite 不用 Bitmap（AIC 侧是 COO 转稠密块再 matmul），论文完整版的做法仍未知；
(3) Lite 是"先对全图重排、再抽取"，与论文 §8.6 的"抽走的行跳过重排"顺序相反，同一组作者的两个版本在这一步顺序上就不一致——与空白二"这一步顺序本身影响很小"相容，只作旁注。

## 来源

- Ai, Ling, Yuan, Wang, Zhang, Peng & Yu, *NeutronSparse: Coordinating Heterogeneous Engines for Sparse Matrix Multiplication on NPUs*, arXiv 2606.22482v1, 2026（仓库 `文献pdf/`）；
  据东北大学教师主页发表于 SIGMOD 2026（PACMMOD）。https://faculty.neu.edu.cn/zhangyf/en/lwcg/39667/content/37663.htm
- Wang, Shao, Wang, Ge, Li & Zhang, *Ascend-SpMM*, arXiv 2611.01936v1（用户上传全文，§4.1、§4.4、Table 6、图 8）。
- `iDC-NEU/NeutronSparseLite`（commit `a84e9ac`，2026-06-14）。https://github.com/iDC-NEU/NeutronSparseLite
- *Article Classification with Graph Neural Networks and Multigraphs*, arXiv 2309.11341，表 1（ogbn-arxiv 无向化后 2,315,598 条边）。https://arxiv.org/pdf/2309.11341
- 项目文档《RSH-NPU-Ascend-SpMM阅读记录-20261105》（Ascend-SpMM 图 8、Table 6、§2.3 的转述）；`讨论记录/2026-11-03-路线评审/02-motivation与NeutronSparse差异.md`。
- 本稿自算：Cora 度数分布（`T17-空白一试算脚本/rq2lib.load_cora`）。
