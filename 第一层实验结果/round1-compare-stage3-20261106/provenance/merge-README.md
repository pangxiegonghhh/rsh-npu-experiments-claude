# T22 / T23 双主机合并交付（2026-11-10）

T22 与 T23 阶段1–2的原始封存包位于 sealed-first-deliveries/，字节和 SHA 不变。
本目录 results.csv、status.csv 等为 T23 阶段3的独立合并导出；不覆盖原始表。
409例全部有真实终止记录：320 OK、48 INCOMPLETE、41 SKIPPED；另列6个可选参照 SKIPPED。
6276行正式条件；远端20例488行（200 OK、288 INCOMPLETE），原表全部字段逐项保持。
整例状态与生成阶段状态不同，不能把生成 OK 或“终止”视为整例通过。

## 文件与核验

- results.csv / status.csv / diag.csv / groups.csv / guard-counts.csv / post-E.csv：合并表与主机标签。
- case-host-ledger.csv：409例的实际原件、SHA、主机与历史 Rabbit 粗排计时来源。
- raw/hostA/ 与 raw/hostB/：原始科学记录、日志、源码和平台证据分开保留。
- merge-evidence/remote-verification.json：263冻结文件、输入哈希、11个新WSL门禁、源码链、ELF及19行序校验。
- combined-source-chain-audit.json：按实际命令SHA核验入口与静态本地导入源码，不执行返还的程序。
- merged-arithmetic-audit.json：所有OK行的算术、固定成员U/T和比值不变量核验。
- orders-manifest.json / checkpoints-manifest.json：大文件位于单独的 T23-orders-merged-20261110.tar.gz。
- SHA256SUMS：本包所有文件；外部同名 .sha256 校验整个 tar.gz。

## 口径与限制

hostB为Windows/WSL2 x86_64、AMD Ryzen7 5800H，Python3.12.3、NumPy2.4.4、SciPy1.17.1。
hostA为Mac M1 Pro 16GiB、macOS15.2 arm64、Python3.12.10。实际版本原件分别保留。
Linux RSS仅作KiB→MiB移植，5处源码反向还原AST一致，ELF按构建/加载SHA独立核验。
不同主机耗时不混合平均或互换。-R的历史Rabbit-U粗排成本来自hostA，原local_seconds另见记录。
guard计数是保存的条件报告，可能继承缓存，不按行数宣称独立物理扫描；未增加Linux生产者白名单。
Reddit C8-METIS τ53超时、τ153重启中断和products C6-HP exit -9保持INCOMPLETE。
远端C3-A原生成超时保持INCOMPLETE，未产生最终行序，未用其他方法行序代替。
原完成轮次检查点保留完整向量，但本次合并不重跑LS、D或检查点评价。
本包完成数据合并与证据核验，不声称另一个正式阶段3封存流程的所有回收步骤已闭合。
无NPU、无提交或推送，未写分析结论。定时任务已删除；两个空闲等待进程已行政停止。
