# M5 正式统计原始数据与复核脚本

这是方便 AI/研究者分析的统计包。目录 t8-m5 下保留原有相对路径，包含正式计时、质量补测、全部首尾哨兵 CSV、manifest、块登记（含作废记录）、正确性 gate、分析 JSON/CSV 和源码。

本包不含大型 L1 回读二进制及完整模型逐指令追踪；它们在已下载的完整 t8-m5-evidence-20261115.tar.gz 中。完整包 SHA256：1f95e4eae66f7fae630169d0a363968667ce526de3d6ee5b6c21c03b562d877e。此前完整包内 58,245 个文件的校验均通过。

从 t8-m5 目录执行：

```text
python audit_m5_statistics_offline.py .
```

只需 Python 标准库，无需设备、CANN 或联网；原始分析文件保持只读。offline-statistical-verification.json 是打包时的重算结果。

重要读取规则：

- 正式有效数据为 20 块、55,040 行；质量补测有效 20 块、7,200 行，另有一个作废补测块，须按 block-registration.json 排除。
- 补测的 90 个用例使用新数据替换原批量数据，不能将两批合并扩大样本量。最终拟合实际使用的点样本仍为 688×4×20=55,040。
- 原始批量 64/256/1024/4096；补测 256/1024/4096/16384。sample 是块编号；us/cycles 是整批测量，不是每次搬运耗时。
- cycles 是整数原始计数；us=cycles/50 后仅打印 6 位有效数字。现有报告和原统计脚本使用 us；用 cycles 重算时应注明精度口径不同。
- 初次 59 个“逐块 R² 平均值低于 .999”的用例及配对组成 90 个补测用例。最终筛选另用“批量均值曲线 R²”，仅排除一对。两个指标不能混淆。
- paired.csv 有全部 344 对；timing-qualified-pairs.json 有最终 343 对，仍含 56 个单段控制。最终多段汇总须选 segments>1，共 287 对。
- final-summary.json 的 qualified_groups 是报告中的最终汇总，groups 是均值曲线质量筛选前的汇总。不能把 FP16/NZ 的 3.250 与最终 3.255 混用。
- saved_ci_low/high 是节省时间的逐点 95% 区间，不是速度倍数的区间；未做多重比较校正。api_calls 是源码按配置推算的预计 API 调用数，不是实卡 PMU。
- M5 为单 AIC、热源重复搬运微基准；源跨度最多 1 MiB，不是全卡、HBM 或完整 SpMM。

详细设计与真实用例解读见 M5-design-and-number-guide-20261115.md。
