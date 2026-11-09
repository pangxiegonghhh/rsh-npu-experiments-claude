# T23 阶段1–2：round1-compare-20261106

CPU 结构实验；基准提交 3ecc8f4ae0f6a7dff556fe1ad4e888a500f3162b，树 54dd7a113c4ecad145e07b47d8745f9de7d56756。仓库原有 263 个文件哈希均未变，未提交、未推送。

已覆盖 157 个 W16 行序评估例（主种子与波动例），224 个后处理例。逐项状态见 status.csv；各 τ 实算值与原始输入来源、显式零数见 manifest.json。

复用行序引用 68 个；新行序文件 313 个、合计 84159617 B。新行序超过50 MiB时按派发仅留本地，逐文件路径与SHA-256见 orders-manifest.json。

T21、T22、T23参考自检、八个官方行序SHA、40行评价网格、外部工具同种子重复及每张矩阵三行序独立核对均见 logs。

Rabbit 使用原作者锁定提交、Linux ARM、Boost1.58、gperftools2.16、单线程。作者无种子接口，1/2标记为确定性重复，不伪装成不同随机种子。PyNNDescent、METIS环境与编译选项见 manifest.json 和日志。

co_chain 守卫：窗口涉及残余点超过400时跳过该窗口的co计数。guard-counts.csv逐条件列出实际触发窗口数；不同成员、窗口宽度与来源分别记账。

时序与故障：空字符串种子错误的T22临时数据已隔离；队列存活探测的启动错误已保存并补齐未启动项。T23已复用T21的P-LS输出，其重复验证副本不计入主新行序。日志保留原始证据。

RSH和rabbit/neutron先导版按原名称/基线记账；历史先导参照不参加排名。B-RCM-ref只供带状矩阵排名。wiki-RfA为指定重建版，B0和P11的ΣR/ΣU只作参考。

未写研究分析结论。阶段3单独交回，不修改本目录。

## τ 与显式零值

|matrix|τ规则和值|显式零条目|
|---|---|---|
|cora|fixed=2, fixed=3|0|
|wiki-RfA|fixed=2, fixed=3|11493|
|olafu|q20=53, q40=56|0|
|dawson5|q20=15, q40=17|0|
|human_gene1|q20=82, q40=342|0|
|pattern1|q20=8, q40=757|0|
|ogbn-arxiv|fixed=2, fixed=3|0|

## co_chain守卫触发

每个条件的计数见 guard-counts.csv。下表仅汇总tail-co调用；累计值按条件相加，未对窗口去重。

|matrix|tau|条件数|单条件最小|单条件最大|累计跳过窗口数|
|---|---|---|---|---|---|
|cora|2|188|0|0|0|
|cora|3|188|0|0|0|
|wiki-RfA|2|140|0|0|0|
|wiki-RfA|3|140|0|0|0|
|olafu|53|140|0|0|0|
|olafu|56|140|0|0|0|
|dawson5|15|140|0|0|0|
|dawson5|17|140|0|0|0|
|human_gene1|82|140|0|3|224|
|human_gene1|342|140|278|788|57460|
|pattern1|8|140|2|12|744|
|pattern1|757|140|34|520|20444|
|ogbn-arxiv|2|188|0|1|80|
|ogbn-arxiv|3|188|1|3|316|

## 矩阵 × 方法状态

