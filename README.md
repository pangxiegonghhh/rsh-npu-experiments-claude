# T23 阶段3正式结果：round1-compare-stage3-20261106

全部409例已有真实终止记录；不是运行中快照。按派发§8保留超时/中断/工作空间失败为INCOMPLETE，不重跑、不调参。

整例：320 OK / 48 INCOMPLETE / 41 SKIPPED；另6个可选参照SKIPPED。正式条件6276行：5396 OK / 588 INCOMPLETE / 292 SKIPPED。

本目录是2026-11-10对已核验双主机终止证据的正式封存。原合并包与T21/T22/阶段1–2全部不改。数值表逐字节复制；只新增清单、README和补充材料。

## 下载与合并校验

```sh
cat round1-compare-stage3-20261106.tar.gz.part* > round1-compare-stage3-20261106.tar.gz
sha256sum -c SHA256SUMS
```

分支根SHA256SUMS覆盖完整tar.gz与分片；解包后目录内SHA256SUMS覆盖所有正式文件（自身除外）。raw/内原始主机清单是历史证据，可能指向仅本地保留的ELF/行序，请以正式目录根清单核验本包。

## 输入与T19差异

结构按存储条目定义，显式零保留；A0去对角/固定对称处理，A1按定义加I，残余集合按A0度数固定。
Reddit实测nnz(A0)=114615892，与T19一致；products点数2449029，与T19一致，nnz(A0)=123718024，比T19的123718152少128。原始边表实测128个对角存储条目，不用“64个自环”的旧推测替代实测；未为匹配引用值改图。
mycielskian15下载失败，不能提供输入SHA/实算规模/τ；相关条件SKIPPED，不用引用规模冒充实测。

|matrix|n|stored_entries|diagonal_entries|nnz_A0|explicit_zero_entries|sha256|source_url|
|---|---|---|---|---|---|---|---|
|cora|2708|5278|0|10556|0|f54431cb38cf0e4b832093889736bf1e3397019b90a186a1c13405038a573856|https://github.com/pangxiegonghhh/rsh-npu-experiments-claude/blob/87594cc9e80e800c77a65988c09f7067b63957be/第一层实验结果/cora-pilot-20261104/neutron-matrices/cora.mtx|
|wiki-RfA|11380|188077|93|361960|11493|de2a93800a08edb5d3e6289b57b56aa8afd43c37b709306efbceecf137adf005|https://snap.stanford.edu/data/wiki-RfA.txt.gz|
|olafu|16146|515651|16146|999010|0|8ff0691051957f7e4c6fb302c3ad026ee526691958d4f1c2c0a5520c8e89a4d5|https://www.cise.ufl.edu/research/sparse/MM/Simon/olafu.tar.gz|
|dawson5|51537|531157|51537|959240|0|549f0f6076676c622a32a4d622fd5d2dc8d0a0651c22307ca4435c569d94a0d6|https://www.cise.ufl.edu/research/sparse/MM/GHS_indef/dawson5.tar.gz|
|human_gene1|22283|12345963|22283|24647360|0|5c035d8398baf2045367e3d77b12bc367a6f3e4ef9e8e202849de480b0ce120f|https://www.cise.ufl.edu/research/sparse/MM/Belcastro/human_gene1.tar.gz|
|pattern1|19242|4671337|19242|9304190|0|62e04b81ff10bca38216a8f31235085673f018e6fa055c672b6fdae6ddd92ae1|https://www.cise.ufl.edu/research/sparse/MM/Andrianov/pattern1.tar.gz|
|ogbn-arxiv|169343|1166243|0|2315598|0|c80df13aa49c918bc4daf8634d0458910ad0be0bfd8be634038bf03b566de108|https://snap.stanford.edu/ogb/data/nodeproppred/arxiv.zip|
|ogbn-products|2449029|61859140|128|123718024|0|a012950cc853f8262d5bbc9d93ca393e978e1e8f34bcf639125585dc3b515341|https://snap.stanford.edu/ogb/data/nodeproppred/products.zip|
|reddit|232965|114615892|0|114615892|0|42b4a8d9bbbaa61e74611c125673865712fb9498da99c1571ebc1fb180bfc2e0|https://dgl-data.s3-accelerate.amazonaws.com/dataset/reddit.zip|
|mycielskian15|缺失|缺失|缺失|缺失|缺失|缺失|SuiteSparse official index https://sparse.tamu.edu/ and original failed-download logs|

## τ实算、残余与工作空间

8GiB为安全估算门槛，不是实测内存。LS公式与co-chain公式/缺失原因见supplements/workspace-formulas.md；每τ的具体数值见下表及CSV。

|matrix|tau|tau_rule|residual_rows|residual_nnz_A0|LS_preflight_bytes|over_estimated_budget|
|---|---|---|---|---|---|---|
|cora|2|fixed|1068|1651|766812|False|
|cora|3|fixed|1621|3310|694992|False|
|wiki-RfA|2|fixed|4736|5811|20294240|False|
|wiki-RfA|3|fixed|5366|7701|19979968|False|
|olafu|53|q20|6186|299197|53824076|False|
|olafu|56|q40|6584|321281|53646776|False|
|dawson5|15|q20|10528|120194|117274584|False|
|dawson5|17|q40|33263|506680|77668836|False|
|human_gene1|82|q20|4466|111643|1197148132|False|
|human_gene1|342|q40|8917|988097|1193734392|False|
|pattern1|8|q20|4155|33240|456974858|False|
|pattern1|757|q40|10918|2937865|452455942|False|
|ogbn-arxiv|2|fixed|39126|57648|831425360|False|
|ogbn-arxiv|3|fixed|54353|103329|747133384|False|
|ogbn-products|2|fixed|236776|273719|180695009260|True|
|ogbn-products|3|fixed|312413|500630|174717828430|True|
|reddit|53|q20|46840|1048063|6911541954|False|
|reddit|153|q40|93329|5671784|6560382824|False|
|mycielskian15|缺失|input unavailable|缺失|缺失|缺失|缺失|

