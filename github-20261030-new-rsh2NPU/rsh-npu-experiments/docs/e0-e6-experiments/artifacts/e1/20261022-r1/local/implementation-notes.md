# E1实现边界与覆盖

日期：2026-10-22；状态：本地实现中，设备未恢复。

字段协议沿用研究报告§4。每例是已固定单个16行窗口，列映射排序且不重复；不执行A重排或路由。空窗口不生成tile descriptor，设备显式写零C。设备AIV用标量解析原始位图/局部索引到UB零底板，再写GM A和补齐列映射；串行同步后用原E0 Probe<false>逐K16消费。每次捕获完整扩展A、refs、C和两个debug，host逐次检查所有输入guard及字节不变。

正常矩阵：10个U × 6个N × 4种密度/值模式 × 4编码=960例。另全占用率z=0…256 × 4编码=1028例（固定结构列域的单tile编码诊断，允许更新后结构零列，不冒充实际列并集密度），共1988例。重复核心覆盖4编码、U17/37/63与N17/64，各10次，后续脚本核对确切调用数。重复过程独立轮换A/B符号，连续编号和数量强校验。

需检查offset/长度/nnz/popcount/index严格递增/列映射及零padding。非法输入只运行host验证分支，在aclInit之前拒绝，不提交设备。

本路径包含GM中转，不证明UB→L1跨核共享或性能收益。计时非E1目标，不提供速度排名。

本地实际C++ Input验证1988有效例通过，16类非法输入拒绝。实际解码器标量函数体以host内存API stub编译运行，1988例A/refs/空C还原通过；这些不是目标CANN编译或设备结果。

核对官方同步说明后，新解码器显式使用S_MTE3就绪事件，并在入口/出口刷新标量DCache；目标9.0.0实际支持仍以设备编译和运行验收。参考：https://www.hiascend.com/doc_center/source/zh/CANNCommunityEdition/82RC1alpha003/API/ascendcopapi/atlasascendc_api_07_0270.html；https://www.hiascend.com/doc_center/source/zh/CANNCommunityEdition/850/API/ascendcopapi/atlasascendc_api_07_0206.html

重复按24核心配置×3新进程×10调用=720，连同1988主例合计2708次E1案例调用；早期备注仅描述单个10次组，现以此明确计数。

第一次恢复被平台因余额不足拒绝，实例保持OFF；用户随后自行充值并授权继续。
