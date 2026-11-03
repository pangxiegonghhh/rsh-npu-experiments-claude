# RSH 行重排结构实验与分层研究背景

本目录归档 2026-10-30 经用户审核的实验背景、第一层实验草稿及配套原型。

从[实验文档索引](实验文档索引.md)开始阅读；运行方法见[程序说明](README-RSH-行重排结构实验.md)。

当前实现包含原始顺序、RSH 思路的简化实现、Rabbit 风格及 Neutron 风格启发式对照。公开数据集多矩阵实验与论文算法忠实复现仍未完成。`rsh-reorder-results/` 是早期合成输入验证记录，不是修订版代码的重新运行结果，也不是 NPU 性能结果。

本目录是一条独立的结构实验研究线，不改动仓库中 E0—E6 的冻结输入、续跑指针和封存证据。

在本目录运行：

```sh
python3 -m unittest -v test_rsh_reorder_experiment.py
python3 rsh_reorder_experiment.py --output-dir new-synthetic-results
```

公开数据集先核验来源、维度、对称展开和 NNZ，再执行结构评价；数据下载说明见[NEUTRON-DATASET-README.md](NEUTRON-DATASET-README.md)。
