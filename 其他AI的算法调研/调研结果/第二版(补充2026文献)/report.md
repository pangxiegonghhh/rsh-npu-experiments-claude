# Zotero 候选与 2026 年文献补充核验

日期：2026-10-31。补充上一版 [调研报告](../report.md)，不修改已确认的三份研究约定，不涉及算法运行或设备实验。

**后续全文补证：**本报告初次记录时AFH无本地附件、BlockSmith的Zotero附件错配。用户随后已提供两篇匹配正式PDF并完成相关算法补读，见 [最新结论](../fulltext-afh-blocksmith-20261031/report.md)。下文原Zotero入库计数仍是当时集合快照，不代表目前仍缺这两篇全文。

## 1. 对两个问题的回答

上一版对近期文献覆盖不足。原文献表 25 项中，按表中年份计算，2026 年工作只有 RSH、Neutron、BlockSmith、BSMR 四项。全文入口受限确实存在，但不能把覆盖不足都归因于拿不到文章：用户本地 Zotero 已保存多篇相关全文，本轮可以直接读取。

上一条五行表格主要列新增探索路线，并没有明确列出参考对照。RSH 被放在 Cora 简化原型基线 B1，Neutron 的思路放进了 C5；这不等于已安排了两篇论文方法的独立参考比较。尤其 C5 的固定粗范围和 W16 是项目适配，不能直接标成 Neutron 原方法。本轮已在 [候选表](../candidates.md) 单列 B-RSH-ref、B-Neutron-ref，并保留它们与历史原型、项目适配之间的区别。参考项目前是待落实的比较要求，未声称实现完成。

## 2. 本轮资料范围与身份检查

- 截图对应 Zotero 的“02 方法参考”集合，共 **22 项，其中 8 项为 2026 年**；21 项有本地 PDF，AFH-SpMM 无附件。这 21 项的首页题名均与条目相符。
- 额外读取/核查 RSH、Neutron、AsyncSparse、Segmented Operations 和 BlockSmith 条目。前四项附件匹配；**BlockSmith 条目附件实际是 Swift（HPCA 2026）**，不能用它支持 BlockSmith 的算法描述。初次据此依赖作者代码与出版方段落；后续已由用户新PDF补足正式全文，原Zotero附件未替换。
- RSH 本地 PDF 是 arXiv v1，Neutron 本地 PDF 也是 arXiv v1；Zotero 条目已填正式 DOI，不代表附件已经更新为正式出版版本。Neutron 的局部窗口高度 M=128 是此 v1 的配置。Segmented Operations 本地附件为 arXiv v2。
- 对匹配的附件筛读摘要与设计概述；对 TileSpMM、SLAWS、Groot、RSH、Neutron 等进一步核对相关算法章节。没有把“全文可取得”写成“整篇逐页精读”。TileSpMM 图 4、SLAWS 行融合公式页、Groot 稀疏 Hamming 算法页另做了页面渲染核对。

条目、附件路径、SHA-256 与提取文本见 [zotero-corpus.json](zotero-corpus.json)。库与附件只读，查询使用临时 SQLite/WAL 副本；本轮没有修正 Zotero 条目或替换 PDF。

## 3. 截图 22 项的逐项探索

下表页码均为 PDF 文件页序，从 1 开始。层次判断针对本项目用途，不评价论文整体质量。

