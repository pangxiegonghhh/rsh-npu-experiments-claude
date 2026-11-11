# 本机收回远端结果后的必做项（尚未执行）

这是本机后续合并检查清单，不是远端完成证明。源码/输入传输包已独立核验；远端 Windows/WSL 尚未交回任何新实验材料。本机仍运行所分配的 21 例。不得据本文件创建 remote-split-import-verified.json 或全局完成标记。

## 1. 原件与所有权

- 逐文件、逐归档成员核验远端原件/行序/检查点/源代码/ELF，保留 WSL 绝对路径原文以及真实原命令返回码、超时、内存失败。确认严格为 assignment.json 的 20 例、488 个正式条件，不接受未授权案例覆盖本机目录。
- 原件放在独立的 remote-evidence/hostB-windows16gb-wsl2/ 根下；导入的本地可执行路径只是明确标注的派生投影，逐项绑定原件 SHA。禁止直接改写原件或覆盖已封存/本机计算记录。
- 确认远端新运行门禁、Linux RSS 单位、实际加载 ELF、矩阵输入 SHA 与冻结 263 个仓库文件。Mac 历史门禁不能替代 WSL 门禁。
- 只有 20 例的原始阶段、命令、488 条条件与所引用行序全部回收核验后，才能创建入口要求的 canonical_case_records 清单/哈希。缺失与失败如实区分，不创建 DELEGATED 或假 SKIPPED。

## 2. 当前汇总/封存代码的跨主机适配缺口

2026-11-09 只读源代码检查发现以下工作必须在最终封存之前完成，当前未声称已适配：

1. collect_stage3.py 原结果字段没有 execution_host_id。为派生导出添加可追溯的主机标签，且不改原始行的数值/状态/计时。当前条件的执行主机与 -R 借用的历史 Rabbit-U 粗排主机须分开，后者的 coarse_seconds 不冒充 WSL 实测。含历史粗排的 order_sec 需明确说明。
2. build_stage3.py 的 environment()/README 工具环境当前只有 Mac 描述。补充 hostB 实际 CPU、WSL、Python/库、RSS 单位移植与新门禁，并按主机报告计时；不得让全部结果看起来都在 Mac 环境运行。
3. artifact_pack.install_sources 目前只收集本机脚本与库。额外封存远端实际执行版本和 Linux ELF，保留按 SHA 区分的 Mac/Linux 源码快照；不以同名库替换本机二进制。
4. source_provenance_audit.py 只遍历本机 logs 根的 stage3-*.command.json；绝对路径也按本机 BASE 解释。远端原命令须另行核验，路径投影与原件 SHA 绑定，不能因 WSL 路径无法相对化而跳过远端入口/导入依赖证明。
5. guard_provenance 使用已验证生产者源码 SHA。Linux RSS 单位适配会改变 Python SHA；要么保守标为执行来源未证明的结构计数，要么先对实际远端源码做有限差异/AST审查及夹具核验再扩展白名单。不得仅因数值一致或耗时很短宣称重新物理扫描。
6. checkpoint_evidence 从规范 work/post-e 路径发现原始检查点，源文件必须仍字节相同；记录中的本地路径投影另列。回收阶段用时/主机与远端原 P-LS 用时/主机分开。不得为补 PASS 重跑 LS 或 D。
7. 所有新增封存元数据适配须先验证，再更新绑定 builder SHA 的 guard/checkpoint/Rabbit 三项门禁与 readiness；目前三项绑定仍为 builder 780c53c281289e1b740310c50bdeb6faf950dc63a6dd419c2f8735913a54b546。

## 3. 完整收尾仍需完成

- 本机 assigned 调度器 session73950 继续 21 例；旧 session14206 是已行政退役的调度器，不能当成活跃进程或科学失败。finalizer session56126 仍等待全局完成标记。
- 远端 ≥3 个 products 行序独立核验须检查具体实际范围与源码/输入/行序 SHA，不扩大成所有布局覆盖声明。
- 完成预定超时检查点的独立 UG 回收；原始失败/INCOMPLETE 不改成 PASS。
- 执行完整 guard-recovery、检查点原件本地保留/派生侧文件、4 个 Rabbit 粗排映射本地保留/清单，完成各自实际落盘验证。
- 最终 409 例全部真实终止记录、全条件网格、表格不变量、两份 AGENT README/派发/方案逐条审计、冻结源文件与已封存 T21/T22/第一阶段 T23 哈希核对后，才能生成第三阶段归档并逐成员读回。
- 不提交、不推送；不修改任何已封存归档或冻结仓库文件；不启动 NPU。

## 4. 最新已核验增量

C8-METIS Reddit 诊断实际 PID38738，rc0，实际 40.151642 秒；15 个偏移记录齐全，T_full=4466045 与原 own A0 full 两行一致，原 Pi SHA 不变。见 logs/stage3-C8METIS-diagnosis-audit.json。整例仍需两个 post。

2026-11-09 06:06:31 UTC 的源码出处审计通过：695 个命令、34 个导入源码版本，缺失 0。此时刻快照不覆盖之后尚未执行的命令，最终仍需重审。
