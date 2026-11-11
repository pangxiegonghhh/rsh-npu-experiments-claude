# T4 B-RSH-ref — 2026-11-11

状态：COMPLETE，按预登记早停走「否」分支。这里的 COMPLETE 表示本轮规定流程完成，不表示研究假设通过。

按选参规则后的第2轮最优/B1 = **0.997163764**，是控制器实际使用的早停值，大于0.98。以下同时给出全部已测 α/k、iso=tail 档位的原始最小值；两种读法均未达到2%，不影响早停结论。

在 cora 与 ogbn-arxiv 的 A0、W16、划分后、tail-co、own、τ=2/3 四点上，扫描最优组合相对 B1 的 T 几何均值比为 **0.992439692**（改善 **0.7560%**），未达到 2%。按 <0.5% 差距偏向 B1 的规则选 α=0.125、k=8 供E1诊断；「否」分支的候选池 B-RSH-ref 仍按方案沿用 B1，不把这组调参成绩外推到验证集。第3轮、七张验证集、诊断扫描与 E2/E3 均 SKIPPED，未将先导或未测内容充作结果。

cora 落成自检 PASS；cora、ogbn-arxiv、reddit、ogbn-products 的 (0,8,tail) 行置换全部与冻结 B1 逐位相同，未使用空行例外。cora/arxiv 完整网格的 ΣU 与 T 也逐值相同。选中配置的 cora 独立重复置换哈希相同。原 T21/T22/T23 结果未改。

E1：near 在 7/8 个「矩阵×τ×A0/A1」点上不差于 tail；T4-H4 = True。本轮早停主结论仍是补全 α/k 未达到预登记增益门槛；E1 单列，不改变早停决定。H1b/H2/H3 未检验；H5 的贡献数值见 manifest。

运行主机：hostA-macos-arm64，MacBookPro18,3 / Apple M1 Pro / 16 GiB / 8逻辑核 / macOS15.2。纯 CPU 结构实验，无 NPU 调用或租用实例，无实例关机项。

## 参数扫描

| 参数 | A0 四点几何均值 | A1 四点几何均值 |
|---|---:|---:|
| alpha=0,k=8,iso=tail | 0.647122538 | 0.632018745 |
| alpha=0.125,k=16,iso=tail | 0.645378219 | 0.631015318 |
| alpha=0.125,k=4,iso=tail | 0.645876478 | 0.628429355 |
| alpha=0.125,k=8,iso=near | 0.643722846 | 0.627669744 |
| alpha=0.125,k=8,iso=tail | 0.645287146 | 0.627291524 |
| alpha=0.25,k=8,iso=tail | 0.642230093 | 0.626706052 |
| alpha=0.5,k=8,iso=tail | 0.652803813 | 0.632945422 |
| alpha=0.75,k=8,iso=tail | 0.662784163 | 0.642566509 |
| alpha=1,k=8,iso=tail | 0.672199389 | 0.654988293 |

## 计时校准

| 校准点 | 本轮秒 | T23秒 | 比值 | 0.8–1.25 |
|---|---:|---:|---:|---|
| C4-U-calibration | 12.802524 | 11.963602 | 1.070123 | True |
| B-RSH-ref | 468.876978 | 385.995160 | 1.214722 | True |

B1 校准仅合计 cora/arxiv/reddit（三张，同派发的「否」分支定义）；products 本轮也在 hostA 复现，但不进入同主机八张时间轴。C4-U 校准覆盖同主机八张。超出校准区间按方案记录，不因计时差重跑。

## 产物与状态

- `results.csv`：与 T23 同字段，仅 B-RSH-ref；A0/A1、全行与两档τ、tail/tail-co、own/D-greedy；不含 B1 行。
- `status.csv`：逐「矩阵×参数×口径」状态表，另列早停跳过项；`parameter-scores.csv` 保存全部调参及E1几何均值。
- `manifest.json`：早停数字、选参、确定性、参数生效、每次诊断、主机、校准与代码哈希。
- `pareto-audit.csv`：按原短名单规则重算的候选池前沿与类别有效性，继承成绩和时间明确标注；最终名额取舍交规划方复审。
- `orders/`：本轮全部新行序及 record；每个 record 记录文件 sha256、峰值内存和 order_sec。
- `evaluations/`：未经汇总的 T23 评价器输出、guard 与返回状态；`logs/` 保留命令、rc、stdout、stderr、构建和输入核验。
- `code/`：实际运行源码。参考实现相对原 rect.cpp 只有57行新增；在此基础上仅增加不参与排序的候选对、孤立行和分量计数。两个diff单列。
- `spec/`：本轮规格快照。评价器字节不变；按派发明确要求使用归档 v2 Layout，而非旧工作区后来演进的 v7 默认实现。

诊断中 candidates 为 top-k 截断之前、排除自身的有向去重候选行对总数；isolated 为被搜索的非空行中 kNN 边集为空的数量，空行另列。near 的局部孤立判定和移动保留派发定义，不推称论文未写明的原意。