| 截图论文 | 年份 | 已核对机制与阅读定位 | 与当前目标的关系、处理决定 |
|---|---:|---|---|
| A Probabilistic Perspective on Tiling Sparse Tensor Algebra（D2T2） | 2025 | 摘要、稀疏统计建模与 tile 搜索概述；以输入统计预测访存，搜索 tile 形状/大小；主评估含 SpMSpM | 后续 Tile 成本建模参考；不是直接输出相似行排列的算法 |
| Adaptive Matrix Multiplication for Dynamic Shapes on Ascend NPUs（AdaptCore） | 2026 | 摘要、§3–5 概述；稠密 MatMul 的空间 tiling、指令编排与解析模型 | 有助于后端形状选择和成本解释；没有据此新增行聚类候选 |
| AFH-SpMM | 2026 | 初次Zotero无附件；后续用户提供正式全文并读§3.2–3.4、图1–3和算法1 | 固定16行内选列与Dense/Row24块构造，保留为F-AFH后续层参考，见最新补读 |
| ENEC | 2026 | 摘要、§IV–V 设计概述；模型权重无损编码、定长分块、位打包和分段 scan | 压缩/解码实现参考；不属于行重排聚类 |
| FlashSparse | 2025 | 摘要、swap-and-transpose 设计；减小稀疏计算粒度并改善数据装载 | 后续逻辑 Tile/执行粒度参考；已在旧表 P17，补上本地全文证据 |
| FuseFlow | 2026 | 摘要、编译流程概述；跨稀疏表达式融合、阻塞和数据流搜索，目标为可重构数据流架构 | 后续多算子/编译层参考；没有抽出独立行重排算法 |
| GeneralSparse | 2025 | §3.1–3.2，PDF p.5 起；row/split 两维稀疏分配空间与 reduction 选择 | 多行处理不等于改变行成员；主要供给/调度层参考 |
| Groot | 2025 | §4.1–4.4、算法 3–7，PDF pp.5–8；Hamming、KGraph、生成森林与先序遍历 | 保留 C1；全文确认 Hamming 是论文的关键选择，Jaccard 是比较变体 |
| Harmonia | 2026 | §III–IV，PDF pp.4–7；静态建模、动态 tile 观测和硬件反馈共同选择形状与数据流 | 含 SpMSpM 与其他稀疏组合；后续 tile/调度成本参考，没有据此新增行排序候选 |
| High Performance Unstructured SpMM Computation Using Tensor Cores（SMaT） | 2024 | §IV-C、§VI-A；相似性行置换减少原始 BCSR 非空块 | 旧表 P08；补读正文退化案例，保留与紧凑列空间目标的区别 |
| HiT | 2026 | 摘要、§IV 概述、§VII；HSparse/MSparse 外积与稠密内积数据流，定制交集/累加硬件 | 跨稀疏度和双操作数类型的架构参考；不直接替换当前行重排步骤 |
| HotTiles | 2024 | 摘要、§V、式 4–5，PDF p.7；依据时间、带宽和合并开销划分 hot/cold tile | 后续 AIC/AIV 分流参考；不把“每 tile 选较快设备”等同于全局最优分流 |
| Mosaic | 2025 | 摘要、iTex 与 tessellation 设计概述；异构指令拼接及调度 | 执行/编译层参考，非列集合聚类 |
| Optimizing Dynamic-Shape Neural Networks…（MikPoly） | 2024 | 摘要、两阶段框架概述；静态微内核加运行时组合及轻量成本模型 | 后端形状/调度参考，非行排序 |
| Parallel Scan on Ascend AI Accelerators | 2025 | 摘要、§3 与 scan 设计概述；Cube/Vector 实现 prefix sum 及其应用 | 后续前缀和、索引生成等基础算子参考；没有行聚类目标 |
| SLAWS | 2026 | §4.1–4.3，PDF pp.5–8；结构 bitmap 交集、采样块排序、按复用成本贪心融合行 | **新增 C7-I：迁移交集选行这一模块**；原对象是 SpMSpM，原数据流成本公式不直接照搬 |
| Spada | 2023 | 摘要、adaptive dataflow 概述；针对 SpGEMM 的窗口数据流与 profiling | 数据流选择参考；其“window”不是当前按列压缩的 row window 算法 |
| SpInfer | 2025 | 摘要、TCA-BME/SMBD 设计概述；低稀疏率权重的 bitmap 格式与共享存储解码 | 格式/解码层参考；未据其 GPU 成绩推导 NPU 收益 |
| Squeezing Operator Performance Potential for the Ascend Architecture | 2025 | 摘要、component-based roofline 概述 | 后续性能归因参考，不能替代设备证据 |
| TileSpMM | 2026 | §3.2、图 4，PDF pp.3–4；按局部列集合重叠在 64/16/8 行粒度间选择 | **保留为下一层窗口划分重点**；可与前置行重排组合，当前不把多高度结果混入固定 W16 主比较 |
| Trapezoid | 2024 | 摘要、§III 概述；多稀疏度内积/Gustavson 数据流与存储层次 | 定制架构参考，没有抽出当前可直接比较的行排序算法 |
| Vectorization of Narrow Matrix Multiplication… | 2025 | 摘要、§III–IV 概述；窄 MatMul 使用 AIV 并与 AIC 重叠 | 执行分工参考，非行列聚类 |

