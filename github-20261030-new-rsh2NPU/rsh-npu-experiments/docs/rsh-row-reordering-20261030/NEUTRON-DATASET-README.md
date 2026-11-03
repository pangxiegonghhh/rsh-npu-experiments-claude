# NeutronSparse 数据集上传说明

NeutronSparse 论文的实验集包含 4 个 GNN 数据集和 16 个 SuiteSparse 矩阵。完整名单、维度、NNZ、平均行长度、密度、偏斜度和空 16×16 tile 比例见 `neutron_dataset_manifest.csv`。

本研究的第一轮 RSH 行重排结构实验建议使用 `small` 预设：

```text
cora, wiki-RfA, dawson5, olafu, pattern1, human_gene1
```

这组数据覆盖小型图、结构工程矩阵、中等稀疏矩阵、相对致密矩阵和高密度基因图，能够先观察行重排对支持集相似性、W16 列并集和连续列段的影响。`reddit`、`amazon-product` 以及 `mycielskian17–19` 很大，建议在第一轮闭环后再单独加入。

## 在实验实例上下载

把 `rsh_reorder_experiment.py`、`neutron_dataset_manifest.csv` 和 `download_neutron_dataset.py` 上传后执行：

```bash
python download_neutron_dataset.py \
  --preset small \
  --output-dir neutron-matrices \
  --archive-dir neutron-archives
```

下载完成后运行结构实验：

```bash
python rsh_reorder_experiment.py \
  --input neutron-matrices/cora.mtx \
  --input neutron-matrices/wiki-RfA.mtx \
  --input neutron-matrices/dawson5.mtx \
  --input neutron-matrices/olafu.mtx \
  --input neutron-matrices/pattern1.mtx \
  --input neutron-matrices/human_gene1.mtx \
  --output-dir rsh-neutron-results
```

SuiteSparse 文件服务当前可能返回 403。脚本会在 `download_report.json` 中记录失败 URL 和对应的 `ssget` 矩阵 ID；如果实例安装了 `ssget`，可以按照报告中的命令下载对应的 Matrix Market 文件，或使用 `--base-url` 指定可用镜像。

## 数据边界

上传包不包含论文中全部矩阵的二进制副本。原因是 SuiteSparse 当前文件服务离线，且完整集合中的最大矩阵达到数亿 NNZ，直接打包会产生不适合上传的巨大文件。清单仍然保留论文的完整数据身份和规模，下载脚本保证在实例上按名称、来源和缓存目录获取数据。

这些矩阵只用于当前结构重排层：

```text
真实矩阵
→ RSH / Rabbit / Neutron 行顺序
→ row-only/native 两种视图
→ W16/K16 结构指标
```

不会在这一轮据此推导 Bitmap、Gather、ND2NZ 或 Cube 性能结论。