## co_chain守卫窗口数

单窗口残余点>400触发跳过。以下是保存的逐条件报告数，含缓存继承，求和不是独立物理扫描次数。失败前未记录计数的条件保持缺失，不能当0；完整原报告与主机说明见guard-counts.csv。

|matrix|W|tau|reported_conditions|min_windows|max_windows|sum_reported_windows|
|---|---|---|---|---|---|---|
|cora|128|3|136|0|2|20|
|cora|128|none|68|0|0|0|
|cora|16|2|144|0|0|0|
|cora|16|3|144|0|0|0|
|cora|16|none|72|0|0|0|
|cora|32|3|136|0|0|0|
|cora|32|none|68|0|0|0|
|cora|64|3|136|0|0|0|
|cora|64|none|68|0|0|0|
|dawson5|128|17|136|0|143|3860|
|dawson5|128|none|68|0|0|0|
|dawson5|16|15|112|0|0|0|
|dawson5|16|17|112|0|0|0|
|dawson5|16|none|56|0|0|0|
|dawson5|32|17|136|0|30|160|
|dawson5|32|none|68|0|0|0|
|dawson5|64|17|136|0|281|2212|
|dawson5|64|none|68|0|0|0|
|human_gene1|16|342|112|0|714|28836|
|human_gene1|16|82|112|0|4|108|
|human_gene1|16|none|56|0|0|0|
|ogbn-arxiv|128|3|136|0|9|208|
|ogbn-arxiv|128|none|68|0|0|0|
|ogbn-arxiv|16|2|144|0|1|4|
|ogbn-arxiv|16|3|144|0|4|136|
|ogbn-arxiv|16|none|72|0|0|0|
|ogbn-arxiv|32|3|136|0|3|112|
|ogbn-arxiv|32|none|68|0|0|0|
|ogbn-arxiv|64|3|136|0|5|132|
|ogbn-arxiv|64|none|68|0|0|0|
|ogbn-products|16|2|114|0|0|0|
|ogbn-products|16|3|114|0|1|4|
|ogbn-products|16|none|58|0|0|0|
|olafu|16|53|112|0|0|0|
|olafu|16|56|112|0|0|0|
|olafu|16|none|56|0|0|0|
|pattern1|16|757|112|0|504|7040|
|pattern1|16|8|112|0|12|364|
|pattern1|16|none|56|0|0|0|
|reddit|16|153|182|0|3753|191444|
|reddit|16|53|252|0|182|18604|
|reddit|16|none|112|0|0|0|
|wiki-RfA|128|3|136|0|5|128|
|wiki-RfA|128|none|68|0|0|0|
|wiki-RfA|16|2|112|0|0|0|
|wiki-RfA|16|3|112|0|0|0|
|wiki-RfA|16|none|56|0|0|0|
|wiki-RfA|32|3|136|0|0|0|
|wiki-RfA|32|none|68|0|0|0|
|wiki-RfA|64|3|136|0|1|12|
|wiki-RfA|64|none|68|0|0|0|

## 环境、工具与阶段1–2差异

阶段1–2主机为macOS15.2 arm64/M1 Pro16GiB，Python3.12.10、NumPy2.4.4、SciPy1.17.1、Apple clang16；本阶段hostA相同。
新增hostB为Windows/WSL2 Linux6.18.54.1 x86_64、AMD Ryzen7 5800H，Python3.12.3、NumPy2.4.4、SciPy1.17.1、g++13.3.0；原RSS KiB→MiB适配与11项新WSL门禁已核验。每行保留实际主机，跨主机时间不混合平均。
外部依赖：PyNNDescent0.7.0 / numba0.68.1 / llvmlite0.50.0 / pymetis2025.2.2 / KaHyPar1.3.7。hostA隔离外部依赖NumPy2.5.4、SciPy1.18.1，与主评价环境不同，原版本JSON/扩展SHA均保留。
Rabbit锁定作者ref f93776e9c1e1d4a8962ee56bc7ff0091e6fe12dd，Linux ARM guest、Boost1.58、gperftools2.16、libnuma2.0.18，OMP=1，无随机种子API。hostB的-R复用hostA历史Rabbit-U粗序，order_sec可能含历史coarse_seconds；当前local_seconds另见原记录，不能视为WSL总实测。
v2→v7缓存/计数实现按原启用时间保留；不把新库追用于早期进程。原命令、导入源码SHA与实际加载DLL/ELF SHA分主机保存。

## 行序与排除内容

新算269份，638252226字节（>50MiB），全部只留本地；复用117条仅引用，未复制到orders/。逐份大小、来源与SHA256见orders-manifest.json。
本地完整行序/检查点包：/Users/Zhuanz/.codex/visualizations/2026/11/05/01a1ac73-0f55-70c0-8e27-bb94bed5ad09/t22-t23-20261106/delivery/T23-orders-merged-20261110.tar.gz；318992249字节；SHA256 `ff0e87f49ef718ad30a0d50c66cd56f10f8f8bc677e1f595b9cd885532c1b334`。该本地包不上传。
排除110项，见excluded-files.csv（原路径/字节数/SHA256/理由）：编译库/可执行文件、批量排列/粗排映射以及非阶段3旧封存包。原件均保留，源码与构建/加载哈希仍可核验。

