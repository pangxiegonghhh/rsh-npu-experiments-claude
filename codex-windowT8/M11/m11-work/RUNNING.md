# M11 完成状态

**设备实验、证据回收、统计分析和报告均已完成。实例已关机；不要为续读报告重新开机。**

- 中文报告：[2026-11-15--t8--r11--ordinary-copy-ablation.md](/Users/Zhuanz/ClaudeCode/rsh-npu-experiments-claude/m11-execution/m11-work/2026-11-15--t8--r11--ordinary-copy-ablation.md)
- 分析目录：/Users/Zhuanz/ClaudeCode/rsh-npu-experiments-claude/m11-execution/m11-work/recovered-evidence/analysis-output
- 完整原始归档：/Users/Zhuanz/ClaudeCode/rsh-npu-experiments-claude/m11-execution/m11-work/m11-evidence-complete.tar.gz
- SHA256：0278def60a7771753a6d7921418434a7794e77ff7c03581dc098be040a3694a9；518,508,328字节。
- 回传204,631文件逐项SHA核验PASS；正式45,920条时钟独立复算PASS。
- 计时前1,104项正确性、计时后594项完整地址复核均PASS；所有正式20轮完整，无漂移作废。
- Cora B1高N按行6/8格降时25.35%–42.07%；FP16/N128两格反而慢30.50%–33.31%。原始FP32 A普通链耗时约为ND的5.5倍。
- 平台OP08JZ85MYKCJKH3在上海2026-11-15 19:18已核对“已关机”；结束无NPU进程；新增约90分钟，4元/小时估算6元，以账单为准。
- 复用用户允许的原实例，没有租新卡；未改M8目录、原资料、论文论点，没有push。
- 临时认证文件已删除；回传二进制未执行。
- 原始归档保留设备运行时的代码；本地analyze.py增加finalize_analysis.py生成最终图表/报告，原数据不变。离线重算命令见报告。

## 可复核限制
仅Cora B行回放+固定稠密A消费，非完整稀疏SpMM；共同gmax未逐路径调优。未识别通用固定t。选优两条普通路径是描述性，点CI无选择校正/同时覆盖保证。阶段3哨兵只有5次中位数及漂移，主20轮原值齐全。source_span_rows描述错误已外部注释且不影响实际地址。完整限制见报告。
