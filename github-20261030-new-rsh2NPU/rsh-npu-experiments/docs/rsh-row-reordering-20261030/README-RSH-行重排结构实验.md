# RSH 行重排结构实验

这是一套独立于 NPU Kernel 的第一层实验工具。它只研究行/列重排怎样改变稀疏矩阵的局部结构，不接入 RS-tile、Bitmap、Gather、ND2NZ、AIV/AIC 或 Cube。

## 运行

不提供输入矩阵时，程序生成一个确定性的合成矩阵，便于先检查完整流程：

```powershell
python rsh_reorder_experiment.py --output-dir rsh-reorder-results
```

输入矩阵支持：

- Matrix Market 坐标格式：`.mtx` 或 `.mtx.gz`
- `--input` 可以重复传入多个矩阵；批量运行时每个矩阵有独立子目录，根目录同时生成方法 × 矩阵汇总表和图表
- JSON：`{"n_cols": ..., "rows": [[0, 3], ...]}`；也支持 `{"columns": [...], "values": [...]}` 行对象
- CSV 边表：每行 `row,column[,value]`，采用从 0 开始的编号
- CSR `.npz`：`indptr`、`indices`，可选 `data`、`shape`

例如：

```powershell
python rsh_reorder_experiment.py `
  --input data/your_matrix.mtx `
  --output-dir results/your_matrix `
  --w16 16 `
  --rsh-k 8 `
  --weighted-alpha 0 `
  --seed 0
```

所有算法参数在一次运行中固定，不能按矩阵单独调节。`weighted-alpha=0` 使用普通支持集 Jaccard；大于 0 时使用列频率加权 Jaccard。

## 对照方法和视图

程序生成四种行顺序：

1. `original`：原始行顺序；
2. `rsh`：非零列支持集 → 倒排候选 → 固定 k 的无向图 → 最大生成树 DFS → 有界局部 2-opt；
3. `rabbit`：二部图上的确定性度优先交替遍历，用作 Rabbit Order 的结构化简化基线；
4. `neutron`：先用二部图粗粒度顺序形成约 `8 × W16` 行的 cluster，再在 cluster 内用 anchor-Jaccard 形成 W16 行窗口。

每种方法同时保存两个视图：

- `row_only`：只使用行顺序，保留原始列编号，是主要公平比较；
- `native`：允许该方法使用自己的列顺序，是补充参考。

Rabbit 和 Neutron 的实现是可重复的结构化简化版本，输出中的 `method_config.simplification` 会明确记录这一点；结果不能直接解释为两篇论文的完整复现。

## 输出

输出目录中包含：

- 每个矩阵、方法、视图一个 JSON 文件，字段包括 `row_perm`、`inverse_row_perm`、`optional_col_perm`、`method_config`、`adjacency_metrics`、`W16_window_metrics`、`preprocessing_time_seconds`、`graph_statistics` 和 `correctness`；
- `method_metrics.csv`：方法 × 视图的聚合结构指标；
- `window_metrics.csv`：每个 W16 窗口的非零列并集、K16 数量、连续段和占用率；
- `row_order_structure_comparison.svg`：相邻行相似度对比；
- `W16_window_nonzero_union.svg`：窗口非零列并集对比；
- `continuous_run_distribution.svg`：连续列段数量对比；
- `manifest.json` 和 `experiment_result.json`：运行配置与完整结果。

窗口指标中的 `k16_count` 按固定的 K16=16 列分组计算，即 `ceil(unique_columns / 16)`；W16 只表示行窗口高度。两者仅用于结构观察。连续列段只记录为后续 ND2NZ 研究的观察项，当前 RSH 行重排没有把它作为优化目标。

## 验收测试

```powershell
python -m unittest -v test_rsh_reorder_experiment.py
```

测试检查四种方法的行置换双射、逆映射恢复、NNZ/值/列编号保持、native 行列置换语义、固定参数确定性、W16/K16 指标和结果文件生成。

## 与下一层的边界

本实验完成后，可以固定一个行顺序进入：

```text
固定行顺序
→ NPU 细粒度行划分
→ NPU Row Window / 逻辑 Tile
```

本工具不会根据结构指标直接得出 Bitmap、Gather、ND2NZ 或 Cube 性能结论。连续列段特征也留到后续实验，在固定细粒度行划分后作为 RSH 候选特征的单独变量比较。