## 补充计时与INCOMPLETE分类

64个post-E组合，267条已记录完整轮次；逐轮秒数未独立记录，明确标缺失，只附原始累计elapsed，不作差。D-greedy与tail-co独立秒数同样缺失；72条原始combined d_sec仅标为layout+metrics总计时，不能冒充分段。
supplements/INCOMPLETE-cases.csv覆盖48例，按超时/工作空间估算门槛/被中断归类，可多原因；当前无排队中。products C6-HP原exit -9归“被中断”，来源未证实，不称为实测OOM；Reddit C8-METIS保留τ53超时和τ153重启中断，无伪造退出码。
原完成轮次检查点完整向量仅本地保留，包内为明确标注的派生元数据。未执行检查点LS/D/评价重跑，未把其tracked数值提升为新验证结果；原INCOMPLETE仍INCOMPLETE。

## 矩阵 × 候选 × W 状态表

覆盖全部409正式例与6可选参照；其中包含reddit/products/mycielskian15及W32/64/128敏感性，不把生成OK等同整例OK。

|matrix|member|W|seed|status|reason|
|---|---|---|---|---|---|
|cora|C3-A|16|0|OK||
|cora|C3-W4-noP|16|0|OK||
|cora|C3-W4-R|16|0|OK||
|cora|C3-A-R|16|0|OK||
|cora|C4-U-R|16|0|OK||
|cora|C4-T-R|16|0|OK||
|cora|C7-I-R|16|0|OK||
|cora|C5-CN|16|0|OK||
|cora|C5-U-CN|16|0|OK||
|cora|C6-HP|16|0|OK||
|cora|C6-RB (T21 口径)|16|0|OK||
|cora|C6-M mnc=1 (T21 口径)|16|0|OK||
|cora|C6-M mnc=4 (T21 口径)|16|0|OK||
|cora|C6-M mnc=16 (T21 口径)|16|0|OK||
|ogbn-arxiv|C3-A|16|0|OK||
|ogbn-arxiv|C3-W4-noP|16|0|OK||
|ogbn-arxiv|C3-W4-R|16|0|OK||
|ogbn-arxiv|C3-A-R|16|0|OK||
|ogbn-arxiv|C4-U-R|16|0|OK||
|ogbn-arxiv|C4-T-R|16|0|OK||
|ogbn-arxiv|C7-I-R|16|0|OK||
|ogbn-arxiv|C5-CN|16|0|OK||
|ogbn-arxiv|C5-U-CN|16|0|OK||
|ogbn-arxiv|C6-HP|16|0|OK||
|ogbn-arxiv|C6-RB (T21 口径)|16|0|OK||
|ogbn-arxiv|C6-M mnc=1 (T21 口径)|16|0|OK||
|ogbn-arxiv|C6-M mnc=4 (T21 口径)|16|0|OK||
|ogbn-arxiv|C6-M mnc=16 (T21 口径)|16|0|OK||
|wiki-RfA|C3-A|16|0|OK||
|wiki-RfA|C3-W4-noP|16|0|OK||
|wiki-RfA|C3-W4-R|16|0|OK||
|wiki-RfA|C3-A-R|16|0|OK||
|wiki-RfA|C4-U-R|16|0|OK||
|wiki-RfA|C4-T-R|16|0|OK||
|wiki-RfA|C7-I-R|16|0|OK||
|wiki-RfA|C5-CN|16|0|OK||
|wiki-RfA|C5-U-CN|16|0|OK||
|wiki-RfA|C6-HP|16|0|OK||
|wiki-RfA|C6-RB (T21 口径)|16|0|OK||
|wiki-RfA|C6-M mnc=1 (T21 口径)|16|0|OK||
|wiki-RfA|C6-M mnc=4 (T21 口径)|16|0|OK||
|wiki-RfA|C6-M mnc=16 (T21 口径)|16|0|OK||
|dawson5|C3-A|16|0|OK||
|dawson5|C3-W4-noP|16|0|OK||
|dawson5|C3-W4-R|16|0|OK||
|dawson5|C3-A-R|16|0|OK||
|dawson5|C4-U-R|16|0|OK||
|dawson5|C4-T-R|16|0|OK||
|dawson5|C7-I-R|16|0|OK||
|dawson5|C5-CN|16|0|OK||
|dawson5|C5-U-CN|16|0|OK||
|dawson5|C6-HP|16|0|OK||
|dawson5|C6-RB (T21 口径)|16|0|OK||
|dawson5|C6-M mnc=1 (T21 口径)|16|0|OK||
|dawson5|C6-M mnc=4 (T21 口径)|16|0|OK||
|dawson5|C6-M mnc=16 (T21 口径)|16|0|OK||
|olafu|C3-A|16|0|OK||
|olafu|C3-W4-noP|16|0|OK||
|olafu|C3-W4-R|16|0|OK||
|olafu|C3-A-R|16|0|OK||
|olafu|C4-U-R|16|0|OK||
|olafu|C4-T-R|16|0|OK||
|olafu|C7-I-R|16|0|OK||
|olafu|C5-CN|16|0|OK||
|olafu|C5-U-CN|16|0|OK||
|olafu|C6-HP|16|0|OK||
|olafu|C6-RB (T21 口径)|16|0|OK||
|olafu|C6-M mnc=1 (T21 口径)|16|0|OK||
|olafu|C6-M mnc=4 (T21 口径)|16|0|OK||
|olafu|C6-M mnc=16 (T21 口径)|16|0|OK||
|pattern1|C3-A|16|0|OK||
|pattern1|C3-W4-noP|16|0|OK||
|pattern1|C3-W4-R|16|0|OK||
|pattern1|C3-A-R|16|0|OK||
|pattern1|C4-U-R|16|0|OK||
|pattern1|C4-T-R|16|0|OK||
|pattern1|C7-I-R|16|0|OK||
|pattern1|C5-CN|16|0|OK||
|pattern1|C5-U-CN|16|0|OK||
|pattern1|C6-HP|16|0|OK||
|pattern1|C6-RB (T21 口径)|16|0|OK||
|pattern1|C6-M mnc=1 (T21 口径)|16|0|OK||
|pattern1|C6-M mnc=4 (T21 口径)|16|0|OK||
|pattern1|C6-M mnc=16 (T21 口径)|16|0|OK||
|human_gene1|C3-A|16|0|OK||
|human_gene1|C3-W4-noP|16|0|OK||
|human_gene1|C3-W4-R|16|0|OK||
|human_gene1|C3-A-R|16|0|OK||
|human_gene1|C4-U-R|16|0|OK||
|human_gene1|C4-T-R|16|0|OK||
|human_gene1|C7-I-R|16|0|OK||
|human_gene1|C5-CN|16|0|OK||
|human_gene1|C5-U-CN|16|0|OK||
|human_gene1|C6-HP|16|0|OK||
|human_gene1|C6-RB (T21 口径)|16|0|OK||
|human_gene1|C6-M mnc=1 (T21 口径)|16|0|OK||
|human_gene1|C6-M mnc=4 (T21 口径)|16|0|OK||
|human_gene1|C6-M mnc=16 (T21 口径)|16|0|OK||
|cora|C5-CN|16|1|OK||
|cora|C5-CN|16|2|OK||
|cora|C5-U-CN|16|1|OK||
|cora|C5-U-CN|16|2|OK||
|ogbn-arxiv|C5-CN|16|1|OK||
|ogbn-arxiv|C5-CN|16|2|OK||
|ogbn-arxiv|C5-U-CN|16|1|OK||
|ogbn-arxiv|C5-U-CN|16|2|OK||
|cora|B0|32|0|OK||
|cora|B1|32|0|OK||
|cora|B-RCM-ref|32|0|OK||
|cora|C9-Gorder|32|0|OK||
|cora|C9-S|32|0|OK||
|cora|C10-BP|32|0|OK||
|cora|C2-LSH|32|0|OK||
|cora|C3-W1|32|0|OK||
|cora|C3-W4|32|0|OK||
|cora|C4-U|32|0|OK||
|cora|C4-T|32|0|OK||
|cora|C7-I|32|0|OK||
|cora|C1-J|32|0|OK||
|cora|C1-H|32|0|OK||
|cora|C5|32|0|OK||
|cora|C5-U|32|0|OK||
|cora|C8-METIS|32|0|OK||
|cora|B0|64|0|OK||
|cora|B1|64|0|OK||
|cora|B-RCM-ref|64|0|OK||
|cora|C9-Gorder|64|0|OK||
|cora|C9-S|64|0|OK||
|cora|C10-BP|64|0|OK||
|cora|C2-LSH|64|0|OK||
|cora|C3-W1|64|0|OK||
|cora|C3-W4|64|0|OK||
|cora|C4-U|64|0|OK||
|cora|C4-T|64|0|OK||
|cora|C7-I|64|0|OK||
|cora|C1-J|64|0|OK||
|cora|C1-H|64|0|OK||
|cora|C5|64|0|OK||
|cora|C5-U|64|0|OK||
|cora|C8-METIS|64|0|OK||
|cora|B0|128|0|OK||
|cora|B1|128|0|OK||
|cora|B-RCM-ref|128|0|OK||
|cora|C9-Gorder|128|0|OK||
|cora|C9-S|128|0|OK||
|cora|C10-BP|128|0|OK||
|cora|C2-LSH|128|0|OK||
|cora|C3-W1|128|0|OK||
|cora|C3-W4|128|0|OK||
|cora|C4-U|128|0|OK||
|cora|C4-T|128|0|OK||
|cora|C7-I|128|0|OK||
|cora|C1-J|128|0|OK||
|cora|C1-H|128|0|OK||
|cora|C5|128|0|OK||
|cora|C5-U|128|0|OK||
|cora|C8-METIS|128|0|OK||
|ogbn-arxiv|B0|32|0|OK||
|ogbn-arxiv|B1|32|0|OK||
|ogbn-arxiv|B-RCM-ref|32|0|OK||
|ogbn-arxiv|C9-Gorder|32|0|OK||
|ogbn-arxiv|C9-S|32|0|OK||
|ogbn-arxiv|C10-BP|32|0|OK||
|ogbn-arxiv|C2-LSH|32|0|OK||
|ogbn-arxiv|C3-W1|32|0|OK||
|ogbn-arxiv|C3-W4|32|0|OK||
|ogbn-arxiv|C4-U|32|0|OK||
|ogbn-arxiv|C4-T|32|0|OK||
|ogbn-arxiv|C7-I|32|0|OK||
|ogbn-arxiv|C1-J|32|0|OK||
|ogbn-arxiv|C1-H|32|0|OK||
|ogbn-arxiv|C5|32|0|OK||
|ogbn-arxiv|C5-U|32|0|OK||
|ogbn-arxiv|C8-METIS|32|0|OK||
|ogbn-arxiv|B0|64|0|OK||
|ogbn-arxiv|B1|64|0|OK||
|ogbn-arxiv|B-RCM-ref|64|0|OK||
|ogbn-arxiv|C9-Gorder|64|0|OK||
|ogbn-arxiv|C9-S|64|0|OK||
|ogbn-arxiv|C10-BP|64|0|OK||
|ogbn-arxiv|C2-LSH|64|0|OK||
|ogbn-arxiv|C3-W1|64|0|OK||
|ogbn-arxiv|C3-W4|64|0|OK||
|ogbn-arxiv|C4-U|64|0|OK||
|ogbn-arxiv|C4-T|64|0|OK||
|ogbn-arxiv|C7-I|64|0|OK||
|ogbn-arxiv|C1-J|64|0|OK||
|ogbn-arxiv|C1-H|64|0|OK||
|ogbn-arxiv|C5|64|0|OK||
|ogbn-arxiv|C5-U|64|0|OK||
|ogbn-arxiv|C8-METIS|64|0|OK||
|ogbn-arxiv|B0|128|0|OK||
|ogbn-arxiv|B1|128|0|OK||
|ogbn-arxiv|B-RCM-ref|128|0|OK||
|ogbn-arxiv|C9-Gorder|128|0|OK||
|ogbn-arxiv|C9-S|128|0|OK||
|ogbn-arxiv|C10-BP|128|0|OK||
|ogbn-arxiv|C2-LSH|128|0|OK||
|ogbn-arxiv|C3-W1|128|0|OK||
|ogbn-arxiv|C3-W4|128|0|OK||
|ogbn-arxiv|C4-U|128|0|OK||
|ogbn-arxiv|C4-T|128|0|OK||
|ogbn-arxiv|C7-I|128|0|OK||
|ogbn-arxiv|C1-J|128|0|OK||
|ogbn-arxiv|C1-H|128|0|OK||
|ogbn-arxiv|C5|128|0|OK||
|ogbn-arxiv|C5-U|128|0|OK||
|ogbn-arxiv|C8-METIS|128|0|OK||
|wiki-RfA|B0|32|0|OK||
|wiki-RfA|B1|32|0|OK||
|wiki-RfA|B-RCM-ref|32|0|OK||
|wiki-RfA|C9-Gorder|32|0|OK||
|wiki-RfA|C9-S|32|0|OK||
|wiki-RfA|C10-BP|32|0|OK||
|wiki-RfA|C2-LSH|32|0|OK||
|wiki-RfA|C3-W1|32|0|OK||
|wiki-RfA|C3-W4|32|0|OK||
|wiki-RfA|C4-U|32|0|OK||
|wiki-RfA|C4-T|32|0|OK||
|wiki-RfA|C7-I|32|0|OK||
|wiki-RfA|C1-J|32|0|OK||
|wiki-RfA|C1-H|32|0|OK||
|wiki-RfA|C5|32|0|OK||
|wiki-RfA|C5-U|32|0|OK||
|wiki-RfA|C8-METIS|32|0|OK||
|wiki-RfA|B0|64|0|OK||
|wiki-RfA|B1|64|0|OK||
|wiki-RfA|B-RCM-ref|64|0|OK||
|wiki-RfA|C9-Gorder|64|0|OK||
|wiki-RfA|C9-S|64|0|OK||
|wiki-RfA|C10-BP|64|0|OK||
|wiki-RfA|C2-LSH|64|0|OK||
|wiki-RfA|C3-W1|64|0|OK||
|wiki-RfA|C3-W4|64|0|OK||
|wiki-RfA|C4-U|64|0|OK||
|wiki-RfA|C4-T|64|0|OK||
|wiki-RfA|C7-I|64|0|OK||
|wiki-RfA|C1-J|64|0|OK||
|wiki-RfA|C1-H|64|0|OK||
|wiki-RfA|C5|64|0|OK||
|wiki-RfA|C5-U|64|0|OK||
|wiki-RfA|C8-METIS|64|0|OK||
|wiki-RfA|B0|128|0|OK||
|wiki-RfA|B1|128|0|OK||
|wiki-RfA|B-RCM-ref|128|0|OK||
|wiki-RfA|C9-Gorder|128|0|OK||
|wiki-RfA|C9-S|128|0|OK||
|wiki-RfA|C10-BP|128|0|OK||
|wiki-RfA|C2-LSH|128|0|OK||
|wiki-RfA|C3-W1|128|0|OK||
|wiki-RfA|C3-W4|128|0|OK||
|wiki-RfA|C4-U|128|0|OK||
|wiki-RfA|C4-T|128|0|OK||
|wiki-RfA|C7-I|128|0|OK||
|wiki-RfA|C1-J|128|0|OK||
|wiki-RfA|C1-H|128|0|OK||
|wiki-RfA|C5|128|0|OK||
|wiki-RfA|C5-U|128|0|OK||
|wiki-RfA|C8-METIS|128|0|OK||
|dawson5|B0|32|0|OK||
|dawson5|B1|32|0|OK||
|dawson5|B-RCM-ref|32|0|OK||
|dawson5|C9-Gorder|32|0|OK||
|dawson5|C9-S|32|0|OK||
|dawson5|C10-BP|32|0|OK||
|dawson5|C2-LSH|32|0|OK||
|dawson5|C3-W1|32|0|OK||
|dawson5|C3-W4|32|0|OK||
|dawson5|C4-U|32|0|OK||
|dawson5|C4-T|32|0|OK||
|dawson5|C7-I|32|0|OK||
|dawson5|C1-J|32|0|OK||
|dawson5|C1-H|32|0|OK||
|dawson5|C5|32|0|OK||
|dawson5|C5-U|32|0|OK||
|dawson5|C8-METIS|32|0|OK||
|dawson5|B0|64|0|OK||
|dawson5|B1|64|0|OK||
|dawson5|B-RCM-ref|64|0|OK||
|dawson5|C9-Gorder|64|0|OK||
|dawson5|C9-S|64|0|OK||
|dawson5|C10-BP|64|0|OK||
|dawson5|C2-LSH|64|0|OK||
|dawson5|C3-W1|64|0|OK||
|dawson5|C3-W4|64|0|OK||
|dawson5|C4-U|64|0|OK||
|dawson5|C4-T|64|0|OK||
|dawson5|C7-I|64|0|OK||
|dawson5|C1-J|64|0|OK||
|dawson5|C1-H|64|0|OK||
|dawson5|C5|64|0|OK||
|dawson5|C5-U|64|0|OK||
|dawson5|C8-METIS|64|0|OK||
|dawson5|B0|128|0|OK||
|dawson5|B1|128|0|OK||
|dawson5|B-RCM-ref|128|0|OK||
|dawson5|C9-Gorder|128|0|OK||
|dawson5|C9-S|128|0|OK||
|dawson5|C10-BP|128|0|OK||
|dawson5|C2-LSH|128|0|OK||
|dawson5|C3-W1|128|0|OK||
|dawson5|C3-W4|128|0|OK||
|dawson5|C4-U|128|0|OK||
|dawson5|C4-T|128|0|OK||
|dawson5|C7-I|128|0|OK||
|dawson5|C1-J|128|0|OK||
|dawson5|C1-H|128|0|OK||
|dawson5|C5|128|0|OK||
|dawson5|C5-U|128|0|OK||
|dawson5|C8-METIS|128|0|OK||
|reddit|B0|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE; post-E tau153: actual method timeout, queue excluded; post-E: actual method timeout, queue excluded; exit code 124|
|reddit|B1|16|0|OK||
|reddit|B-RCM-ref|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE|
|reddit|rabbit-pilot|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE|
|reddit|neutron-pilot|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE|
|reddit|C9-Gorder|16|0|OK||
|reddit|C9-S|16|0|INCOMPLETE|post-E tau153: P-LS stop condition completed; post-layout evaluation: actual method timeout, queue excluded; post-E tau53: actual method timeout, queue excluded|
|reddit|C10-BP|16|0|OK||
|reddit|C2-LSH|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE; post-E tau153: P-LS stop condition completed; post-layout evaluation: incomplete; post-E: actual method timeout, queue excluded; exit code 124|
|reddit|C3-W1|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE; post-E tau153: P-LS stop condition completed; post-layout evaluation: incomplete; post-E: actual method timeout, queue excluded; exit code 124|
|reddit|C3-W4|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE; post-E tau153: P-LS stop condition completed; post-layout evaluation: incomplete; post-E: actual method timeout, queue excluded; exit code 124|
|reddit|C4-U|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE; post-E: actual method timeout, queue excluded; exit code 124|
|reddit|C4-T|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE; post-E tau153: P-LS stop condition completed; post-layout evaluation: incomplete; post-E: actual method timeout, queue excluded; exit code 124|
|reddit|C7-I|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE; post-E: actual method timeout, queue excluded; exit code 124|
|reddit|C1-J|16|0|OK||
|reddit|C1-H|16|0|INCOMPLETE|post-E tau153: P-LS stop condition completed; post-layout evaluation: incomplete|
|reddit|C5|16|0|OK||
|reddit|C5-U|16|0|OK||
|reddit|C8-METIS|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE; post-E: actual method timeout, queue excluded; exit code 124; post-E: post-E controller ended before final record|
|reddit|C3-A|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE|
|reddit|C3-W4-noP|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE|
|reddit|C3-W4-R|16|0|OK||
|reddit|C3-A-R|16|0|OK||
|reddit|C4-U-R|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE|
|reddit|C4-T-R|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE|
|reddit|C7-I-R|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE|
|reddit|C5-CN|16|0|OK||
|reddit|C5-U-CN|16|0|OK||
|reddit|C6-HP|16|0|INCOMPLETE|actual method timeout, queue excluded; generator exited/terminated before a final order record; see generation_command; last completed preparation phase: partitioning|
|reddit|C6-RB (T21 口径)|16|0|SKIPPED|dispatch requires frozen T21 C6-RB/M orders, unavailable for second-batch matrices; no rerun under T21 label|
|reddit|C6-M mnc=1 (T21 口径)|16|0|SKIPPED|dispatch requires frozen T21 C6-RB/M orders, unavailable for second-batch matrices; no rerun under T21 label|
|reddit|C6-M mnc=4 (T21 口径)|16|0|SKIPPED|dispatch requires frozen T21 C6-RB/M orders, unavailable for second-batch matrices; no rerun under T21 label|
|reddit|C6-M mnc=16 (T21 口径)|16|0|SKIPPED|dispatch requires frozen T21 C6-RB/M orders, unavailable for second-batch matrices; no rerun under T21 label|
|ogbn-products|B0|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE; post-E tau2: LS exact workspace preflight estimate 180695009260 bytes exceeds frozen 8GiB safety budget; post-E tau3: LS exact workspace preflight estimate 174717828430 bytes exceeds frozen 8GiB safety budget|
|ogbn-products|B1|16|0|INCOMPLETE|post-E tau2: LS exact workspace preflight estimate 180695009260 bytes exceeds frozen 8GiB safety budget; post-E tau3: LS exact workspace preflight estimate 174717828430 bytes exceeds frozen 8GiB safety budget|
|ogbn-products|B-RCM-ref|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE|
|ogbn-products|rabbit-pilot|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE|
|ogbn-products|neutron-pilot|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE|
|ogbn-products|C9-Gorder|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE; post-E tau2: LS exact workspace preflight estimate 180695009260 bytes exceeds frozen 8GiB safety budget; post-E tau3: LS exact workspace preflight estimate 174717828430 bytes exceeds frozen 8GiB safety budget|
|ogbn-products|C9-S|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE; post-E tau2: LS exact workspace preflight estimate 180695009260 bytes exceeds frozen 8GiB safety budget; post-E tau3: LS exact workspace preflight estimate 174717828430 bytes exceeds frozen 8GiB safety budget|
|ogbn-products|C10-BP|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE; post-E tau2: LS exact workspace preflight estimate 180695009260 bytes exceeds frozen 8GiB safety budget; post-E tau3: LS exact workspace preflight estimate 174717828430 bytes exceeds frozen 8GiB safety budget|
|ogbn-products|C2-LSH|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE; post-E tau2: LS exact workspace preflight estimate 180695009260 bytes exceeds frozen 8GiB safety budget; post-E tau3: LS exact workspace preflight estimate 174717828430 bytes exceeds frozen 8GiB safety budget|
|ogbn-products|C3-W1|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE; post-E tau2: LS exact workspace preflight estimate 180695009260 bytes exceeds frozen 8GiB safety budget; post-E tau3: LS exact workspace preflight estimate 174717828430 bytes exceeds frozen 8GiB safety budget|
|ogbn-products|C3-W4|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE; post-E tau2: LS exact workspace preflight estimate 180695009260 bytes exceeds frozen 8GiB safety budget; post-E tau3: LS exact workspace preflight estimate 174717828430 bytes exceeds frozen 8GiB safety budget|
|ogbn-products|C4-U|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE; post-E tau2: LS exact workspace preflight estimate 180695009260 bytes exceeds frozen 8GiB safety budget; post-E tau3: LS exact workspace preflight estimate 174717828430 bytes exceeds frozen 8GiB safety budget|
|ogbn-products|C4-T|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE; post-E tau2: LS exact workspace preflight estimate 180695009260 bytes exceeds frozen 8GiB safety budget; post-E tau3: LS exact workspace preflight estimate 174717828430 bytes exceeds frozen 8GiB safety budget|
|ogbn-products|C7-I|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE; post-E tau2: LS exact workspace preflight estimate 180695009260 bytes exceeds frozen 8GiB safety budget; post-E tau3: LS exact workspace preflight estimate 174717828430 bytes exceeds frozen 8GiB safety budget|
|ogbn-products|C1-J|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE; post-E tau2: LS exact workspace preflight estimate 180695009260 bytes exceeds frozen 8GiB safety budget; post-E tau3: LS exact workspace preflight estimate 174717828430 bytes exceeds frozen 8GiB safety budget|
|ogbn-products|C1-H|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE; post-E tau2: LS exact workspace preflight estimate 180695009260 bytes exceeds frozen 8GiB safety budget; post-E tau3: LS exact workspace preflight estimate 174717828430 bytes exceeds frozen 8GiB safety budget|
|ogbn-products|C5|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE; post-E tau2: LS exact workspace preflight estimate 180695009260 bytes exceeds frozen 8GiB safety budget; post-E tau3: LS exact workspace preflight estimate 174717828430 bytes exceeds frozen 8GiB safety budget|
|ogbn-products|C5-U|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE; post-E tau2: LS exact workspace preflight estimate 180695009260 bytes exceeds frozen 8GiB safety budget; post-E tau3: LS exact workspace preflight estimate 174717828430 bytes exceeds frozen 8GiB safety budget|
|ogbn-products|C8-METIS|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE; post-E tau2: LS exact workspace preflight estimate 180695009260 bytes exceeds frozen 8GiB safety budget; post-E tau3: LS exact workspace preflight estimate 174717828430 bytes exceeds frozen 8GiB safety budget|
|ogbn-products|C3-A|16|0|INCOMPLETE|actual method timeout, queue excluded; generator exited/terminated before a final order record; see generation_command|
|ogbn-products|C3-W4-noP|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE|
|ogbn-products|C3-W4-R|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE|
|ogbn-products|C3-A-R|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE|
|ogbn-products|C4-U-R|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE|
|ogbn-products|C4-T-R|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE|
|ogbn-products|C7-I-R|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE|
|ogbn-products|C5-CN|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE|
|ogbn-products|C5-U-CN|16|0|INCOMPLETE|co pair map exceeds 8GiB workspace safety budget estimate; INCOMPLETE|
|ogbn-products|C6-HP|16|0|INCOMPLETE|generator exit code -9; generator exited/terminated before a final order record; see generation_command; last completed preparation phase: constructing hypergraph|
|ogbn-products|C6-RB (T21 口径)|16|0|SKIPPED|dispatch requires frozen T21 C6-RB/M orders, unavailable for second-batch matrices; no rerun under T21 label|
|ogbn-products|C6-M mnc=1 (T21 口径)|16|0|SKIPPED|dispatch requires frozen T21 C6-RB/M orders, unavailable for second-batch matrices; no rerun under T21 label|
|ogbn-products|C6-M mnc=4 (T21 口径)|16|0|SKIPPED|dispatch requires frozen T21 C6-RB/M orders, unavailable for second-batch matrices; no rerun under T21 label|
|ogbn-products|C6-M mnc=16 (T21 口径)|16|0|SKIPPED|dispatch requires frozen T21 C6-RB/M orders, unavailable for second-batch matrices; no rerun under T21 label|
|mycielskian15|B0|16|0|SKIPPED|official TAMU403; files-server TLS timeout; UF official fallback404; see secondbatch input logs|
|mycielskian15|B1|16|0|SKIPPED|official TAMU403; files-server TLS timeout; UF official fallback404; see secondbatch input logs|
|mycielskian15|B-RCM-ref|16|0|SKIPPED|official TAMU403; files-server TLS timeout; UF official fallback404; see secondbatch input logs|
|mycielskian15|rabbit-pilot|16|0|SKIPPED|official TAMU403; files-server TLS timeout; UF official fallback404; see secondbatch input logs|
|mycielskian15|neutron-pilot|16|0|SKIPPED|official TAMU403; files-server TLS timeout; UF official fallback404; see secondbatch input logs|
|mycielskian15|C9-Gorder|16|0|SKIPPED|official TAMU403; files-server TLS timeout; UF official fallback404; see secondbatch input logs|
|mycielskian15|C9-S|16|0|SKIPPED|official TAMU403; files-server TLS timeout; UF official fallback404; see secondbatch input logs|
|mycielskian15|C10-BP|16|0|SKIPPED|official TAMU403; files-server TLS timeout; UF official fallback404; see secondbatch input logs|
|mycielskian15|C2-LSH|16|0|SKIPPED|official TAMU403; files-server TLS timeout; UF official fallback404; see secondbatch input logs|
|mycielskian15|C3-W1|16|0|SKIPPED|official TAMU403; files-server TLS timeout; UF official fallback404; see secondbatch input logs|
|mycielskian15|C3-W4|16|0|SKIPPED|official TAMU403; files-server TLS timeout; UF official fallback404; see secondbatch input logs|
|mycielskian15|C4-U|16|0|SKIPPED|official TAMU403; files-server TLS timeout; UF official fallback404; see secondbatch input logs|
|mycielskian15|C4-T|16|0|SKIPPED|official TAMU403; files-server TLS timeout; UF official fallback404; see secondbatch input logs|
|mycielskian15|C7-I|16|0|SKIPPED|official TAMU403; files-server TLS timeout; UF official fallback404; see secondbatch input logs|
|mycielskian15|C1-J|16|0|SKIPPED|official TAMU403; files-server TLS timeout; UF official fallback404; see secondbatch input logs|
|mycielskian15|C1-H|16|0|SKIPPED|official TAMU403; files-server TLS timeout; UF official fallback404; see secondbatch input logs|
|mycielskian15|C5|16|0|SKIPPED|official TAMU403; files-server TLS timeout; UF official fallback404; see secondbatch input logs|
|mycielskian15|C5-U|16|0|SKIPPED|official TAMU403; files-server TLS timeout; UF official fallback404; see secondbatch input logs|
|mycielskian15|C8-METIS|16|0|SKIPPED|official TAMU403; files-server TLS timeout; UF official fallback404; see secondbatch input logs|
|mycielskian15|C3-A|16|0|SKIPPED|official TAMU403; files-server TLS timeout; UF official fallback404; see secondbatch input logs|
|mycielskian15|C3-W4-noP|16|0|SKIPPED|official TAMU403; files-server TLS timeout; UF official fallback404; see secondbatch input logs|
|mycielskian15|C3-W4-R|16|0|SKIPPED|official TAMU403; files-server TLS timeout; UF official fallback404; see secondbatch input logs|
|mycielskian15|C3-A-R|16|0|SKIPPED|official TAMU403; files-server TLS timeout; UF official fallback404; see secondbatch input logs|
|mycielskian15|C4-U-R|16|0|SKIPPED|official TAMU403; files-server TLS timeout; UF official fallback404; see secondbatch input logs|
|mycielskian15|C4-T-R|16|0|SKIPPED|official TAMU403; files-server TLS timeout; UF official fallback404; see secondbatch input logs|
|mycielskian15|C7-I-R|16|0|SKIPPED|official TAMU403; files-server TLS timeout; UF official fallback404; see secondbatch input logs|
|mycielskian15|C5-CN|16|0|SKIPPED|official TAMU403; files-server TLS timeout; UF official fallback404; see secondbatch input logs|
|mycielskian15|C5-U-CN|16|0|SKIPPED|official TAMU403; files-server TLS timeout; UF official fallback404; see secondbatch input logs|
|mycielskian15|C6-HP|16|0|SKIPPED|official TAMU403; files-server TLS timeout; UF official fallback404; see secondbatch input logs|
|mycielskian15|C6-RB (T21 口径)|16|0|SKIPPED|official TAMU403; files-server TLS timeout; UF official fallback404; see secondbatch input logs|
|mycielskian15|C6-M mnc=1 (T21 口径)|16|0|SKIPPED|official TAMU403; files-server TLS timeout; UF official fallback404; see secondbatch input logs|
|mycielskian15|C6-M mnc=4 (T21 口径)|16|0|SKIPPED|official TAMU403; files-server TLS timeout; UF official fallback404; see secondbatch input logs|
|mycielskian15|C6-M mnc=16 (T21 口径)|16|0|SKIPPED|official TAMU403; files-server TLS timeout; UF official fallback404; see secondbatch input logs|
|reddit|B-RSH-ref|16|0|SKIPPED|T4/T2 reference dependency unavailable; optional by dispatch, not part of409core cases|
|reddit|B-Neutron-ref|16|0|SKIPPED|T4/T2 reference dependency unavailable; optional by dispatch, not part of409core cases|
|ogbn-products|B-RSH-ref|16|0|SKIPPED|T4/T2 reference dependency unavailable; optional by dispatch, not part of409core cases|
|ogbn-products|B-Neutron-ref|16|0|SKIPPED|T4/T2 reference dependency unavailable; optional by dispatch, not part of409core cases|
|mycielskian15|B-RSH-ref|16|0|SKIPPED|T4/T2 reference dependency unavailable; optional by dispatch, not part of409core cases|
|mycielskian15|B-Neutron-ref|16|0|SKIPPED|T4/T2 reference dependency unavailable; optional by dispatch, not part of409core cases|
