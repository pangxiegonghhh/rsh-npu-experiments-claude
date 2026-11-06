# T19：NeutronSparse 实验章节与相关方法细节核对

状态：2026-11-06（北京时间）规划方完成。读的是仓库 `文献pdf/` 中的 NeutronSparse 全文（arXiv 2606.22482v1，2026-06-21，28 页），
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
4. **Ascend-SpMM 图 8（NeutronSparse 与 Naive CSR 同档）与 NeutronSparse 自报结果不能直接对比，但有一个可能的解释【推】：** NeutronSparse 的静态划分只是初值，
   它靠逐 epoch 的计时反馈迁移负载，约 7–10 个 epoch 收敛，收敛后比初始划分快 3.83×（§8.3、图 17）；在 ogbn-arxiv 上默认阈值约 339，初始几乎全部行都进 AIV。
   若 Ascend-SpMM 按单次调用测内核，NeutronSparse 只能用初始划分运行，落到低位并不意外。二者的基线（MindSporeGL 对作者自实现的 Naive CSR）与矩阵集
   （20 张对 820 张）也不同。Ascend-SpMM 如何运行 NeutronSparse（官方代码还是自实现、是否预热）须读其 §4.1 原文确认【待核】。
5. **顺带发现：** (a) "amazon-product" 在 Table 2 中是 2,449,029 行（即 ogbn-products 的规模），在 Table 4 中却是 1,569,960 行（PyG AmazonProducts 的规模），
   原文前后不一，T16 备数据时须按 Table 2 取 ogbn-products；(b) NeutronSparse 的默认阈值在 Cora 上相当于 τ = 5（84.6% 的行初始进 AIV），本项目第一层用的
   τ = 2、3 对应其扫描范围的低端；(c) motivation 中"划分不再回头调整"的措辞需更精确：它**会**在运行时迁移，只是依据执行时间与块密度，不看窗口结构（见 §6 待拍板）。

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
- **对照：** Ascend-SpMM 实测同一目的区被两种核写时多 14.9% 开销（其 §2.3、图 3(a)），并因此限制块级拆分。
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

## 4. Ascend-SpMM 图 8 与 NeutronSparse 自报结果

| 项 | NeutronSparse 自报 ★ | Ascend-SpMM 中的 NeutronSparse（据项目文档《Ascend-SpMM 阅读记录》） |
|---|---|---|
| 矩阵 | 4 个 GNN 图 + 16 张 SuiteSparse（Table 2） | 820 张 SuiteSparse（≥10K 行列、≥100K nnz） |
| NPU 基线 | MindSporeGL（主要用 AIV）、作者重实现的 AIC 内核 | Naive CSR、Moustafa（均为 Ascend-SpMM 作者自实现）、NeutronSparse |
| 结果 | 对 MindSporeGL 平均 3.48×，对 AIC 内核 3.25×（§8.2）；对 AIV-only 3.71×（§8.3） | 图 8：与 Naive CSR 同处低位，部分点 OOM |
| 运行方式 | 逐 epoch 迁移，约 7–10 个 epoch 收敛，收敛后比初始划分快 3.83×（§8.3、图 17、图 18）；默认阈值 2×10⁻³ | 未核 |

**判读【推】：** 二者不能直接对比，但不一定矛盾。NeutronSparse 的性能依赖迁移收敛；ogbn-arxiv 上 K = 169,343，默认阈值 α·K ≈ 339，而平均行长 13.6，
初始几乎全部行进 AIV（`讨论记录/2026-11-03-路线评审/02-motivation与NeutronSparse差异.md` 已指出）。若 Ascend-SpMM 只测单次调用，NeutronSparse 停在初始划分，
吞吐落到与 Naive CSR 相近的低位是可能的。**引用 Ascend-SpMM 对 NeutronSparse 的数字时须注明这一差别**；本项目 G1 比的是结构指标（相同 AIC nnz 占比下的 T、ΣU），
不受此影响。确认需读 Ascend-SpMM §4.1 对 NeutronSparse 的运行说明【待核】。

