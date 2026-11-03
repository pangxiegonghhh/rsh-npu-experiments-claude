# Motivation 与 NeutronSparse 的差异

## 用户的担心

原 motivation 来自 RSH 对混合架构的批评：分区粒度粗，看不到行组内部和跨行组的细粒度结构。重读 NeutronSparse 后发现，它的 Two-Stage Row-Column Extraction 是按单行、单列判断，把稀疏行列分到 AIV，并不是把 A 粗暴切成稀疏、稠密两块。于是"NPU 上的混合方法粒度太粗"这个前提站不住。

## 讨论结论（用户已同意）

**用户说对的地方：** NeutronSparse 不是矩阵级切分，"粒度太粗"不能写进论文。

**RSH 的批评仍有一半适用。** RSH 批评 HC-SpMM 的原话是 "global sparsity statistics or simple per-row thresholds"，问题在于 ignore inter-row similarity, column-span overlap within windows。对照 NeutronSparse：

1. **判据只看行自身长度。** 规则是 Len(v) ≤ α·K（§5.2.2），一行进不进 AIC 与它会和哪些行同窗无关。RSH 的 Δ 判据看的是放进当前窗口后列并集增加多少。
2. **划分与成窗脱钩。** 先抽取，后做 Global/Local 重排；局部重排只在已分给 AIC 的行里按 Jaccard 拼 128 行窗口，划分不再调整。
3. **静态规则在 GNN 图上基本不起作用。** ogbn-arxiv：K=169,343，默认 α=2×10⁻³，阈值约 339，而 AvgL=13.6（Table 2），几乎所有行初始都进 AIV。最终 AIC 占多数靠运行时迁移（约 7 轮收敛，§8），迁移依据的是执行时间偏差和 tile 密度，也不看行与窗口的结构吻合。

## 改写后的 motivation

> NeutronSparse 的划分只依据每行自身长度，与成窗脱钩。在 NPU 上，AIC 代价由窗口压缩后的 K（列并集）决定，它同时决定 L0A/L0B 占用和 Gather 次数。一行该不该进 AIC，应看它对所在窗口列并集的增量。

这也能回应 NeutronSparse §6.1 的论点（细粒度重排不适合按大 tile 执行的 NPU）："判断粒度细"和"tile 小"是两回事，Δ 判据可以在 128 行窗口上算。

## 验证实验 G1（CPU，go/no-go）

- 流水线 A（复现 NeutronSparse）：行/列抽取 → Rabbit → anchor-Jaccard 拼 M128 窗口 → 列压缩。
- 流水线 B（上下文感知）：重排后顺序扫描，按 Δ 同时决定进窗口或进 AIV。**算法尚未设计，见 06 代办。**
- 固定 AIC 承担的 nnz 占比相同，比较 padding 体积 Σ(M×K_compact) − nnz、tile 数、Gather 行数。
- 判断线（经验值，可再定）：多数数据集上 B 比 A 少 20%～30% 以上则成立；不到 5% 则放弃。
- 风险：运行时迁移可能抵消部分静态差距，最终仍需端到端时间验证。