这 22 项里，SLAWS 提供了可以拆出的选行模块，TileSpMM 则直接帮助思考后续窗口划分。其余论文仍保留在相关层的资料中；不能因为大多数不是新的行重排算法就省略筛查记录，也不为凑 2026 年数量把它们全部列成重排候选。

## 4. 需要具体吸收的内容

### 4.1 TileSpMM：列重叠决定是否扩大窗口

对一个待合并区域，令 N 为整个区域的非空列并集大小，S 为其子窗口非空列数之和，以 S/N 衡量跨子窗口列共享。实际设计先看 64 行区域的 S16/N64，未满足条件再看 16 行区域的 S8/N16，否则回退 8 行。阈值由结合矩阵结构特征与实测性能的模型选择，而不是论文给出一个普遍有效的固定密度阈值。[作者全文 §3.2](https://www.ssslab.cn/assets/papers/2026-zeng-TileSpMM.pdf)

它不重新挑选任意行成员，而是扫描已有行序、形成不同高度的连续区域，再用 row map 写回结果。与本项目的关系是：前置行重排可以让相邻区域共享更多列，后续划分再决定是否合并。这是两个可以组合研究的步骤。GPU 的 8/16/64 不能直接成为 NPU 的设备配置；当前统一 W16 是隔离第一层变量的评价条件，不是排除后续可变窗口研究。

### 4.2 SLAWS：交集候选发现与组收益分开

SLAWS 面向稀疏×稀疏。其 Structure-Profiling 将行支持转成 bitmap，删除整个选区都为空的列，再用交集计数建立行对 score table；Block-Reordering 采样比较块之间重叠并贪心构造执行顺序。局部 Pass-Generation 挑选重叠较多的行，再比较融合后的 OutP 成本与分开执行的成本。它不是只有调度硬件，也确实包含结构组织步骤。（PDF pp.5–8、§4.1–4.3。）

可迁移的是“重叠计数选候选，再检查整个组”的模块组织。原成本含稀疏 B 的输出估计、两种数据流及专用硬件，不能原样带入稀疏×稠密 NPU。新增 C7-I 因而只借用交集选行：沿用 C4 的输入、候选池和容量，把评分替换成候选行与当前列并集的交集大小，最后仍按真实 U/T 评价。它是 **SLAWS 启发的项目适配**，不是 SLAWS 原算法复现。具体规则见 [C7 规格](../candidates.md#11-c7slaws-启发的交集收益贪心)。

SLAWS 用多行高阶交集的统计近似来减少硬件代价；本项目结构比较可以维护精确并集。原文的“高阶交集少”不能未经检验就套在行聚类后的高共享窗口上。

### 4.3 Groot 全文补证与 SMaT 退化案例

Groot 全文现已取得。论文 §4 明确把 Jaccard 换成 Hamming，目标是减小连续行差异，再用 kNN 图与树遍历近似。C1-H 与论文度量一致；当前 C1 使用 Python 更新版的 PyNNDescent，仍需标明与论文 KGraph 的实现区别，不能把度量相同写成完整复现。原文对近邻构建效率的经验/引用结果，也不应写成本项目所有矩阵的复杂度保证。

SMaT §VI-A 报告已有良好结构的矩阵会因 Jaccard 重排增加 BCSR 块数。这支持保留原序对照和逐矩阵退化记录；原文的原始 BCSR 块统计仍需转换到本项目紧凑列空间评价，不能混用。

### 4.4 Swift 与 AsyncSparse 的补充位置

误挂在 BlockSmith 下的 Swift 实际按列 NNZ 排序，在 CSC 上构造规则/不规则工作块，并处理输出局部归约。它不是 BlockSmith 的在线行聚类；这一身份错误若不核对首页，会直接把两个算法混为一谈。对本项目主要是另一种存储/执行组织参考。

AsyncSparse（2026，本地全文）分析 WCSR/BCSR 与异步 GPU 特性的配合，包含大窗口任务拆分。WCSR 中 B 仍要间接 gather，不能把 A 的异步连续搬运收益自动套给 B。它主要补充后续供数、负载均衡与执行层，不作为本轮新增行重排算法。

## 5. 更新后的比较范围

| 类别 | 明确保留什么 | 与旧表的关系 |
|---|---|---|
| 原序/历史控制 | B0、B1，以及 Cora 包内简化 Rabbit/Neutron 的历史记录 | 保持历史身份；不替代论文方法 |
| **RSH 参考重排** | **B-RSH-ref**：加权 Jaccard、候选倒排、kNN、树序、2-opt、孤立行回插 | 新增独立参考项；参数缺口与 MST 权重方向须记录 |
| **Neutron 参考重排** | **B-Neutron-ref**：真实 Rabbit 二部图粗聚类、当前窗口代表行 anchors、cluster 内 Jaccard 重建 | 新增独立参考项；原生 M128 与统一评价 W16 分开标记，cluster/anchor 未说明的细节不能隐瞒 |
| 原有项目候选 | C1-J/H、C2-LSH、C3-W1/W4、C4-U/T、C5-Rabbit | 五类八配置继续保留；C5 明确称 Neutron–Rabbit 思路的有界适配 |
| **近期模块适配** | **C7-I**：SLAWS 启发的精确交集收益选行 | 新增一个配置，与 C4 只改评分，不全面交叉组合 |
| 补充组合目标 | C6-HP | 继续保留；优化列并集与对齐 Tile 数的差别仍在 |
| 后续窗口层 | TileSpMM 式重叠驱动合并/划分 | 单独列入下一层问题，不伪装成已经输出行排列的算法 |
| 后续窗口内构造 | AFH-SpMM（F-AFH） | 全文已补读；不重新选择行成员，参考其块构造与剩余路径成本判断 |

RSH 的 2-opt 如果仅交换同一固定窗口内部的行，不会改变该窗 U/T；它仍是参考流程的一部分，但不能单独解释本项目结构收益。孤立行跨窗口回插则可能改变成员和指标。Neutron 原论文同时置换行列，列置换对固定行组的并集基数不变，但可能改变粗聚类结果、连续段与 B 局部性，因此需保存两种映射。

## 6. 继续独立检索的记录与限制

没有把检索限制在截图或用户的几个关键词。沿 ICPP 2026 官方程序又发现 **RODIS**、**CoTC-SpMM**；当前 primary 证据只足以确认论文和作者，尚不足以确认它们有没有可抽出的行聚类算法，故列为待正文探索，不根据第三方摘要定稿。[ICPP 官方程序](https://icpp2026.github.io/schedule/)

另找到 SC 2025 的 *Improving SpGEMM Performance Through Matrix Reordering and Cluster-wise Computation*，作者材料区分行排序与 cluster-wise 计算，可补充组合评价的思路；它面向 SpGEMM，不能据整体性能结论直接证明本项目的紧凑窗口收益。[作者仓库](https://github.com/PASSIONLab/reordering-spgemm)、[预印本](https://arxiv.org/abs/2507.21253)

初次核查时，AFH的ACM正文/摘要/PDF入口未取得可用正文，BlockSmith的Zotero附件错配；这些历史获取限制没有用于伪造算法细节。用户后续已提供两篇匹配全文并补读；现有来源、适用层次和实现细节缺口以最新补读为准。

本轮资料增加后，文献目录记录 **50项**，其中**16项2026工作**。后续补读AFH/BlockSmith不重复增加目录项；RODIS、CoTC仍只有近期题名线索。数量代表登记范围，不代表全部精读、全部候选或检索穷尽。详细索引见 [更新文献表](../literature.md)，初次检索及身份核验见 [audit.md](audit.md)，新全文来源见最新补读。