## 5. 顺带发现

1. **amazon-product 的身份（影响 T16）。** Table 2 是 2,449,029 行、123,718,152 个非零（ogbn-products 的规模）；Table 4 是 1,569,960 行（PyG AmazonProducts 的规模），
   且 Table 4 正文说比较的是"cora、ogbn-arxiv 和 reddit"，与表中所列不符。内核评测以 Table 2 为准，T16 备数据时取 **ogbn-products**。
2. **阈值换算（影响 T22、T23 的 τ）。** Thres = α·K，K 为列数（§5.2.2 式 5）；默认 α = 2×10⁻³（§8.3），扫描范围 1–10 ×10⁻³。Cora（K = 2,708）上默认阈值 5.4，
   即非零 ≤ 5 的行初始进 AIV，占 84.6% 的行、59.4% 的非零；本项目 τ = 2、3 相当于 α ≈ 0.7×10⁻³、1.1×10⁻³。大图上 α·K 很大（ogbn-arxiv 约 339），按它的规则几乎所有行
   都初始进 AIV，故其最终划分主要由运行时迁移决定。第一层用的 nz_r ≤ τ 仍是方向中性的替身（P6），不追随它的阈值。
3. **运行时迁移与 motivation 措辞（待拍板）。** `流程图.md` 的 motivation 写"划分与成窗脱钩……划分不再回头调整"。原文 §5.3 有逐 epoch 的负载迁移：AIC 慢时把较稀的
   整块拆成向量交给 AIV，AIV 慢时把较稠的向量拼成块交给 AIC。它确实回头调整，但只按两引擎的执行时间差、以整块或整向量为单位，不看一行与窗口内其他行的列重叠。
   审稿人可能据 §5.3 质疑"不再回头调整"。建议改为"……划分之后只按执行时间做整块 / 整向量的迁移，不按窗口结构调整行的去留"（动 motivation 措辞，须用户拍板）。
4. **它自己的消融（可供引用）：** 重排使块密度平均提高 10.06×（全局 3.44×，再加局部）（§8.4、图 21）；重排带来 2.17× 加速，块复用再 1.42×（图 20）；
   默认块形 (128, 256, 64) 比 (16, 16, 16) 快 3.39×（图 22）；预处理（划分 + 重排）约占 200 epoch GCN 总时间的 5.9%（Table 3）。

## 6. 待拍板（超出 T19 的部分）

1. **P12 补一句**：与 NeutronSparse 比较（G1a）时以 A0 为主口径；A1 仍并列，主口径仍待目标流水线定。
2. **motivation 措辞**：把"划分不再回头调整"改为"划分之后只按执行时间做整块 / 整向量的迁移，不按窗口结构调整行的去留"，并在出处中引 NeutronSparse §5.3。
3. **T16**：amazon-product 明确为 ogbn-products（2,449,029 点）；第二批数据中 reddit 的自环情况核对后再定 A0 预处理。
4. **T2**：B-Neutron-ref 局部阶段按 M = 128 实现，评价报 W16 与 W128 两套（与 `candidates.md` §1 一致，只是确认）。

## 来源

- Ai, Ling, Yuan, Wang, Zhang, Peng & Yu, *NeutronSparse: Coordinating Heterogeneous Engines for Sparse Matrix Multiplication on NPUs*, arXiv 2606.22482v1, 2026（仓库 `文献pdf/`）。
- *Article Classification with Graph Neural Networks and Multigraphs*, arXiv 2309.11341，表 1（ogbn-arxiv 无向化后 2,315,598 条边）。https://arxiv.org/pdf/2309.11341
- 项目文档《RSH-NPU-Ascend-SpMM阅读记录-20261105》（Ascend-SpMM 图 8、Table 6、§2.3 的转述）；`讨论记录/2026-11-03-路线评审/02-motivation与NeutronSparse差异.md`。
- 本稿自算：Cora 度数分布（`T17-空白一试算脚本/rq2lib.load_cora`）。