|matrix|member|status|reason|
|---|---|---|---|
|cora|B0|OK||
|cora|B1|OK||
|cora|B-RCM-ref|OK||
|cora|rabbit-pilot|OK||
|cora|neutron-pilot|OK||
|cora|C9-Gorder|OK||
|cora|C9-S|OK||
|cora|C10-BP|OK||
|cora|C2-LSH|OK||
|cora|C3-W1|OK||
|cora|C3-W4|OK||
|cora|C4-U|OK||
|cora|C4-T|OK||
|cora|C7-I|OK||
|cora|C1-J|OK||
|cora|C1-H|OK||
|cora|C5|OK||
|cora|C5-U|OK||
|cora|C8-METIS|OK||
|cora|B-RSH-ref|SKIPPED|T4/T2 reference dependency not available; optional by plan|
|cora|B-Neutron-ref|SKIPPED|T4/T2 reference dependency not available; optional by plan|
|ogbn-arxiv|B0|OK||
|ogbn-arxiv|B1|OK||
|ogbn-arxiv|B-RCM-ref|OK||
|ogbn-arxiv|rabbit-pilot|OK||
|ogbn-arxiv|neutron-pilot|OK||
|ogbn-arxiv|C9-Gorder|OK||
|ogbn-arxiv|C9-S|OK||
|ogbn-arxiv|C10-BP|OK||
|ogbn-arxiv|C2-LSH|OK||
|ogbn-arxiv|C3-W1|OK||
|ogbn-arxiv|C3-W4|OK||
|ogbn-arxiv|C4-U|OK||
|ogbn-arxiv|C4-T|OK||
|ogbn-arxiv|C7-I|OK||
|ogbn-arxiv|C1-J|OK||
|ogbn-arxiv|C1-H|OK||
|ogbn-arxiv|C5|OK||
|ogbn-arxiv|C5-U|OK||
|ogbn-arxiv|C8-METIS|OK||
|ogbn-arxiv|B-RSH-ref|SKIPPED|T4/T2 reference dependency not available; optional by plan|
|ogbn-arxiv|B-Neutron-ref|SKIPPED|T4/T2 reference dependency not available; optional by plan|
|wiki-RfA|B0|OK||
|wiki-RfA|B1|OK||
|wiki-RfA|B-RCM-ref|OK||
|wiki-RfA|rabbit-pilot|OK||
|wiki-RfA|neutron-pilot|OK||
|wiki-RfA|C9-Gorder|OK||
|wiki-RfA|C9-S|OK||
|wiki-RfA|C10-BP|OK||
|wiki-RfA|C2-LSH|OK||
|wiki-RfA|C3-W1|OK||
|wiki-RfA|C3-W4|OK||
|wiki-RfA|C4-U|OK||
|wiki-RfA|C4-T|OK||
|wiki-RfA|C7-I|OK||
|wiki-RfA|C1-J|OK||
|wiki-RfA|C1-H|OK||
|wiki-RfA|C5|OK||
|wiki-RfA|C5-U|OK||
|wiki-RfA|C8-METIS|OK||
|wiki-RfA|B-RSH-ref|SKIPPED|T4/T2 reference dependency not available; optional by plan|
|wiki-RfA|B-Neutron-ref|SKIPPED|T4/T2 reference dependency not available; optional by plan|
|dawson5|B0|OK||
|dawson5|B1|OK||
|dawson5|B-RCM-ref|OK||
|dawson5|rabbit-pilot|OK||
|dawson5|neutron-pilot|OK||
|dawson5|C9-Gorder|OK||
|dawson5|C9-S|OK||
|dawson5|C10-BP|OK||
|dawson5|C2-LSH|OK||
|dawson5|C3-W1|OK||
|dawson5|C3-W4|OK||
|dawson5|C4-U|OK||
|dawson5|C4-T|OK||
|dawson5|C7-I|OK||
|dawson5|C1-J|OK||
|dawson5|C1-H|OK||
|dawson5|C5|OK||
|dawson5|C5-U|OK||
|dawson5|C8-METIS|OK||
|dawson5|B-RSH-ref|SKIPPED|T4/T2 reference dependency not available; optional by plan|
|dawson5|B-Neutron-ref|SKIPPED|T4/T2 reference dependency not available; optional by plan|
|olafu|B0|OK||
|olafu|B1|OK||
|olafu|B-RCM-ref|OK||
|olafu|rabbit-pilot|OK||
|olafu|neutron-pilot|OK||
|olafu|C9-Gorder|OK||
|olafu|C9-S|OK||
|olafu|C10-BP|OK||
|olafu|C2-LSH|OK||
|olafu|C3-W1|OK||
|olafu|C3-W4|OK||
|olafu|C4-U|OK||
|olafu|C4-T|OK||
|olafu|C7-I|OK||
|olafu|C1-J|OK||
|olafu|C1-H|OK||
|olafu|C5|OK||
|olafu|C5-U|OK||
|olafu|C8-METIS|OK||
|olafu|B-RSH-ref|SKIPPED|T4/T2 reference dependency not available; optional by plan|
|olafu|B-Neutron-ref|SKIPPED|T4/T2 reference dependency not available; optional by plan|
|pattern1|B0|OK||
|pattern1|B1|OK||
|pattern1|B-RCM-ref|OK||
|pattern1|rabbit-pilot|OK||
|pattern1|neutron-pilot|OK||
|pattern1|C9-Gorder|OK||
|pattern1|C9-S|OK||
|pattern1|C10-BP|OK||
|pattern1|C2-LSH|OK||
|pattern1|C3-W1|OK||
|pattern1|C3-W4|OK||
|pattern1|C4-U|OK||
|pattern1|C4-T|OK||
|pattern1|C7-I|OK||
|pattern1|C1-J|OK||
|pattern1|C1-H|OK||
|pattern1|C5|OK||
|pattern1|C5-U|OK||
|pattern1|C8-METIS|OK||
|pattern1|B-RSH-ref|SKIPPED|T4/T2 reference dependency not available; optional by plan|
|pattern1|B-Neutron-ref|SKIPPED|T4/T2 reference dependency not available; optional by plan|
|human_gene1|B0|OK||
|human_gene1|B1|OK||
|human_gene1|B-RCM-ref|OK||
|human_gene1|rabbit-pilot|OK||
|human_gene1|neutron-pilot|OK||
|human_gene1|C9-Gorder|OK||
|human_gene1|C9-S|OK||
|human_gene1|C10-BP|OK||
|human_gene1|C2-LSH|OK||
|human_gene1|C3-W1|OK||
|human_gene1|C3-W4|OK||
|human_gene1|C4-U|OK||
|human_gene1|C4-T|OK||
|human_gene1|C7-I|OK||
|human_gene1|C1-J|OK||
|human_gene1|C1-H|OK||
|human_gene1|C5|OK||
|human_gene1|C5-U|OK||
|human_gene1|C8-METIS|OK||
|human_gene1|B-RSH-ref|SKIPPED|T4/T2 reference dependency not available; optional by plan|
|human_gene1|B-Neutron-ref|SKIPPED|T4/T2 reference dependency not available; optional by plan|
