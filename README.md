# T22 / T23 结果原样传输

本孤立分支只用于规划方下载核验。没有修改 main 或其他已有分支，没有使用 Git LFS。实验冻结提交为3ecc8f4ae0f6a7dff556fe1ad4e888a500f3162b；上传准备时 origin/main 为8621d22ae5cf468e6f5070885d9ff63e4b7fed2c。

## 压缩包与来源

|包|来源|原始字节|原始文件数|入包文件数|压缩字节|
|---|---|---:|---:|---:|---:|
|rq3-validate-20261106.tar.gz|/Users/Zhuanz/.codex/visualizations/2026/11/05/01a1ac73-0f55-70c0-8e27-bb94bed5ad09/t22-t23-20261106/delivery/第一层实验结果/rq3-validate-20261106|14617072|7409|7394|1901732|
|round1-compare-20261106.tar.gz|/Users/Zhuanz/.codex/visualizations/2026/11/05/01a1ac73-0f55-70c0-8e27-bb94bed5ad09/t22-t23-20261106/delivery/第一层实验结果/round1-compare-20261106|31117549|6451|6438|8259483|
|round1-compare-stage3-inprogress-20261109.tar.gz|isolated read-only collection from work/ + raw stage3 evidence|203746912|6465|6465|53710470|

全部压缩包合计 63871685 B，低于1.5 GiB（1610612736 B）。分片由 `split -b 90m -d -a 3` 生成，本次每个包都只有part000。Git中只存分片，完整tar.gz在本地保留并可用下方命令重建。

## 结果原件与排除内容

T22与T23阶段1–2源目录中所有保留文件均逐字节复制，不修改、不删除、不重命名源文件。仅按用户要求在传输包中排除28个编译库/可执行文件，详见excluded-files.csv（原路径、字节数、SHA256与排除理由）。没有将deps、构建目录或第三方可执行文件上传。源代码、日志、映射等研究证据保留。原始SHA256SUMS内容保持原样，其中仍引用被排除的运行库；检查包内原始清单时应结合排除表。外层SHA256SUMS是本次传输的完整包与分片校验清单。

T23阶段3尚无正式封存结果目录。本次单独生成INPROGRESS快照，不修改work/stage3-collected等现有结果。快照含派发409例的当前结果/状态及原始阶段记录与日志，尚未完成的条件如实INCOMPLETE，缺输入按SKIPPED；不表示全量实验完成。它是运行中按文件采集的快照，表格和原始日志可能取自采集区间内不同瞬间，不假装事务级冻结。原始记录内容里的绝对路径是历史来源；tar成员路径全部相对路径，未改写记录内容。

新行序超过50MiB后依原方案留在本机，原正式目录中的orders-manifest保留原路径、大小、SHA。此次没有把这些目录外文件冒充原结果目录内容；此前另行提供的完整交接包包含实际行序。本分支用于本次指定的原结果目录传输。

## 三项补充材料

SUPPLEMENTS.txt一份文本包含全部补充表；supplements/同时提供便于处理的CSV及对应源码。

- post-E-round-times.csv：按矩阵×候选×τ列每轮elapsed标记、相邻标记差（含轮间开销）与已记录总轮数；timeout只列已完成轮次，冻结T21复用或未完成首轮时不补造记录。
- post-E-layout-times.csv：原d_sec是布局请求加lc.metrics的合计耗时；D-greedy和tail-co没有独立计时，因此单独秒数字段留空并说明。不能从现有日志可靠分离，未重跑，也不以own/D耗时相减冒充独立耗时。
- reddit-residual-and-workspace.csv：τ53残余46840行、1048063个A0非零；τ153残余93329行、5671784个A0非零。A1各加残余行数。LS预估分别6911541954与6560382824字节，公式和co-pair阈值见workspace-and-timing-definitions.txt与source/。co-pair错误的8GiB文字不是实测峰值，实际字节估算未记录的项目不填造值。
- products-mycielskian-condition-status.csv：920条候选×条件状态，含own/post、A0/A1、τ、放置、D规则、原因、本机/远端分配及是否已有最终case记录。INCOMPLETE可能是排队/运行中/尚未收到远端结果，原因列区分；不是把所有INCOMPLETE等同数值失败。

## 实验环境

macOS 15.2 arm64；Apple M1 Pro，8逻辑核，16GiB；Python3.12.10，Apple clang16.0.0。CPU实验，不用NPU。主环境NumPy2.4.4、SciPy1.17.1、NetworkX3.6.1。外部候选隔离环境：PyNNDescent0.7.0、Numba0.68.1、llvmlite0.50.0、NumPy2.5.4、SciPy1.18.1、scikit-learn1.9.1、PyMetis2025.2.2、joblib1.6.0、cloudpickle3.1.2、threadpoolctl3.8.0。KaHyPar1.3.7，direct k-way km1，epsilon0.03、seed0。Rabbit作者ref f93776e9c1e1d4a8962ee56bc7ff0091e6fe12dd；Linux ARM虚拟机，Boost1.58、gperftools2.16、libnuma2.0.18、OMP=1，无种子接口。environment/提供原始版本记录；原结果manifest和日志保留各阶段真实环境与版本证据。

## 下载、合并与校验

在本分支目录执行（先把三个包都合并，再核对含全部包/分片的清单）：

```sh
cat rq3-validate-20261106.tar.gz.part* > rq3-validate-20261106.tar.gz
cat round1-compare-20261106.tar.gz.part* > round1-compare-20261106.tar.gz
cat round1-compare-stage3-inprogress-20261109.tar.gz.part* > round1-compare-stage3-inprogress-20261109.tar.gz
sha256sum -c SHA256SUMS
```

单个包对应的形式是 `cat <名>.tar.gz.part* > <名>.tar.gz && sha256sum -c SHA256SUMS`；完整清单需要其余两个包也已合并。Windows可在WSL执行；macOS若无sha256sum，可用`shasum -a 256 -c SHA256SUMS`。

压缩包内部只有相对成员路径。外层SHA256SUMS同时覆盖每个完整tar.gz和每个分片。README、补充文件和排除表由Git提交固定版本。无实验分析结论。
