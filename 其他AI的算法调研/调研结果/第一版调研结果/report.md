# 面向紧凑 NPU row window 的行重排与聚类调研

初版日期：2026-10-30；更新：2026-10-31。依据：[调研目的及方法](../调研目的及方法.md)、[输出结果](../输出结果.md)。截图 22 项、近期工作补读和附件身份核验见 [10 月 31 日补充报告](update-20261031/report.md)。

**最新全文补读：**用户已提供匹配的 AFH 和 BlockSmith 完整正式 PDF，两篇相关算法部分均已核对，见 [全文补读结论](fulltext-afh-blocksmith-20261031/report.md)。BlockSmith 直接补强 C3，并保留 C3-A 自动宽度作补充；AFH 定位为后续窗口内块构造/路由参考。

## 结论与交付

建议保留六类主候选：**Groot 式近邻图与树遍历、DTC 式 LSH 聚类、BlockSmith 式限容量在线聚类、HC-SpMM 的窗口密度贪心、Rabbit 与局部窗口重组、SLAWS 启发的交集收益选行**。在度量、特征宽度及评分上保留少量变体，共九个主配置；另保留 C3-A 自动宽度和超图路线作补充。**RSH 与 Neutron 的论文重排参考另行单列**，不与 Cora 简化原型或 C5 适配混为一项。具体输入、步骤、参数和待验证假设见 [candidates.md](candidates.md)。

本轮补查表明此前 2026 年覆盖不足。已筛查截图 22 项，其中 8 项是 2026 年；TileSpMM 对后续窗口划分有直接启发，SLAWS 可拆出当前层的选行模块。最初 AFH 无全文、BlockSmith 的 Zotero 附件实为 Swift；随后用户补充了两篇匹配全文，当前限制与结论见最新补读。原错配附件不能用于 BlockSmith 正文证据。

当前没有哪一项已经在本项目的新候选比较中胜出。本轮完成的是来源核验、方法比较和候选设计，尚未实现或运行这些新候选。

完整文献范围与阅读定位见 [literature.md](literature.md)，检索过程和受限来源见 [search-log.md](search-log.md)。

## 1. 问题应怎样表达

令一行的原始非零列支持集为 $S_r$，评价窗口 $w$ 包含行集合 $R_w$，定义：

$$
U_w=\left|\bigcup_{r\in R_w}S_r\right|,\qquad
z_w=\sum_{r\in R_w}|S_r|,\qquad
T_w=\left\lceil U_w/K_0\right\rceil.
$$

在相同输入、固定高度 $W$ 和列块宽度 $K_0$ 下，主要目标是减小 $\sum_w T_w$ 及对应填充容量，同时记录 $\sum_w U_w$ 和预处理成本。相邻行相似度是代理指标；它能帮助构造行序，但一个好行序是否形成好窗口，还取决于窗口边界和整组行的列并集。

以下两个区分直接影响算法选型：