本地 `work/` 保留新编译库及原库/输入只读链接，不进入交回包；详见 `excluded-files.csv`。SHA256SUMS 覆盖交回包内全部常规文件（自身除外）。输入与库均可由记录中的原T23本地路径恢复并核对哈希；库可用 manifest 编译命令重建。

源码、参数与硬门槛均未因结果调整。下一操作：规划方复审 manifest、结果表与原始日志，决定后续；本轮不启动新实验，不改 candidates.md。

## 逐矩阵、参数与评价口径状态表（交付文档v2）

以下每格覆盖全行及两档τ、T23完整放置和D规则网格；逐条件见status.csv。所有原始结果及v1归档保持不变。

| 矩阵 | 参数 | 口径 | 条件数 | 状态 |
|---|---|---|---:|---|
| cora | alpha=0,k=8,iso=tail | A0 | 10 | OK |
| cora | alpha=0,k=8,iso=tail | A1 | 10 | OK |
| cora | alpha=0.125,k=16,iso=tail | A0 | 10 | OK |
| cora | alpha=0.125,k=16,iso=tail | A1 | 10 | OK |
| cora | alpha=0.125,k=4,iso=tail | A0 | 10 | OK |
| cora | alpha=0.125,k=4,iso=tail | A1 | 10 | OK |
| cora | alpha=0.125,k=8,iso=near | A0 | 10 | OK |
| cora | alpha=0.125,k=8,iso=near | A1 | 10 | OK |
| cora | alpha=0.125,k=8,iso=tail | A0 | 10 | OK |
| cora | alpha=0.125,k=8,iso=tail | A1 | 10 | OK |
| cora | alpha=0.25,k=8,iso=tail | A0 | 10 | OK |
| cora | alpha=0.25,k=8,iso=tail | A1 | 10 | OK |
| cora | alpha=0.5,k=8,iso=tail | A0 | 10 | OK |
| cora | alpha=0.5,k=8,iso=tail | A1 | 10 | OK |
| cora | alpha=0.75,k=8,iso=tail | A0 | 10 | OK |
| cora | alpha=0.75,k=8,iso=tail | A1 | 10 | OK |
| cora | alpha=1,k=8,iso=tail | A0 | 10 | OK |
| cora | alpha=1,k=8,iso=tail | A1 | 10 | OK |
| ogbn-arxiv | alpha=0,k=8,iso=tail | A0 | 10 | OK |
| ogbn-arxiv | alpha=0,k=8,iso=tail | A1 | 10 | OK |
| ogbn-arxiv | alpha=0.125,k=16,iso=tail | A0 | 10 | OK |
| ogbn-arxiv | alpha=0.125,k=16,iso=tail | A1 | 10 | OK |
| ogbn-arxiv | alpha=0.125,k=4,iso=tail | A0 | 10 | OK |
| ogbn-arxiv | alpha=0.125,k=4,iso=tail | A1 | 10 | OK |
| ogbn-arxiv | alpha=0.125,k=8,iso=near | A0 | 10 | OK |
| ogbn-arxiv | alpha=0.125,k=8,iso=near | A1 | 10 | OK |
| ogbn-arxiv | alpha=0.125,k=8,iso=tail | A0 | 10 | OK |
| ogbn-arxiv | alpha=0.125,k=8,iso=tail | A1 | 10 | OK |
| ogbn-arxiv | alpha=0.25,k=8,iso=tail | A0 | 10 | OK |
| ogbn-arxiv | alpha=0.25,k=8,iso=tail | A1 | 10 | OK |
| ogbn-arxiv | alpha=0.5,k=8,iso=tail | A0 | 10 | OK |
| ogbn-arxiv | alpha=0.5,k=8,iso=tail | A1 | 10 | OK |
| ogbn-arxiv | alpha=0.75,k=8,iso=tail | A0 | 10 | OK |
| ogbn-arxiv | alpha=0.75,k=8,iso=tail | A1 | 10 | OK |
| ogbn-arxiv | alpha=1,k=8,iso=tail | A0 | 10 | OK |
| ogbn-arxiv | alpha=1,k=8,iso=tail | A1 | 10 | OK |

| 其他矩阵/步骤 | 范围 | 状态 | 原因 |
|---|---|---|---|
| reddit、ogbn-products | (0,8,tail) 行序复现 | OK | 已与冻结B1逐位核对；未重新评价验证集 |
| 同主机八张 | C4-U 行序计时 | OK | 八次实际执行，详见manifest |
| 第3轮、七张验证集、诊断扫描、E2/E3 | 所有计划条件 | SKIPPED | 预登记调参改善不足2%早停 |

交付修订v2仅补充本状态表、清理计划中间状态，并附completion-audit.json。GitHub推送仍待用户对确切仓库的直接授权；不得把本地提交写成上传完成。
