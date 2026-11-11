# T4 执行记录

- 输入说明：/Users/Zhuanz/ClaudeCode/rsh-npu-experiments-claude/第一层工作区/T4派发/说明.md
- 当前仓库起始 HEAD：0d01756bfe36e2d07b4a99f49143d648af48c44b，main，有既存未提交变更。
- 当前仓库 E0-E6 resume 是历史 10 月记录，与 T4 不同系列；不据此自动启动 E4/NPU。
- 所有本轮修改放新目录；原始资料只读。

- 原工作区 native.py 已从 v2 演进到 v7；本轮按派发要求使用归档 native.py 的 v2 Layout，评价器字节一致，原 librect 和矩阵只读 symlink。
- cora 自检 PASS；cora 与 T23 B1 置换及全部 ΣU/T 精确一致。
- 所有超时停止不重试；每个进程保留内存保护日志。

- 已在 /private/tmp/t4-sync-20261111 建立独立 clone，codex/run-t4-rshref-20261111；原 checkout/index 未改。遵循用户 AGENTS 的逐轮同步授权，最终不向 main 推送。
- 原始计时合并两期来源：C4-U 八张 11.9636018276s；B1 八张449.0656901002s。NO 分支按派发使用 cora/arxiv/reddit 三张校准 B1。

- 四张 B1 一致性门均通过，零差异；cora/arxiv 全网格ΣU/T也一致，无空行例外。reddit461.299秒，products454.672秒（本轮hostA）。

- 控制器COMPLETED_NO_BRANCH，29次行序生成；18个调参/E1评价案例、360行全部OK。E1在7/8点不差，H4成立；cora独立重复确定性通过。
- 独立全档复算与控制器第2轮数值均不触发2%扩展；全部输入运行后哈希未变。
- 辅助只读检查中ps被沙箱拒绝，不影响实验；未升级采集全系统进程。

- 帕累托汇总首遍遇到历史reddit B0/tau153 tail-co INCOMPLETE，无T字段，保留attempt1失败日志；修复汇总选择器，按T23已验证的T放置不变量取同矩阵同τ的tail-own T，逐项写入T_invariant_fallbacks。未重跑实验、未修改历史行。
- 重算A0/A1前沿相同：C9-Gorder、C10-BP、C4-U、C4-T、C7-I、B-RSH-ref。类别覆盖与至多3个名额的最终取舍交规划复审，原短名单不改。