- **原始列空间的块密度与列压缩后的块密度。** SMaT 的 BCSR 块保留原始列块边界；本项目在窗口内删除空列后再按 K16 分组。原始块数下降，需要在紧凑列空间重新评价，才能判断对这里有多少帮助。[SMaT §IV-B–C](https://arxiv.org/html/2408.11551v1#S4)
- **行序与行分组。** Groot/RSH 主要输出排列；DTC、BlockSmith、LOA 等显式构造行组。后者可输出展平的行序，并附带行组边界供诊断。后续细粒度分流仍应使用统一规则，不能把候选生成的行组直接当成已确定的最终 NPU 窗口。

固定行组时，任意双射列置换 $q$ 都满足 $|q(\cup_r S_r)|=|\cup_r S_r|$，所以单独改列号不会改变 $U_w$ 和上述紧凑 Tile 数。它可以改变连续列段、B 地址局部性或粗聚类过程，相关收益需要分别记录。这一结论由集合双射性质推出，不是某篇论文的性能结论。

## 2. 用户补充线索的核验

UBT 是 **Ultra-dense Block Transformation**，属于 BlockSmith 的预处理框架；可变宽度相似性、iterative clustering 和聚类后处理都是该框架的组成部分。它们可以拆成不同模块做比较，但不应计为四篇互不相关的算法论文。[BlockSmith §4](https://doi.org/10.1145/3828547)

可迁移的具体部分是：用 $F_b(r)=\{\lfloor j/b\rfloor:j\in S_r\}$ 压缩行特征；按代表行接受新成员；行组达到目标高度后停止接收；再处理未满行组。这里 $b$ 是**相似性特征宽度**，不等于后端 K16。签名相似并不保证原始列重合，最终仍用原始 $S_r$ 计算结构指标。[作者聚类代码](https://github.com/CGCL-codes/BlockSmith/blob/bf7348d0ba64b7b1eee8ac014a0ca4162b1d7717/preprocess/src/matrix_reorder_cuda.cu)

## 3. 各路线的作用与取舍

| 路线 | 已核验机制 | 适合本项目的部分 | 主要不确定性 |
|---|---|---|---|
| Groot / RSH | 稀疏相似性近邻图，生成树与遍历；RSH 另有局部调整 | 保留现有“先行序、后划分”的接口；用近似近邻控制候选搜索 | 邻接路径目标与固定窗口 Tile 目标不完全一致；近似近邻可能漏掉好邻居 |
| DTC-SpMM | MinHash/LSH 找相似行对，再按相似度合并；另有缓存层重聚类 | 将候选发现和组内组织分开；为容量约束提供自然对照 | 作者实现的合并可能超过阈值；LSH 大桶仍可能产生大量行对 |
| BlockSmith | 粗粒度二值特征、代表行在线聚类、满组退出、未满组重组 | 直接研究特征精度、容量约束和窗口边界 | 粗签名可能误合并；活跃组过多时仍可能接近二次比较 |
| HC-SpMM LOA | 在有限候选范围内，反复选使窗口 NNZ/列并集最大的行 | 目标直接对应列压缩后的平均列复用；可加入 K 对齐评分 | 局部贪心可能牺牲后续窗口；分子偏好长行的影响需测试 |
| Neutron + Rabbit | Rabbit 粗粒度组织，组内 anchor-Jaccard 重建窗口 | 用已有社区算法缩小局部搜索范围，再接窗口层 | 粗聚类可能把共享列的行分开；原论文与现有简化原型不同 |
| SLAWS 启发 | 交集 score table、块排序、按复用成本融合行；原对象为 SpMSpM | 抽出交集驱动选行作为 C7-I，与 C4 单独比较评分 | 稀疏 B 的成本不能照搬；最大交集不保证新增列少 |
| AFH-SpMM（后续层） | 固定16行内用列行签名选Dense、检查余下Row24成本，再进行局部匹配 | 窗口内选列、块类型及残余成本的联合判断 | 不改变当前行成员；Row24依赖GPU稀疏TC，不能直接当作NPU路径 |
| 超图划分 | column-net 模型与 connectivity 目标 | 直接表达窗口列并集总量，作有不同目标依据的补充 | 小容量精确划分和大量分区的成本；K 对齐舍入未被直接优化 |

来源：[Groot 作者仓库](https://github.com/yuang-chen/Groot-EuroSys25)、[RSH §3.4](https://arxiv.org/html/2603.08734v1#S3.SS4)、[DTC §4.3](https://home.cse.ust.hk/~weiwa/papers/dtc-spmm-asplos24.pdf)、[BlockSmith 作者实现](https://github.com/CGCL-codes/BlockSmith)、[LOA §V-B](https://arxiv.org/html/2412.08902v1#S5.SS2)、[Neutron §6.1](https://arxiv.org/html/2606.22482v1#S6.SS1)、[KaHyPar](https://kahypar.org/)。

### 3.1 从行对相似性走向窗口目标

Groot 的作者 C++ 实现使用稀疏 Hamming 距离、KGraph、MST 和 DFS；后来的 Python 版本提供 Jaccard/Hamming 及遍历选项。两种距离对行长度的偏好不同，因此保留一个度量变体有比较价值。不能把仓库中后加的 Python 选项都称为论文原算法。[Groot README 与实现](https://github.com/yuang-chen/Groot-EuroSys25/tree/a591f4152ca0d30d9e75002aa0542dbd4139edd2)

RSH 的加权 Jaccard 会减弱高频列的影响，原目标是减小沿行序累计的不相似度。它与本项目按每个原始列计数的窗口并集目标有联系，也有差异；既有原型可以作基线，不必成为所有候选的固定算法骨架。[RSH §3.4](https://arxiv.org/html/2603.08734v1#S3.SS4)

LOA 将比较对象从“行与行”改为“候选行加入当前窗口后的密度”。本项目可保留原始 $z/U$ 评分，并构造 $z/(W K_0\lceil U/K_0\rceil)$ 变体，检验硬件块边界是否改善最终 Tile 数。这一变体属于本项目适配设计，不宣称是 LOA 原文已有方法或新的已验证贡献。[HC-SpMM 算法 5–6](https://arxiv.org/html/2412.08902v1#S5.SS2)

### 3.2 聚类结果如何变成连续窗口

相似性聚类产生的组大小不一定整除 $W$。如果简单拼接，组可能被窗口边界切开，部分窗口又混入不相似的组。BlockSmith 的后处理专门处理这一问题，其公开代码按组大小排序，再在容量允许时合并较小组；这一步本身需要单独观察成本和效果。[作者后处理代码](https://github.com/CGCL-codes/BlockSmith/blob/bf7348d0ba64b7b1eee8ac014a0ca4162b1d7717/preprocess/src/matrix_reorder.cpp)

DTC 的论文伪代码与作者代码均是在合并达到阈值后冻结聚类，因此组可能超过 $W$。候选 C2 加入“合并后大小不得超过 $W$”是明确的本项目改动，结果应称为 DTC 式适配。这个区别也说明：给算法加一个 W16 参数，尚不足以证明它已按 W16 形成窗口。[DTC 作者代码](https://github.com/HPMLL/DTC-SpMM_ASPLOS24/blob/66eca266bde1f3faf5f8ef7a054db2391b50e27d/reordering/TCA_reorder.py)

### 3.3 借用已有算法的具体方式

Neutron 的组合方式已经从原文核实：全局阶段把稀疏矩阵表示为二部图，借用 Rabbit 重排相关行列；局部阶段在粗聚类内，用代表行及 Jaccard 重新组织窗口。Rabbit 提供已有社区结构组织方法，Neutron 再把它接到面向 Tile 的局部处理上。其论文该处使用的目标高度 $M$ 为 128，本项目 W16 是另一个适配条件。[Neutron §6.1](https://arxiv.org/html/2606.22482v1#S6.SS1)

现有 Cora 原型中的 Rabbit 风格方法是二部图遍历，Neutron 风格方法是粗顺序分组加局部组织；它们不能替代真正 Rabbit 或 Neutron 的算法比较。候选 C5 要使用作者 Rabbit 实现产生的行序或社区，再接明确定义的局部步骤。[Rabbit 作者仓库](https://github.com/araij/rabbit_order)

## 4. 超图路线为什么值得保留

以行为顶点、每个非空列为一条超边。若列 $j$ 出现在 $\lambda_j$ 个窗口中，则由重复计数得到：

$$
\sum_w U_w=\sum_j\lambda_j
=n_{\mathrm{nonempty\ columns}}+\sum_j(\lambda_j-1).
$$

所以，固定行组容量时，最小化 column-net 的 connectivity-1 目标，等价于最小化窗口列并集总量。column-net 与 connectivity 定义来自已有超图研究；上述对应本项目窗口指标的等式是这里的推导。[Yamazaki 等的模型定义](https://portal.nersc.gov/project/sparse/xiaoye-web/ipdps13.pdf)、[KaHyPar 目标定义](https://kahypar.org/)

但 $\sum_w\lceil U_w/K_0\rceil$ 还有每个窗口的对齐舍入，二者并非完全相同。通用划分器也不保证输出恰好 W 行的组：KaHyPar 的文档明确说明精确平衡的限制。故 C6 包含容量检查与显式修复，并要求在修复后重新评价。它是补充路线，不能冒称密度上界或全局最优解。

## 5. 未进入首轮主候选的工作

本轮还检索并记录了 SMaT/1-SA、BSA、Acc-SpMM、ASpT-RR、DDB、FlashSparse、cuTeSpMM、Rabbit++、图重排评价研究、N:M 重排及 SDDMM 的 BSMR，见文献表。保留或暂缓的理由如下：

- **SMaT/1-SA/BSA：**提供粗粒度行特征与聚类思路，但需要区分原始 BCSR 块目标与紧凑列空间目标。SMaT 正文已读；1-SA、BSA 原始全文本轮未取得，不能按二手描述直接给它们贴上忠实复现标签。
- **Acc-SpMM/Rabbit++：**社区与树形组织可作粗阶段的替代；先保留 Rabbit 路线，以控制候选数量。Acc-SpMM 的数据亲和重排不是简单的“Jaccard+MST”。
- **ASpT-RR：**LSH 加速层次聚类是 DTC 的相关前驱；本轮取得会议摘要，未取得原文完整工程细节，首轮采用证据更充分的 DTC 式方案。
- **FlashSparse、cuTeSpMM、DDB：**说明逻辑粒度、数据组织和矩阵单元适配也会改变有效计算密度，但其主要贡献不等于一个可直接替换本层的行序算法。相关设计留给后续 Tile/格式/执行层。
- **N:M 重排、BSMR：**分别面向结构化稀疏约束及 SDDMM 稠密/稀疏块组织，目标与当前一般无损 SpMM 的列压缩不同；不直接照搬其硬件结论。
- **Fused3S 的 row-window reordering：**对已经形成的窗口重新排序以平衡执行，保持窗口成员时不会降低本项目的窗口并集或 Tile 总数。

上述判断只说明对本次候选集的适配性，不评价论文整体质量。

## 6. Cora 先导结果的定位

对用户提供的原包进行了只读检查，没有执行归档脚本。包 SHA-256 为 `3edb393a142c0efc7088314f2887069886e7a570e262a61a2137d8422b7662f8`。包内三项输入/源码哈希通过；从 Matrix Market 对称展开后，独立核对了八份排列、逆映射、窗口列集合、NNZ、K16 数与相邻 Jaccard。详见 [cora-pilot-audit.json](cora-pilot-audit.json)。

输入为 $2708\times2708$，文件存储 5278 项，按 symmetric 展开后 NNZ=10556。row_only 口径如下：

| 归档原型 | 窗口列并集总量 | K16 Tile 总数 | 按 M16/K16 补齐容量计算的整体占用率 |
|---|---:|---:|---:|
| original | 9583 | 681 | 6.055% |
| rsh | 6035 | 455 | 9.063% |
| rabbit 风格 | 7678 | 553 | 7.456% |
| neutron 风格 | 7595 | 554 | 7.443% |

整体占用率采用总 NNZ/总物理槽位，与归档中逐窗口占用率的算术平均不是同一指标。这些数值只支持“该输入上现有简化原型的结构变化”，不证明论文方法优劣、跨矩阵稳健性或 NPU 加速。原包没有完整设备环境与命令记录，归档预处理时间本轮未重测。

## 7. 后续比较应验证什么

按 [评价指标与验收](../评价指标与验收.md)进行同输入、同规则评价。六类主候选的九个配置先在 CPU 结构层比较，同时保留原序、历史原型与单列的论文重排参考项，记录正确性、总 Tile、总列并集、整体占用率、时间和峰值内存。每个配置使用同一套全局参数；近似搜索记录随机种子及候选规模。首轮矩阵延续已有候选集并按实际文件核验身份，不用 Cora 单矩阵结果确定赢家。

第一层比较固定评价用 W/K，所有行保留，主结果采用原始列编号。对能够形成行组的算法，同时报告其内部组与最终连续 W 行评价窗口的对应关系。后续接细粒度分流时，固定同一分流规则和参数再比较各行序，并同时报告残余工作量。

候选的必要变体只改变一个模块：C1 的距离、C3 的特征宽度、C4 的评分。短组后处理开关只在预先指定的 C3-W4 上做一次消融，不与所有配置交叉组合。具体配置表见 [candidates.md](candidates.md)。

## 8. 证据边界

核心选择依据来自论文相关章节和作者公开代码；未获取全文的工作已逐项标注。本地六源检索脚本因网络解析失败没有得到有效 API 记录，不能宣称六个数据库已穷尽；出版方部分入口亦有 403/429。网页检索、论文参考文献和作者仓库仍覆盖了上述不同路线。

本轮不宣称发现新的研究贡献，也不将 GPU 论文整体加速比外推到 NPU。候选的参数、容量修复和对齐评分均明确标为适配设计，实际效果留待后续统一实验。
