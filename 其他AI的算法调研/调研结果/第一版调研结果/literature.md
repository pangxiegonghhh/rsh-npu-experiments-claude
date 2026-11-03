# 文献与来源核验

初版核验日期：2026-10-30；补充核验：2026-10-31。共登记 50 项：原 25 项、新增 23 项筛读/方法参考、另 2 项近期题名线索。按表中年份有 16 项 2026 工作，不代表均已取得算法全文。表中“正文”指实际核对了与本问题有关的章节，不表示逐页精读整篇论文；“代码”指阅读作者实现，不表示本轮已运行复现。仅取得摘要或材料的工作不作为忠实实现的充分依据。截图逐项判断见 [补充报告](update-20261031/report.md)。

**最新来源更新：**AFH、BlockSmith 已由用户提供匹配正式全文，相关章节已补读，见 [全文核对](fulltext-afh-blocksmith-20261031/report.md) 与 [文件身份清单](fulltext-afh-blocksmith-20261031/sources.json)。不新增重复文献项，目录仍为50项。

## 1. 文献范围

| ID | 工作与年份 | 原目标或机制 | 本轮证据范围 | 本次用途 |
|---|---|---|---|---|
| P01 | [RSH-SpMM: A Row-Structured Hybrid Kernel for Sparse Matrix-Matrix Multiplication on GPUs](https://arxiv.org/abs/2603.08734)，2026 | 加权支持集相似性、kNN、树遍历、局部调整及混合执行 | 原文 §3.4、算法 3 | 现有主线和基线；辨明行序代理目标 |
| P02 | [TC-GNN: Bridging Sparse GNN Computation and Dense Tensor Cores on GPUs](https://www.usenix.org/conference/atc23/presentation/wang-yuke)，ATC 2023 | 行窗口内排序、去重、空列压缩与原列映射 | 作者论文算法 1，亦见 [PDF](https://par.nsf.gov/servlets/purl/10467860) | 明确列压缩口径；无新增重排控制 |
| P03 | [DTC-SpMM: Bridging the Gap in Accelerating General Sparse Matrix Multiplication with Tensor Cores](https://doi.org/10.1145/3620666.3651378)，ASPLOS 2024 | TCU-aware 行聚类、cache-aware 聚类间组织 | 原文 §4.3、算法 1，作者 TCA 代码 | C2 的来源 |
| P04 | [A novel data transformation and execution strategy for accelerating sparse matrix multiplication on GPUs](https://doi.org/10.1145/3332466.3374546)，PPoPP 2020 | LSH 加速层次行聚类，改善 SpMM/SDDMM 局部性 | [会议公开摘要](https://sigplan.github.io/OpenTOC/ppopp20.html)、[作者机构元数据](https://augusta.elsevierpure.com/en/publications/a-novel-data-transformation-and-execution-strategy-for-accelerati/)；未取得全文 | LSH 聚类前驱；不直接承诺完整复现 |
| P05 | [BlockSmith: Ultra-dense Block Transformation for Efficient Sparse Matrix Multiplication Using Tensor Cores](https://doi.org/10.1145/3828547)，TACO 23(3), 87，2026 | 特征宽度、限容量在线聚类、短组后处理与列压缩 | 用户提供的24页正式全文：§2.2、§4、算法1、§6.3/6.5/6.6、§8；作者关键代码 | C3、C3-A补充宽度策略及后处理消融；论文/代码边界明记 |
| P06 | [Groot: Graph-Centric Row Reordering with Tree for Sparse Matrix Multiplications on Tensor Cores](https://doi.org/10.1145/3689031.3717460)，EuroSys 2025 | 稀疏近邻图、MST、遍历生成行序 | 作者 C++/Python；10 月 31 日新增本地全文 §4、算法 3–7 | C1；论文 Hamming/KGraph 与后来代码变体分开 |
| P07 | [HC-SpMM: Accelerating Sparse Matrix-Matrix Multiplication for Graphs with Hybrid GPU Cores](https://arxiv.org/abs/2412.08902)，2024 预印本 | 混合执行及 LOA 窗口贪心密度优化 | 原文 §V-B、算法 5–6、式 5–6 | C4 的直接依据 |
| P08 | [High Performance Unstructured SpMM Computation Using Tensor Cores](https://doi.org/10.1109/SC41406.2024.00060)，SC 2024，SMaT | BCSR、行重排减少块数 | [原文 §IV-C、§VI-A](https://arxiv.org/html/2408.11551v1)、[作者出版记录](https://spcl.inf.ethz.ch/Publications/index.php?pub=532) | 1-SA 聚类思路与原始列块口径对照 |
| P09 | [Blocking Sparse Matrices to Leverage Dense-Specific Multiplication](https://doi.org/10.1109/IA356718.2022.00009)，IA3 2022，1-SA | 按结构相似性聚类，支持稠密块计算 | [作者机构记录](https://www.research.unipd.it/handle/11577/3470280)；机制部分仅取得 SMaT 的引用描述，原文受限 | 相关前驱；暂不单列忠实复现候选 |
| P10 | [Accelerated Block-Sparsity-Aware Matrix Reordering for Leveraging Tensor Cores in Sparse Matrix-Multivector Multiplication](https://doi.org/10.1007/978-3-031-69583-4_1)，Euro-Par 2024，BSA | 面向块稀疏结构的行特征和聚类 | [作者出版页](https://mlsys.sogang.ac.kr/publications)、[官方 artifact 说明](https://zenodo.org/records/11579181/files/BSA-SpMM_EURO_PAR_2024_Overview.pdf)；全文未获取 | 特征设计补充；详细公式不据二手材料定稿 |
| P11 | [Rabbit Order: Just-in-Time Parallel Reordering for Fast Graph Analysis](https://doi.org/10.1109/IPDPS.2016.110)，IPDPS 2016 | 层次社区与并行增量聚合 | [作者实现与使用协议](https://github.com/araij/rabbit_order)，Neutron 对其使用的原文 | C5 粗阶段；替换二部图遍历简化基线 |
| P12 | [Acc-SpMM: Accelerating General-purpose Sparse Matrix-Matrix Multiplication with GPU Tensor Cores](https://arxiv.org/abs/2501.09251)，PPoPP 2025 | 模块度聚合成 dendrogram，再按数据亲和关系生成顺序 | 原文 §3.2、算法 1 | 粗组织替代路线，暂缓以控制首轮规模 |
| P13 | [Permuting Sparse Rectangular Matrices into Block-Diagonal Form](https://doi.org/10.1137/S1064827502401953)，SISC 2004 | 二部图与超图模型进行矩阵重排 | 出版方摘要；全文未读 | 表明矩形矩阵可用独立行列模型，避免仅限邻接方阵 |
| P14 | [On partitioning and reordering problems in a hierarchically parallel hybrid linear solver](https://portal.nersc.gov/project/sparse/xiaoye-web/ipdps13.pdf)，IPDPS 2013 | column-net、row-net 与 connectivity 等目标 | 原文模型定义和式 7–9 | C6 的建模依据；不是 SpMM 实测依据 |
| P15 | [High-Quality Hypergraph Partitioning](https://arxiv.org/abs/2106.08696)，2021 预印本，KaHyPar | 多层超图划分，优化 connectivity | 原文摘要与[作者工具文档](https://kahypar.org/)的目标、容量限制及接口 | C6 工具路线与限制 |
| P16 | [Efficient K-Nearest Neighbor Graph Construction for Generic Similarity Measures](https://www.cs.princeton.edu/cass/papers/www11.pdf)，WWW 2011，NN-Descent | 用局部邻居传播构造近似 kNN | 作者原文摘要及算法动机 | C1 的可扩展候选构造依据 |
| P17 | [FlashSparse: Minimizing Computation Redundancy for Fast Sparse Matrix Multiplications on Tensor Cores](https://arxiv.org/abs/2412.11007)，PPoPP 2025 | Swap-and-transpose 缩小稀疏计算粒度 | [会议摘要](https://sigplan.org/OpenTOC/ppopp25.html)、预印本记录；本轮不复审 kernel | 后续逻辑 Tile 层，非本轮独立行序候选 |
| P18 | [cuTeSpMM: Accelerating Sparse-Dense Matrix Multiplication using GPU Tensor Cores](https://arxiv.org/abs/2504.06443)，2025 预印本 | HRPB、计算组织及 TCU-Synergy 分析 | 原文结构与相关设计说明 | 区分结构可用性和实际执行性能 |
| P19 | [Dense Dynamic Blocks: Optimizing SpMM for Processors with Vector and Matrix Units Using Machine Learning Techniques](https://research.ibm.com/publications/dense-dynamic-blocks-optimizing-spmm-for-processors-with-vector-and-matrix-units-using-machine-learning-techniques)，ICS 2022 | DDB-MM/DDB-HYB 与策略选择 | IBM 作者摘要、[作者 PDF](https://iacoma.cs.uiuc.edu/iacoma-papers/ics22_2.pdf)相关背景 | 跨平台矩阵单元/向量混合路线；后续层参考 |
| P20 | [Block-structured matrix reordering for efficient SDDMM on tensor cores](https://doi.org/10.1007/s11227-026-08606-2)，Journal of Supercomputing，2026 | 双向重排与稠密/稀疏块处理 | 出版方可检索正文的 row reordering、开销段；作者出版页 | 邻近 SDDMM 路线，不能直接用其结果证明 SpMM |
| P21 | [Can Graph Reordering Speed Up Graph Neural Network Training? An Experimental Study](https://www.vldb.org/pvldb/vol18/p293-merkel.pdf)，PVLDB 18(2)，2025；2024 预印本 | 多种图重排、开销与 GNN 条件比较 | 原文摘要、实验范围与[作者仓库](https://github.com/nikolaimerkel/reordering)说明 | 评价需跨矩阵、记录超参数和摊销 |
| P22 | [Community-based Matrix Reordering for Sparse Linear Algebra Optimization](https://bvignesh.github.io/papers/ISPASS_2023_CommunityBasedReordering.pdf)，ISPASS 2023，Rabbit++ | 分析社区重排失效条件并改进 Rabbit | 作者原文引言、社区偏斜分析说明 | 粗聚类的风险与扩展方向 |
| P23 | [Accelerating GNNs on GPU Sparse Tensor Cores through N:M Sparsity-Oriented Graph Reordering](https://doi.org/10.1145/3710848.3710881)，PPoPP 2025 | 无损重排满足 V:N:M 结构 | 出版方摘要 | 结构化稀疏目标对照；不照搬硬件约束 |
| P24 | [Fused3S: Fast Sparse Attention on Tensor Cores](https://hpcrl.github.io/ICS2025-webpage/program/Proceedings_ICS25/ics25-70.pdf)，ICS 2025 | 稀疏注意力融合、窗口调度重排 | 作者/会议 PDF 的 row-window reordering 段 | 窗口执行顺序与成员重组的区别 |
| P25 | [NeutronSparse: Coordinating Heterogeneous Engines for Sparse Matrix Multiplication on NPUs](https://arxiv.org/abs/2606.22482)，2026 | Rabbit 粗重排与局部 anchor-Jaccard，配合 NPU Tile 组织 | 原文 §6.1、本地原始 TeX | C5；核实已有算法的整合位置 |

## 2. 核心方法的阅读结论

### P03：DTC-SpMM

Jaccard 在原始列支持集上计算；LSH 用于产生待比较的行对，优先队列控制合并顺序。第一层针对 TC 块密度，第二层针对多个窗口的缓存局部性。两层不应合并成一个无法解释收益来源的开关。作者源码先合并、再根据聚类大小冻结，因此加入严格容量限制属于适配改动。[原文](https://home.cse.ust.hk/~weiwa/papers/dtc-spmm-asplos24.pdf)、[作者源码](https://github.com/HPMLL/DTC-SpMM_ASPLOS24/blob/66eca266bde1f3faf5f8ef7a054db2391b50e27d/reordering/TCA_reorder.py)

### P05：BlockSmith

论文把特征宽度选择、聚类容量与后处理放在同一预处理框架。用户提供的完整PDF已补读：式3按D=max(rows,cols)选择4/32/128；算法1是固定首行代表、按组大小优先的首次匹配逐行分配，并非迭代重分配直至收敛。论文阈值J>0.2，代码距离≤0.8对应J≥0.2；相等边界不同。当前工具在行数超过200000时返回跳过，自动宽度按rows决定。§4.3文字后处理与代码细则、项目共用P也有区别。§6.3强调预处理仍需摊销，§6.6表明内核优化可独立贡献收益；不能把整体加速全归于重排。工具记录的部分CUDA kernel时间不能直接用作完整预处理时间。[脚本](https://github.com/CGCL-codes/BlockSmith/blob/bf7348d0ba64b7b1eee8ac014a0ca4162b1d7717/scripts/run_preprocess.py)、[入口代码](https://github.com/CGCL-codes/BlockSmith/blob/bf7348d0ba64b7b1eee8ac014a0ca4162b1d7717/preprocess/tools/preprocess_main_cuda.cpp)、[最新全文补读](fulltext-afh-blocksmith-20261031/report.md)

### P06：Groot

作者 C++ 版本的距离为两个非零列集合的对称差大小，即二值结构 Hamming 距离；使用 KGraph 发现近邻，再生成树并 DFS。Python 更新版使用 PyNNDescent，可选 Jaccard/Hamming。README 提供 Cora 示例块数，但本轮不把作者的 Cora 当成用户提供的 Cora：同名输入仍需哈希及预处理身份一致。[C++ 距离与树](https://github.com/yuang-chen/Groot-EuroSys25/blob/a591f4152ca0d30d9e75002aa0542dbd4139edd2/groot/transforms/knn.h)、[Python](https://github.com/yuang-chen/Groot-EuroSys25/blob/a591f4152ca0d30d9e75002aa0542dbd4139edd2/groot.py)

### P07：HC-SpMM LOA

式 5 的密度目标是窗口非零元数除以非零列数。算法 5–6 从按最小邻居 ID 排序的序列取种子，限制候选搜索范围，并按密度最大、再按度数的规则扩展窗口；还利用倒排关系增量计算交集。对一般矩形稀疏矩阵，需使用真正的列到行倒排索引，不能把图邻居的写法直接当作对称矩阵假设。[§V-B](https://arxiv.org/html/2412.08902v1#S5.SS2)

### P01：RSH

原文把相似性写为按列频率加权的 Jaccard，并把优化目标写为沿排列累计不相似度。算法 3 对树边写 sim，而后写 minimum spanning tree；正文目标与这处伪代码存在方向歧义。适配时明确采用 distance=1-sim 的最小生成森林，等价于 sim 最大生成森林；把这一选择与现有简化原型的其他工程选择分别记录。[§3.4](https://arxiv.org/html/2603.08734v1#S3.SS4)

### P25 + P11：Neutron 使用 Rabbit 的位置

Neutron 原文 §6.1 明确使用二部图和 Rabbit 的粗阶段，再在每个 cluster 内以 anchor-Jaccard 重建窗口。P02 提供 SGT 的历史背景，P11 提供粗阶段算法，P25 说明两阶段在 NPU 流程中的组合。Rabbit 原算法具有层次社区和并行增量聚合，普通二部图遍历不等价于其实现。[Neutron 原文](https://arxiv.org/html/2606.22482v1#S6.SS1)、[Rabbit 作者仓库](https://github.com/araij/rabbit_order)

## 3. 作者代码快照

| 仓库 | 本轮读取的固定 ref | 核对文件 |
|---|---|---|
| CGCL-codes/BlockSmith | `bf7348d0ba64b7b1eee8ac014a0ca4162b1d7717` | matrix_reorder_cuda.cu、matrix_reorder.cpp、matrix_condense.cpp、preprocess_main_cuda.cpp、run_preprocess.py |
| yuang-chen/Groot-EuroSys25 | `a591f4152ca0d30d9e75002aa0542dbd4139edd2` | README、groot.py、knn.h、reorder.h |
| HPMLL/DTC-SpMM_ASPLOS24 | `66eca266bde1f3faf5f8ef7a054db2391b50e27d` | reordering/TCA_reorder.py |
| araij/rabbit_order | `f93776e9c1e1d4a8962ee56bc7ff0091e6fe12dd` | README、license.txt、demo/reorder.cc、rabbit_order.hpp 的聚合/顺序接口 |

已保存的代码文本是阅读证据，见 [sources/manifest.json](sources/manifest.json)；本轮未编译或执行。Neutron 原文 TeX 的本地来源见 `docs/neutron-operand-path-20261028/sources/arxiv-v1/extracted/sec4-2.tex`。

Rabbit 作者仓库采用 evaluation license。后续内部评估应保留其作为原样外部依赖，不默认可修改或随项目再分发。其 demo 会对输入边自动对称化；二部图坐标边只提交一次，避免重复加权。[作者许可](https://github.com/araij/rabbit_order/blob/f93776e9c1e1d4a8962ee56bc7ff0091e6fe12dd/license.txt)、[图装载及排列接口](https://github.com/araij/rabbit_order/blob/f93776e9c1e1d4a8962ee56bc7ff0091e6fe12dd/demo/reorder.cc)

## 4. 需要保留的来源限制

- 10 月 30 日 Groot 全文入口受限；10 月 31 日已由 Zotero 本地全文补证。1-SA、BSA 原始全文仍未取得，后两项仅作补充。
- BlockSmith正文直连一度403，初期依赖出版方索引及作者代码。此后用户提供了匹配完整PDF，已补读并单独记录来源哈希；历史索引读取不冒称当时已回收全文。
- 本轮六源脚本没有有效 API 结果，不能提供可靠引用量排名；不以引用量代替与本问题的相关性。
- 未采用搜索结果中自动生成的论文解读作为关键算法依据。题名相同的预印本与正式版不重复计数。
- 10月31日最初核对发现Zotero的BlockSmith条目附件实际为Swift；Swift单列P47。用户后续提供的BlockSmith完整PDF匹配题名/作者/DOI，P05已用新文件补证，旧错配附件及原库不改。RSH/Neutron条目正式DOI与本地v1附件版本仍分开记录，不能将v1自动标成正式出版稿。

## 5. 2026-10-31 新增文献索引

本地匹配全文筛读了摘要和设计概述，优先相关算法进一步核对正文。各项 PDF 路径、SHA-256、提取文本和条目年份见 [zotero-corpus.json](update-20261031/zotero-corpus.json)；原附件未拷贝或改写。该清单是索引，不能按条目总数宣称全部精读。

| ID | 工作与年份、来源 | 本轮证据与本项目用途 |
|---|---|---|
| P26 | [TileSpMM: A Variable-Size Tiled Algorithm for Sparse Matrix-Matrix Multiplication on Tensor Cores](https://www.ssslab.cn/assets/papers/2026-zeng-TileSpMM.pdf)，ICPP 2026 | 本地及作者全文 §3.2、图 4；列重叠驱动的可变高度划分，后续窗口层重点 |
| P27 | [SLAWS: Spatial Locality Analysis and Workload Orchestration for Sparse Matrix Multiplication](https://doi.org/10.1145/3779212.3790222)，ASPLOS 2026 | 本地全文 §4.1–4.3；bitmap 交集、块排序、按复用成本融合行；C7-I 的模块来源，原对象 SpMSpM |
| P28 | [Harmonia: A Unified Hierarchical Scheduling Framework for Sparse Matrix Multiplication](https://doi.org/10.1109/ISCA66397.2026.00151)，ISCA 2026 | 本地全文 §III–IV；静态/动态分层 tiling 与数据流选择；后续调度层 |
| P29 | [AFH-SpMM: Auto-Fit Heterogeneous Block Sparse-Dense Matrix Multiplication on Tensor Core GPUs](https://doi.org/10.1145/3832810.3832843)，ICPP 2026 | 用户提供的11页正式全文已补读§3.2–3.4、图1–3、算法1与§4.3–4.4；固定16行内选列和Dense/Row24路由，定位F-AFH后续层，不另起行排序候选 |
| P30 | [HiT: A Unified Sparsity-Adaptive Architecture for High-Throughput Matrix Multiplication](https://doi.org/10.1109/ISCA66397.2026.00187)，ISCA 2026 | 本地全文摘要、§IV 概述与 §VII；多稀疏度定制架构及预处理计时边界 |
| P31 | [Adaptive Matrix Multiplication for Dynamic Shapes on Ascend NPUs](https://arxiv.org/abs/2608.10803)，2026 预印本，AdaptCore | 本地全文；稠密 MatMul 的形状/tiling/指令模型，后端参考 |
| P32 | [ENEC: A Lossless AI Model Compression Method Enabling Fast Inference on Ascend NPUs](https://doi.org/10.1109/ISCA66397.2026.00100)，ISCA 2026 | 本地全文；权重无损编码、bit packing、scan；压缩/解码层 |
| P33 | [FuseFlow: A Fusion-Centric Compilation Framework for Sparse Deep Learning on Streaming Dataflow](https://doi.org/10.1145/3779212.3790165)，ASPLOS 2026 | 本地全文；跨表达式融合、阻塞/数据流配置；后续编译层 |
| P34 | [GeneralSparse: Bridging the Gap in SpMM for Pruned Large Language Model Inference on GPUs](https://www.usenix.org/conference/atc25/presentation/wang-yaoyu)，ATC 2025 | 本地全文 §3.1–3.2；row/split 分配空间与 reduction；供给/调度层 |
| P35 | [HotTiles: Accelerating SpMM with Heterogeneous Accelerator Architectures](https://doi.org/10.1109/HPCA57654.2024.00081)，HPCA 2024 | 本地全文 §V、式 4–5；hot/cold tile 的全局成本分配，后续分流参考 |
| P36 | [A Probabilistic Perspective on Tiling Sparse Tensor Algebra](https://doi.org/10.1145/3725843.3756095)，MICRO 2025，D2T2 | 本地全文；统计/概率模型预测访存与 tile 搜索；后续模型参考 |
| P37 | [SpInfer: Leveraging Low-Level Sparsity for Efficient Large Language Model Inference on GPUs](https://doi.org/10.1145/3689031.3717481)，EuroSys 2025 | 本地全文；TCA-BME、SMBD、pipeline；存储与解码层 |
| P38 | [Squeezing Operator Performance Potential for the Ascend Architecture](https://doi.org/10.1145/3676641.3716243)，ASPLOS 2025 | 本地全文；component-based roofline，后续性能归因 |
| P39 | [Vectorization of Narrow Matrix Multiplication for Ascend AI Inference Acceleration](https://doi.org/10.1109/CloudCom67567.2025.11331396)，CloudCom 2025 | 本地全文；窄 MatMul 的 AIV/AIC 分工，执行层参考 |
| P40 | [Parallel Scan on Ascend AI Accelerators](https://doi.org/10.1109/IPDPSW66978.2025.00216)，IPDPSW 2025 | 本地全文；Cube/Vector scan，索引/前缀和基础算子参考 |
| P41 | [Optimizing Dynamic-Shape Neural Networks on Accelerators via On-the-Fly Micro-Kernel Polymerization](https://doi.org/10.1145/3620665.3640390)，ASPLOS 2024，MikPoly | 本地全文；微内核运行时组合与成本模型，后端参考 |
| P42 | [Mosaic: Exploiting Instruction-Level Parallelism on Deep Learning Accelerators with iTex Tessellation](https://doi.org/10.1145/3676641.3716262)，ASPLOS 2025 | 本地全文；iTex 拼接及异构指令编排，执行/编译层 |
| P43 | [Spada: Accelerating Sparse Matrix Multiplication with Adaptive Dataflow](https://doi.org/10.1145/3575693.3575706)，ASPLOS 2023 | 本地全文；SpGEMM 的窗口自适应数据流，非当前 row-window 成员聚类 |
| P44 | [Trapezoid: A Versatile Accelerator for Dense and Sparse Matrix Multiplications](https://doi.org/10.1109/ISCA59077.2024.00072)，ISCA 2024 | 本地全文；跨稀疏度架构/数据流，后续架构参考 |
| P45 | [AsyncSparse: Accelerating Sparse Matrix-Matrix Multiplication on Asynchronous GPU Architectures](https://arxiv.org/abs/2604.17834)，2026 预印本 | 本地全文；BCSR/WCSR、TMA、WGMMA、任务拆分；供给与执行层 |
| P46 | [Segmented Operations using Matrix Multiplications](https://arxiv.org/abs/2506.23906)，2025 预印本，本地 v2 | 本地全文；MMV-RAM、segmented scan/sum 与 Ascend 案例；基础算子/理论参考 |
| P47 | Swift: High-Performance Sparse-Dense Matrix Multiplication on GPUs，HPCA 2026 | 本地 PDF 首页核实，文件误挂于 BlockSmith 条目；按列 NNZ 排序、CSC 工作块与局部归约；存储/执行参考，不视为 BlockSmith |
| P48 | [Improving SpGEMM Performance Through Matrix Reordering and Cluster-wise Computation](https://arxiv.org/abs/2507.21253)，SC 2025 | 作者预印本摘要、[作者仓库](https://github.com/PASSIONLab/reordering-spgemm)；区分排序与 cluster-wise 计算的评价思路；未据此定稿新算法 |
| P49 | [RODIS: Accelerating Sparse Matrix Multiplication on GPU via Row-Orchestration and Dynamic Instruction Scheduling](https://icpp2026.github.io/schedule/)，ICPP 2026 | 独立检索沿官方会程发现；题名/作者核实，算法正文未取得，待探索 |
| P50 | [CoTC-SpMM: A Cooperative Tensor–CUDA Cores Scheme for Efficient Sparse Matrix Multiplication](https://icpp2026.github.io/schedule/)，ICPP 2026 | 独立检索沿官方会程发现；题名/作者核实，算法正文未取得，待探索 |
