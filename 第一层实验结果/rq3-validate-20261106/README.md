# T22 RQ3 验证实验

CPU实验；提交 3ecc8f4ae0f6a7dff556fe1ad4e888a500f3162b，树 54dd7a113c4ecad145e07b47d8745f9de7d56756；原有263个文件哈希未变。未提交、未推送。

170个条件单元、4012行结果、182条P-LS记录；四数表340行、Kendall168行、跨τ112行。逐项状态见status.csv。复用113条行序引用；新生成312个文件，共68435536字节。超过50MiB的新行序按派发仅留本地，路径和SHA见orders-manifest.json。

M1的inplace保留原窗口再删除残余成员；M5的inplace是在保留编号位置放置残余，因此其T等于keep。两者按方案分别记录。

原始seed空字符串错误数据已隔离，队列启动失败、原版gap内存守卫失败均保留。只补齐未成功条件；gap使用经过逐项等值自检的打包端口表示。方法标签从原始来源记录规范化，未重算数值。

co_chain单窗口涉及残余点>400时跳过该窗口co计数，规则保持。完整逐条件计数见guard-counts.csv。

T21/T22参考复现、移植等值、独立复核、复用P-LS不变量检查见logs。未写分析结论。

M2：pattern1、human_gene1采用方案允许的7个偶数切口{2,4,6,8,10,12,14}；其余W16采用1至15，W32/64采用1至W−1。实际切口逐项记录在four_numbers.csv的offsets_used。

## τ和显式零

|matrix|τ|显式零条目|
|---|---|---|
|cora|fixed=2, fixed=3|0|
|wiki-RfA|fixed=2, fixed=3|11493|
|olafu|q20=53, q40=56|0|
|dawson5|q20=15, q40=17|0|
|human_gene1|q20=82, q40=342|0|
|pattern1|q20=8, q40=757|0|
|ogbn-arxiv|fixed=2, fixed=3|0|

## co_chain守卫

累计值为条件计数求和，不代表去重窗口数。

|matrix|tau|有计数条件数|单条件最小|单条件最大|累计|
|---|---|---|---|---|---|
|cora|2|365|0|0|0|
|cora|3|365|0|0|0|
|wiki-RfA|2|269|0|0|0|
|wiki-RfA|3|269|0|0|0|
|olafu|53|237|0|0|0|
|olafu|56|237|0|0|0|
|dawson5|15|237|0|0|0|
|dawson5|17|237|0|0|0|
|human_gene1|82|237|0|4|102|
|human_gene1|342|237|0|788|21167|
|pattern1|8|237|0|12|266|
|pattern1|757|223|0|521|8342|
|ogbn-arxiv|2|353|0|2|66|
|ogbn-arxiv|3|353|0|5|162|

## 矩阵 × 方法状态

