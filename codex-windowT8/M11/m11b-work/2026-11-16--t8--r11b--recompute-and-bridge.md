---
type: results-report
date: 2026-11-16
experiment_line: t8
round: 11b
purpose: recompute-and-bridge
status: complete
source_artifacts:
  - analysis-output/analysis-report.md
  - analysis-output/stats-appendix.md
  - analysis-output/figure-catalog.md
linked_experiments:
  - PROTOCOL.md
linked_results: []
---

# T8 / Round 11b / Recompute and bridge / 2026-11-16

## 结果与决定

离线R1–R12已交回，原M11 tar、原analysis-output和原报告均保持只读；重算基准21文件及全部204,631个原始文件哈希均不变。M11b-B1确认原生成器实际随机1/2行间距，按计划取消上卡部分。**B2结论：不可互推；合成网格仅作机制探查，不可用于预测真实回放选路**（4格中0格d≤15%，4格d>30%）。**B3转置50/50正确、plain-only50/50不等价，无法估算同输出转置差价，未凑12000条无效计时。**

## 重算的重要更正

原归一化计算数值没有算错，问题是字段语义与单位标签：原μs/矩阵应为μs/完整回放：T=(max end−min begin)/50/(E×24)，E是回放重复次数而非时钟周期。Cora每回放170窗口，20轮示例均值12.594219828→12.5942；单窗为该数/170。原6/8比例判读不变。R2异常格判(c)现有证据分不开，不剔除；审核4.42等预测是h16除16的摊销，不是真h1斜率。cold按行按已审计地址重建确实覆盖≥4×L2唯一数据，但无PMU；冷档更大的相对降幅来自ND变慢。hot-only【事后】3/4不替换原8格判据。

R5/R6/R7补齐ND/按行/按条B0/B1、绝对值、固定路径及选优差；R8补全cold/实际gap与API合并率；R9无PMU不能归因；R10指出旧门重做LoadB覆盖计时L0，不能验证primitive等价；R11标签无对调但时差机制不能单凭几何断言；R12的54/54格均有已保存输出覆盖。逐项MD/CSV见../m11-work/analysis-recompute-20261115。

## B2 设置与统计

三组(U,R)×random-gap/cora-like×N128/256×两精度×三路径=72点；另计时前增加12个同批Cora B1控制，减少跨启动参考混淆。84×20=1680条，40320条每核时钟独立复算PASS。普通84项和逐tile强地址84项均在任何正式计时之前完成；kernel.cpp SHA与原M11逐字节相同：63194374d72de61c0bded87ef407d252bb3c3e3519f1d21cd8e242b3242f34b0。host仅加五条哨兵原值落盘，20区组共800条哨兵原值。

同一24 AIC/共同gmax与原M4消费，hot工作集、实际分配/跨度均记录；合成每份一个窗口，Cora每份170窗口，跨几何只比普通/ND之比。效果采用ratio of means、10000成对区组bootstrap seed20261115，点95%CI。原0.15/0.30阈值保持，0.30仍为原稿【推】阈值。完整均值/SD/CI、两普通路径、全部时钟与哨兵见analysis-output。

| dtype | N | synth_row_over_ND | same_batch_replay_row_over_ND | relative_deviation | within_15pct | over_30pct | deviation_to_old |
|---|---|---|---|---|---|---|---|
| FP16 | 128 | 1.932571 | 1.221193 | 0.582527 | False | True | 0.449711 |
| FP16 | 256 | 0.987111 | 0.737890 | 0.337748 | False | True | 0.337081 |
| FP32 | 128 | 0.986707 | 0.746274 | 0.322177 | False | True | 0.321746 |
| FP32 | 256 | 0.977595 | 0.738578 | 0.323618 | False | True | 0.320062 |

这四格的按行/ND优劣方向与同批真实回放仍一致；“不可互推”是原稿的**定量比值误差**门失败，并非观察到四格选路方向相反。合成三格仅约1%–2%按行优势，真实回放约25%–26%，幅度不可直接外推。

【事后补充】同批FP16/N128按行Cora控制均值11.749101 μs/回放、SD=1.514371，逐轮范围9.722787–12.838434，呈约9.72与12.83两档；ND控制仍约9.621。该格比原M11的均值配对比变化约−8.39%，其他三个控制比值变化均小于0.3%。所有轮保留；不按双峰划组重算主门，不把哨兵通过当作所有配置稳定的证明。该现象进一步阻止将异常简单归因为固定blockCount=8惩罚；测量故障/运行状态/流水几何交互仍分不开。以同批与原M11两套参考计算B2，4格偏差都仍超过30%。

另固定报告结构比值之差（(56,50)的按行/ND减(36,18)）：

| dtype | N | layout | u56r50_ratio | u36r18_ratio | ratio_difference | ci_low | ci_high |
|---|---|---|---|---|---|---|---|
| FP16 | 128 | random-gap | 1.302987 | 1.932776 | -0.629789 | -0.659271 | -0.600531 |
| FP16 | 128 | cora-like | 1.108328 | 1.932571 | -0.824244 | -0.851685 | -0.797330 |
| FP16 | 256 | random-gap | 0.698754 | 0.988641 | -0.289887 | -0.292095 | -0.287601 |
| FP16 | 256 | cora-like | 0.604254 | 0.987111 | -0.382857 | -0.385537 | -0.380116 |
| FP32 | 128 | random-gap | 0.701215 | 0.988672 | -0.287457 | -0.289601 | -0.285367 |
| FP32 | 128 | cora-like | 0.606568 | 0.986707 | -0.380139 | -0.384081 | -0.375937 |
| FP32 | 256 | random-gap | 0.640472 | 0.992237 | -0.351765 | -0.352300 | -0.351195 |
| FP32 | 256 | cora-like | 0.557653 | 0.977595 | -0.419942 | -0.423063 | -0.417031 |

