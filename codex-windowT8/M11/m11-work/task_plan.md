# M11 实验执行计划（已完成）

## 目标
读取codex-window/codex-windowT8，完成M11的源码核对、CPU准备、正确性、设备计时、统计与交付。

## 阶段
- [x] 固定资料提交，8,975文件SHA、M4/M5复算通过
- [x] 完成源码/SDK核对、CPU输入与地址/工作集审计
- [x] 重启复用用户授权的原实例，完成1,104项计时前正确性
- [x] 完成45,920条正式计时（每阶段20有效区组，无漂移作废）
- [x] 完成594项计时后完整地址复核，正式计时binary未改
- [x] 全归档回传，204,631文件SHA与45,920条原时钟复算通过
- [x] 平台已关机复核，临时认证文件已删除
- [x] 中文报告、完整数表、3张图及离线复算脚本已检查并交付

## 最终结论
Cora B1高N主格普通按行6/8降低25.35%–42.07%，但FP16/N128慢30.50%–33.31%，优势有条件。六个优势格的普通按行B0/B1仍约1.48倍。FP32原始A普通两stride链正确，耗时为ND链约5.5倍。合成数据R影响相对路径选择，未识别通用固定指令t。

## 决策与边界
固定资料提交f1a1c5e9d119fb1213dff509b5984b6145ee8c51；本地隔离目录m11-execution，分支codex/m11。用户最新授权覆盖旧M8隔离描述，允许复用已空闲实例。M11独立目录运行，不改M8旧数据；未新租卡、未推送Git、未改论文或冻结结构。

## 错误与解决
- 首次编译MTE1_S事件在CANN9无定义：保留失败源码/日志，改MTE1_M→M_S间接等待后全门通过；同时修Linux std::min模板类型兼容。
- 大上传包413：改102,824B源码包，远端重建并核验。
- 浏览器tar下载受拦截：既有Jupyter授权文件接口回传，全部SHA一致，临时授权文件已清除。
- source_span_rows描述字段多16行：实际config/核地址/审计/CSV正确，保留原始归档，外部注释并修未来生成器；1,530输入二进制完全未变。
- 原正确性标记mod7/mod251盲点：新增594项独立完整地址复核，计时后执行时序如实保留。
- 图初版主对比尺度压缩、合成cold点被裁：分面/改范围并目视复核，全部数据展示。

## 最终状态与入口
**已完成、已关机，无运行中任务。** 新增约90分钟/估算6元，详见shutdown-verification.json。
报告：/Users/Zhuanz/ClaudeCode/rsh-npu-experiments-claude/m11-execution/m11-work/2026-11-15--t8--r11--ordinary-copy-ablation.md
分析数据：/Users/Zhuanz/ClaudeCode/rsh-npu-experiments-claude/m11-execution/m11-work/recovered-evidence/analysis-output
完整设备归档：/Users/Zhuanz/ClaudeCode/rsh-npu-experiments-claude/m11-execution/m11-work/m11-evidence-complete.tar.gz
续接状态：/Users/Zhuanz/ClaudeCode/rsh-npu-experiments-claude/m11-execution/m11-work/RUNNING.md
