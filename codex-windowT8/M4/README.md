# M4：段数、精度和流水耗时

- [结果报告](reports/M4-results-text-only-20261115.md)
- [主实验源码与输入](t8-m4-20261114/)
- [Cora回放源码与输入](t8-m4-replay-20261115/)
- [全部有效统计数据](t8-m4-recovered-statistics-20261115/)
- [本任务复核记录](verification/)

原始命令表、CSV/JSON、核函数均保持原字节。CPU原始段表见[共享准备数据](../shared/t8-cpu-prep-20261114/)。M4模型迁移验收未通过，不能把拟合系数当通用指令固定开销。

从资料根目录运行`python3 run_cpu_checks.py --out audit-output`做隔离副本复核。
