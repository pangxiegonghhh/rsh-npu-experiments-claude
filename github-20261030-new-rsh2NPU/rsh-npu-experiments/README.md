# RSH-NPU：分层实验与行重排结构研究

分支：`codex/plan-rsh-row-reordering-20261030`  
更新日期：2026-10-30

本分支整理 **RSH 迁移到 NPU 的研究路线、逐层实验组织方式，以及第一层“RSH 行重排结构实验”的计划和原型**。材料集中在 [docs/rsh-row-reordering-20261030/](docs/rsh-row-reordering-20261030/)。

当前已归档背景文档、实验草稿、结构评价程序、数据集清单和早期合成输入记录。公开数据集的完整多矩阵实验尚未完成。

## 从这里开始

1. [主线与 ND2NZ 后续优化大纲（简版）](docs/rsh-row-reordering-20261030/RSH-NPU主线与ND2NZ后续优化大纲-简版.md)：说明主线和后续优化线。
2. [实验组织方式](docs/rsh-row-reordering-20261030/实验组织方式.md)：说明各层如何独立设计、验证和交接。
3. [RSH 行重排结构实验计划草稿](docs/rsh-row-reordering-20261030/RSH%20行重排结构实验计划草稿.md)：说明第一层的目标、已有实现、公开数据集补充和待办。
4. [实验文档索引](docs/rsh-row-reordering-20261030/实验文档索引.md)：查找配套代码和验证记录。

## 研究路线

```text
RSH 行重排
        ↓
面向 NPU 的细粒度行划分
        ↓
NPU Row Window / 逻辑 Tile
        ↓
类 RS-tile 存储层
        ↓
A/B 数据准备
        ↓
L0A/L0B
        ↓
Cube
```

每一层先完成自己的设计与实验，后一层使用前一层已经固定的输出。存储层先以 Bitmap 为主要格式验证；主流程的 B 取数先采用 Gather。主流程稳定后，再研究候选行特征与窗口列集合对 ND2NZ 的影响。

上述路线是本分支的研究组织方式，各层具体算法和参数仍按对应实验逐步确定。

## 当前第一层实验

[独立结构实验程序](docs/rsh-row-reordering-20261030/rsh_reorder_experiment.py)比较原始行顺序、RSH 思路的简化实现、Rabbit 风格启发式和 Neutron 风格 Global–Local 启发式。

- `row_only` 视图：只应用行顺序，保留原始列编号，作为主要比较。
- `native` 视图：允许方法同时使用其列顺序，作为补充参考。
- 统一评价相邻行 Jaccard、W16 非零列并集、K16 分组、连续列段、预处理时间和图规模。
- 检查行排列双射、逆映射恢复与矩阵语义保持，输出 JSON、CSV 和 SVG。

W16 在这一层是评价用的行分组；`k16_count = ceil(窗口非零列并集大小 / 16)` 是紧凑列空间的结构指标。它们还不是下一层已经确定的 NPU 窗口或 RS-tile 存储格式。

Rabbit 和 Neutron 当前是启发式对照，尚未证明与论文算法一致。本层结果也不能直接推出 Bitmap、Gather、ND2NZ 或 Cube 的性能结论。

## 验证与数据进展

| 项目 | 当前情况 |
| --- | --- |
| 当前原型测试 | 10 项单元测试通过，Python 编译检查通过 |
| 已归档合成输入记录 | 早期 `192 × 192`、2462 NNZ，4 种方法 × 2 个视图；不是修订版代码重新运行的结果 |
| Cora 先导实验 | 会话已报告实例运行成功，加载后为 `2708 × 2708`、10,556 NNZ；远端证据包尚未在本分支归档 |
| 其他公开矩阵 | 待完成下载、输入版本核验及多矩阵评价 |
| 规模与算法核验 | 较大矩阵的时间/内存、论文方法忠实性仍待验证 |

公开矩阵优先与 NeutronSparse 的数据集对齐。完整候选见[数据集清单](docs/rsh-row-reordering-20261030/neutron_dataset_manifest.csv)，第一轮候选包括 `cora、wiki-RfA、dawson5、olafu、pattern1、human_gene1`。清单不表示矩阵已经全部下载或实验完成；输入需核对来源、校验值、对称展开及实际 NNZ。

## 运行第一层原型

本层在 CPU 上运行，不需要 NPU/CANN。Python 3.11 可运行核心程序；读取 CSR NPZ 另需 NumPy。

从仓库根目录进入本分支的独立实验目录：

```sh
cd docs/rsh-row-reordering-20261030
python3 -m unittest -v test_rsh_reorder_experiment.py

# 使用合成输入检查流程，输出到新目录
python3 rsh_reorder_experiment.py --output-dir new-synthetic-results

# 使用已经下载并核验的公开矩阵
python3 rsh_reorder_experiment.py \
  --input /path/to/matrix.mtx \
  --output-dir results-real-matrix
```

详细输入格式与参数见[程序说明](docs/rsh-row-reordering-20261030/README-RSH-行重排结构实验.md)，数据获取方式见[数据说明](docs/rsh-row-reordering-20261030/NEUTRON-DATASET-README.md)。数据源可用性需要实际检查。

## 与仓库既有 E0—E6 材料的关系

本分支从 `main` 的 `0d01756bfe36e2d07b4a99f49143d648af48c44b` 建立。仓库原有 `rsh/`、`npu/`、`scripts/`、`inputs/` 和设备实验资料继续保留；本次归档没有改动这些实现、冻结输入或封存证据。

既有 [项目交接](docs/PROJECT_HANDOFF.md)、[E0—E6 续跑指针](docs/e0-e6-experiments/resume.md)和[实验台账](docs/e0-e6-experiments/experiment-status.md)保留其记录时点的状态，不应当作本分支结构实验的当前进度，也不能代替其他执行分支的最新设备证据。

后续可在固定第一层输出后进入细粒度行划分实验。仓库协作约定见 [AGENTS.md](AGENTS.md) 和[实验工作流程](docs/AGENT_WORKFLOW.md)。
