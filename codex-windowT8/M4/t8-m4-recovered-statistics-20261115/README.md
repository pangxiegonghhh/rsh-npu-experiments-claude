# M4 有效计时数据回传说明

2026-11-15 约14:53～15:00，以无GPU模式短暂开机，只读取已有文件，未新增设备实验；取数后已确认关机。

此前普通文件下载未收到完成事件，本次将原有数据导出成真实可读的分页表格文档，再通过受支持的页面资源保存接口取回，按文档文本恢复记录；不是将二进制归档伪装为文档。导出和回传后的全部数据记录SHA256一致：4ab8a15e87e73edfcb07290efe578371fd2f91e9fb7839261690ea6b886fa285。

本目录的 timing-observations.json / timing-observations.csv 保留2,592个合成实跑配置、40个Cora回放配置各20轮的归一化时间、global时间和批量参数。字符串保留原CSV打印数值；block编号按0～19。CSV是语义等价重建表，不是原文件字节副本；源文件原始SHA256列表在 recovery-verification.json 中。原CSV的行顺序/分块路径不同，不应要求新表匹配原文件SHA256。

- 主测量：51,840个有效点样本，norm单位μs/全局归一化窗口；global为内核内供数+计算区间的全局makespan，μs。
- 回放：800个有效点样本，norm单位μs/全局归一化矩阵；每周期170窗口。
- model-coefficients.json：主R/API各120张、补充pooled API共60张，保留c/a/b均值及95%区间；未保留每块原系数，但可以从20轮时间重新拟合。
- model-recomputation-verification.json：使用既有完整配置manifest和全部取回时间重拟合300张系数表，264可识别、36共线，全部PASS，最大系数差约1.05e-16μs。

在解压后根目录运行 `python audit_m4_recovered_statistics.py`，需要NumPy，可复核上述系数。脚本不会调用设备或CANN。配置manifest须保持随包的相对目录。

本包不含完整回读二进制、stats.bin、所有失败日志或旧中断块。1.45GB完整封存归档仍在实例/data，尚未确认整包本地下载。不能因此把本包称为全部原始证据，但有效正式计时已可离线重算。

模型系数不能当作已通过验收的每指令延迟：主R模型0/20组合通过真实回放，pooled API模型也没有组合同时通过B0/B1。t尚未可靠标定。