图B2-bridge展示均值合成点与真实回放的相对路径比，不可混为绝对时间。图B2-structure-shift分两gap排法展示结构改变，不能把该差值当作真实B0/B1的1.48倍加速或纯R因果效应。两图均经数据表核对并目视检查，点CI非同时覆盖。

## B3 正确性与无法估计的原因

新独立kernel-b3直接将被测L0B送入MMAD，与强地址标记CPU参考比较，没有后续LoadB覆盖。h=1/2/4/8/16、五种N、两精度：transpose50/50 PASS；plain-only50/50 FAIL，全部实际输出/参考/失败原因保留。原稿要求无效plain不得强行计时，故Δ、Δ'、对字节斜率s、fold均NOT_ESTIMABLE。B3-planned-grid-status.csv逐项列出完整600个计划配置、每项20轮计划数与实际正式0轮及原因；未虚构缺失值。

此外，原稿plain+explicit所指的一条Transpose/TransDataTo5HD是向量UB接口，官方CANN9支持TPosition为VECIN/VECCALC/VECOUT，未提供直接L0B→L0B的同等调用。实际SDK转置头文件已归档，不执行非法位置调用，不把转置挪到计时外。要经UB/GM/AIV实现另一条完整链会引入搬运和同步，超出本“普通L0加载后多一条转置”的对照，未自动扩范围。

官方依据：[Transpose](https://www.hiascend.com/doc_center/source/en/CANNCommunityEdition/900/API/ascendcopapi/atlasascendc_api_07_0199.html)、[TransDataTo5HD](https://www.hiascend.com/doc_center/source/en/CANNCommunityEdition/900/API/ascendcopapi/atlasascendc_api_07_0200.html)。这限定当前可用候选，并非对所有硬件方案不可能的证明。h<16在Cube加载仍补齐16行，实际字节16*N*es，不应拿h*N*es假定字节变化；近似常数与CI含0均不能推出纯发射开销。

## 偏离、错误与限制

- B3原稿600点×20应为12000而非1200；无合法参照时不进入此正式网格。B1取消是计划内分岔；B2增加12同批控制在计时前登记，原72点不变。
- B3使用独立target直接消费L0结果，未覆盖原M11 binary；B2 kernel逐字节不变。B3与原binary的差异明确属于验证实现修复，未据此声称完成等价性能对照。
- 当前包/本工作区缺少引用的交回模板，使用现有M11表并补齐item/case_id/kernel_variant/layout与thresholds字段，未冒称读过缺失模板。
- 首区组登记因摘要默认6位有效数字、哨兵原值12位导致过严一致性断言；保留失败源码/日志，仅改登记容差和从原5条重建漂移，原binary、5%阈值、全部计时不变。保存已完整首区组并重核，不按结果重挑点。恢复首区组elapsed_s仅登记复核耗时，非测量墙钟时长。
- 原1MB包上传413，改73712B源码+本机重建输入，全部1340二进制输入SHA与本地一致。启动浏览器连接短暂失败后恢复，未新租卡。
- 只有Cora与三个均值点；cora-like复制gap边缘而非联合分布。没有PMU、未逐路径g调优、未补cold，不是完整稀疏SpMM，结论不能外推到任意矩阵。没有修改论文、原M11归档或推送Git。当前仓库未绑定Obsidian，本报告只作本地交付，未写回知识库。

## 复核与产物

设备新目录/data/t8-m11b-20261115，复用OP08JZ85MYKCJKH3；本次容器7e4ad1fd20aa、物理NPU5、PCI0000:41:00.0，开工核验空闲。启动前累计8h57m，关机后9h27m；平台已在2026-11-16凌晨核对“已关机”，新增约30分钟。按此前4元/小时估算约2元（开机弹窗0.00显示未用作账单，实际以平台账单为准）。完整72,655,915字节归档与10,090文件SHA均在本地通过核验；无远端独有的必要证据，临时认证header已删除。详见shutdown-verification.json，不依赖远端约36小时保留。

- analysis-output/analysis-report.md、stats-appendix.md、figure-catalog.md、figures/：严格分析包。
- ../m11-work/analysis-recompute-20261115/：R1–R12完整离线重算、cases适配表、SHA256SUMS。
- m11b-evidence-complete.tar.gz及archive-receipt.json：全部新增设备原值、输入、源码、二进制、环境、编译及失败记录；SHA256=d86c6a02336dc3b3f93a886b0cdcd6db5fcf34ff580ffb3fecdc1f6654839e87。
- analysis-output/verification.json：1680条与40320核原时钟/计数/归一化及168项前置正确性核验。
- recovered-evidence/GATES-BEFORE-TIMING.json、B3-GATE-RESULTS.json、manifests/thresholds.csv、prep/structures.json：事前门、候选失败、阈值、完整几何。
- analyze.py、prepare.py、run_experiment.py：派生计算及设备规程源码；离线不运行回传binary。

离线复算：在本m11b-work执行`M11B_DATA_ROOT="$PWD/recovered-evidence" python3 analyze.py`。原M11重算在独立analysis-recompute目录执行recompute.py。

## 下一步决定

保持实例关闭。B2下游选路表达按本次阈值判读加限定；B3转置成本标为不可估，不把旧0.00055μs当物理转置系数。若继续研究完整UB/AIV替代链或PMU机制，应另定等价路径与完整计时边界；本次不自动增加设备工作。
