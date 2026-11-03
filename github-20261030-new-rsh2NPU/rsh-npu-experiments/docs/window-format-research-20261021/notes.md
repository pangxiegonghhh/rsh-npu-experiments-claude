# 研究笔记与证据索引

日期：2026-10-21（北京时间）

## 本轮核验结果

- 当前项目 README、环境接收记录：历史设备为 Ascend 910B2 / CANN 9.0.0；本地没有已经验证的 Ascend 编译环境。
- 已重新检查rsh/planner.py、npu/work.h、scripts/prepare_d3.py：A为补零16×16块，运行时没有bitmap解码；B按colref逐行搬入。
- 用户已确定当前任务是固定细粒度行窗口下的格式和供给设计。
- 六篇论文方法位置与原始链接见gpu-window-formats.md和npu-window-formats.md；官方接口见cube-input-contract.md。
- 8个原始输入存在；历史冻结order/routing/cases路径不存在。未重新划窗代替既定计划。
- format_probe.py通过1988项编码/乘法语义检查和20项布局检查；结果、输入及源文件哈希见probe-results.json。

## 检索与证据取舍

- 日期2026-10-21；查询覆盖RSH-SpMM、DTC-SpMM ME-TCF、Acc-SpMM BitTCF、TC-GNN SGT、FlashSparse ME-BCRS、NeutronSparse BitMap，以及CANN 900 Mmad / Nd2NzParams / LoadData2DParams / GetCoreMemSize / CrossCoreSetFlag。
- 以arXiv全文、作者托管DTC论文、USENIX原始论文、Huawei官方文档为结论依据；二手摘要仅用于发现候选。没有进行穷尽检索、GPU复现或全面查新。
- NeutronSparse文中的尺寸/容量选择视为论文设计条件，不覆盖官方API契约；其Lite仓库README明确依赖MindSpore/CANN算子栈。
- 官方900网页存在型号混排：排除351x专用迁移限制与Atlas350专用mode4；A2通路按适用型号表核对。

## 分工与文件

- `cube-input-contract.md`：官方约束、版本与片上路径。
- `gpu-window-formats.md`：GPU 窗口格式原文核验。
- `npu-window-formats.md`：NPU 稀疏格式和供给机制原文核验。
- `report.md`：综合研究与具体设计。
- `format_probe.py`、`probe-results.json`：可复现的CPU语义和布局分析。
- `completion-audit.md`：对原目标逐项检查的交付证据。

## 证据标签

文献明确 / 官方文档 / 当前代码 / 本地离线测量 / 设计建议 / 待设备验证。

## 连续推进记录

上一轮只回答了用户对路线的确认问题，没有执行新的研究工作，按目标审计归类为no progress。本轮重新检查当前文件、活跃代理状态和外部原文，实际写入研究成果并运行验证，归类为progress。代理用量限制没有阻止主代理继续完成本地研究。