|matrix|member|W|tau|status|reason|
|---|---|---|---|---|---|
|cora|B0|16|2|OK||
|cora|B0|16|3|OK||
|cora|rsh-α0|16|2|OK||
|cora|rsh-α0|16|3|OK||
|cora|rabbit-pilot|16|2|OK||
|cora|rabbit-pilot|16|3|OK||
|cora|neutron-pilot|16|2|OK||
|cora|neutron-pilot|16|3|OK||
|cora|C9-Gorder|16|2|OK||
|cora|C9-Gorder|16|3|OK||
|cora|C9-S|16|2|OK||
|cora|C9-S|16|3|OK||
|cora|C10-BP|16|2|OK||
|cora|C10-BP|16|3|OK||
|cora|B-RCM-ref|16|2|OK||
|cora|B-RCM-ref|16|3|OK||
|cora|SlashBurn|16|2|OK||
|cora|SlashBurn|16|3|OK||
|cora|LS-full(C9-Gorder)|16|2|OK||
|cora|LS-full(C9-Gorder)|16|3|OK||
|cora|LS-full(rsh-α0)|16|2|OK||
|cora|LS-full(rsh-α0)|16|3|OK||
|wiki-RfA|B0|16|2|OK||
|wiki-RfA|B0|16|3|OK||
|wiki-RfA|rsh-α0|16|2|OK||
|wiki-RfA|rsh-α0|16|3|OK||
|wiki-RfA|rabbit-pilot|16|2|OK||
|wiki-RfA|rabbit-pilot|16|3|OK||
|wiki-RfA|neutron-pilot|16|2|OK||
|wiki-RfA|neutron-pilot|16|3|OK||
|wiki-RfA|C9-Gorder|16|2|OK||
|wiki-RfA|C9-Gorder|16|3|OK||
|wiki-RfA|C9-S|16|2|OK||
|wiki-RfA|C9-S|16|3|OK||
|wiki-RfA|C10-BP|16|2|OK||
|wiki-RfA|C10-BP|16|3|OK||
|wiki-RfA|B-RCM-ref|16|2|OK||
|wiki-RfA|B-RCM-ref|16|3|OK||
|wiki-RfA|SlashBurn|16|2|OK||
|wiki-RfA|SlashBurn|16|3|OK||
|wiki-RfA|LS-full(C9-Gorder)|16|2|OK||
|wiki-RfA|LS-full(C9-Gorder)|16|3|OK||
|wiki-RfA|LS-full(rsh-α0)|16|2|OK||
|wiki-RfA|LS-full(rsh-α0)|16|3|OK||
|olafu|B0|16|53|OK||
|olafu|B0|16|56|OK||
|olafu|rsh-α0|16|53|OK||
|olafu|rsh-α0|16|56|OK||
|olafu|rabbit-pilot|16|53|OK||
|olafu|rabbit-pilot|16|56|OK||
|olafu|neutron-pilot|16|53|OK||
|olafu|neutron-pilot|16|56|OK||
|olafu|C9-Gorder|16|53|OK||
|olafu|C9-Gorder|16|56|OK||
|olafu|C9-S|16|53|OK||
|olafu|C9-S|16|56|OK||
|olafu|C10-BP|16|53|OK||
|olafu|C10-BP|16|56|OK||
|olafu|B-RCM-ref|16|53|OK||
|olafu|B-RCM-ref|16|56|OK||
|olafu|SlashBurn|16|53|OK||
|olafu|SlashBurn|16|56|OK||
|dawson5|B0|16|15|OK||
|dawson5|B0|16|17|OK||
|dawson5|rsh-α0|16|15|OK||
|dawson5|rsh-α0|16|17|OK||
|dawson5|rabbit-pilot|16|15|OK||
|dawson5|rabbit-pilot|16|17|OK||
|dawson5|neutron-pilot|16|15|OK||
|dawson5|neutron-pilot|16|17|OK||
|dawson5|C9-Gorder|16|15|OK||
|dawson5|C9-Gorder|16|17|OK||
|dawson5|C9-S|16|15|OK||
|dawson5|C9-S|16|17|OK||
|dawson5|C10-BP|16|15|OK||
|dawson5|C10-BP|16|17|OK||
|dawson5|B-RCM-ref|16|15|OK||
|dawson5|B-RCM-ref|16|17|OK||
|dawson5|SlashBurn|16|15|OK||
|dawson5|SlashBurn|16|17|OK||
|human_gene1|B0|16|82|OK||
|human_gene1|B0|16|342|OK||
|human_gene1|rsh-α0|16|82|OK||
|human_gene1|rsh-α0|16|342|OK||
|human_gene1|rabbit-pilot|16|82|OK||
|human_gene1|rabbit-pilot|16|342|OK||
|human_gene1|neutron-pilot|16|82|OK||
|human_gene1|neutron-pilot|16|342|OK||
|human_gene1|C9-Gorder|16|82|OK||
|human_gene1|C9-Gorder|16|342|OK||
|human_gene1|C9-S|16|82|OK||
|human_gene1|C9-S|16|342|OK||
|human_gene1|C10-BP|16|82|OK||
|human_gene1|C10-BP|16|342|OK||
|human_gene1|B-RCM-ref|16|82|OK||
|human_gene1|B-RCM-ref|16|342|OK||
|human_gene1|SlashBurn|16|82|OK||
|human_gene1|SlashBurn|16|342|OK||
|pattern1|B0|16|8|OK||
|pattern1|B0|16|757|OK||
|pattern1|rsh-α0|16|8|OK||
|pattern1|rsh-α0|16|757|OK||
|pattern1|rabbit-pilot|16|8|OK||
|pattern1|rabbit-pilot|16|757|OK||
|pattern1|neutron-pilot|16|8|OK||
|pattern1|neutron-pilot|16|757|OK||
|pattern1|C9-Gorder|16|8|OK||
|pattern1|C9-Gorder|16|757|OK||
|pattern1|C9-S|16|8|OK||
|pattern1|C9-S|16|757|OK||
|pattern1|C10-BP|16|8|OK||
|pattern1|C10-BP|16|757|OK||
|pattern1|B-RCM-ref|16|8|OK||
|pattern1|B-RCM-ref|16|757|OK||
|pattern1|SlashBurn|16|8|OK||
|pattern1|SlashBurn|16|757|OK||
|ogbn-arxiv|B0|16|2|OK||
|ogbn-arxiv|B0|16|3|OK||
|ogbn-arxiv|rsh-α0|16|2|OK||
|ogbn-arxiv|rsh-α0|16|3|OK||
|ogbn-arxiv|rabbit-pilot|16|2|OK||
|ogbn-arxiv|rabbit-pilot|16|3|OK||
|ogbn-arxiv|neutron-pilot|16|2|OK||
|ogbn-arxiv|neutron-pilot|16|3|OK||
|ogbn-arxiv|C9-Gorder|16|2|OK||
|ogbn-arxiv|C9-Gorder|16|3|OK||
|ogbn-arxiv|C9-S|16|2|OK||
|ogbn-arxiv|C9-S|16|3|OK||
|ogbn-arxiv|C10-BP|16|2|OK||
|ogbn-arxiv|C10-BP|16|3|OK||
|ogbn-arxiv|B-RCM-ref|16|2|OK||
|ogbn-arxiv|B-RCM-ref|16|3|OK||
|ogbn-arxiv|SlashBurn|16|2|OK||
|ogbn-arxiv|SlashBurn|16|3|OK||
|ogbn-arxiv|LS-full(C9-Gorder)|16|2|OK||
|ogbn-arxiv|LS-full(C9-Gorder)|16|3|OK||
|ogbn-arxiv|LS-full(rsh-α0)|16|2|OK||
|ogbn-arxiv|LS-full(rsh-α0)|16|3|OK||
|cora|B0|32|2|OK||
|cora|B0|32|3|OK||
|cora|rsh-α0|32|2|OK||
|cora|rsh-α0|32|3|OK||
|cora|C9-Gorder|32|2|OK||
|cora|C9-Gorder|32|3|OK||
|cora|C10-BP|32|2|OK||
|cora|C10-BP|32|3|OK||
|cora|B0|64|2|OK||
|cora|B0|64|3|OK||
|cora|rsh-α0|64|2|OK||
|cora|rsh-α0|64|3|OK||
|cora|C9-Gorder|64|2|OK||
|cora|C9-Gorder|64|3|OK||
|cora|C10-BP|64|2|OK||
|cora|C10-BP|64|3|OK||
|ogbn-arxiv|B0|32|2|OK||
|ogbn-arxiv|B0|32|3|OK||
|ogbn-arxiv|rsh-α0|32|2|OK||
|ogbn-arxiv|rsh-α0|32|3|OK||
|ogbn-arxiv|C9-Gorder|32|2|OK||
|ogbn-arxiv|C9-Gorder|32|3|OK||
|ogbn-arxiv|C10-BP|32|2|OK||
|ogbn-arxiv|C10-BP|32|3|OK||
|ogbn-arxiv|B0|64|2|OK||
|ogbn-arxiv|B0|64|3|OK||
|ogbn-arxiv|rsh-α0|64|2|OK||
|ogbn-arxiv|rsh-α0|64|3|OK||
|ogbn-arxiv|C9-Gorder|64|2|OK||
|ogbn-arxiv|C9-Gorder|64|3|OK||
|ogbn-arxiv|C10-BP|64|2|OK||
|ogbn-arxiv|C10-BP|64|3|OK||
