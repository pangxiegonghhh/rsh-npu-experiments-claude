# M11b 本地交付 / 2026-11-16

报告：2026-11-16--t8--r11b--recompute-and-bridge.md；独立离线R1–R12：../m11-work/analysis-recompute-20261115/README.md。

B1随机已落实，设备分支取消。B2全部84×20完成，预登记定量误差门4/4超过30%，不能用均值合成点定量预测真实回放相对性能。B3差价未估得：plain-only50/50不等价，不能强行作计时参照；未执行其12000条正式网格。三候选600计划配置全部状态见analysis-output/B3-planned-grid-status.csv。

普通84和强地址84检查均在正式计时前完成。全部原始结果/环境/build/失败在72.7MB原始tar；10090文件SHA、1680条时钟复算通过。原M11的204631原始文件和21保护分析文件不变。实例已关机，增量约30分钟/估算2元。不要因阅读报告开机。

偏离：B2加12同批控制在计时前登记；B3改成独立直接消费验证target，B2 kernel字节不变；原稿600×20算术错误修正；缺失被引交回模板采用兼容schema；B3非法L0向量转置不执行、不扩AIV/GM方案。一次group摘要打印精度校验错误只修登记并保留全部首区组原数据。详见总报告。SDK源码、初始上传SHA和后续控制修正的各自版本均保留；最终源以EVIDENCE-SHA256为准。

离线复算：M11B_DATA_ROOT="$PWD/recovered-evidence" python3 analyze.py。需先用verify_return.py把本tar安全解包到recovered-evidence；不执行回传binary。reference-analysis含原M11冻结对比表及SHA，只供旧参考敏感性，原M11原件不修改。原R1–R12重算需已有M11完整回收目录；recompute.py仅写独立新目录。

当前未绑定Obsidian，无知识库写回，无Git push。
