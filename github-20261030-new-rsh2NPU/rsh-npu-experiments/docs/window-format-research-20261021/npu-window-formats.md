# NPU 相关工作与展开路径

核验日期：2026-10-21。

**NeutronSparse: Coordinating Heterogeneous Engines for Sparse Matrix Multiplication on NPUs**，Xin Ai 等，arXiv:2606.22482v1，2026-06-21，是本次检索中与 Ascend 910B 最直接相关的原文。[论文全文](https://arxiv.org/html/2606.22482v1)

| 原文位置 | 能确认的内容 | 不能由此直接推出的结论 |
|---|---|---|
| §5.1 | AIC 路径根据列索引准备 B，并将 A/B 操作数送往计算缓冲 | 不是可直接照写的逐指令搬运程序 |
| §5.2.2 | AIC分配的部分用BitMap，AIV部分用COO | 没有给出足以唯一重建其BitMap ABI的字段、位序、偏移及解码内核 |
| §6.2 | 研究分层tile复用；文中默认(M,N,K)=(128,256,64) | 不是本项目W16的最优尺寸，也不是硬件唯一合法尺寸 |

论文支持“格式应与异构引擎和片上供给共同设计”的方向；不能仅因其采用 BitMap，就认定 16×16 bitmap 会优于已展开的稠密 A。

作者公开的 [NeutronSparseLite 仓库](https://github.com/iDC-NEU/NeutronSparseLite) README 明确其运行依赖 MindSpore/CANN 预编译算子栈，并列出 CANN 8.2.rc1 环境。本轮只核对公开说明，不把 Lite 代码视为完整论文低层 kernel 的复现，更不从中推定目标 CANN 9.0.0 的指令可用性。

## 本项目可以具体研究的路径（设计建议）

1. **预展开 A**：A 的稀疏结构固定时，在离线准备阶段生成512 B分形，AIC从GM装载。这是现有实现的基础，运行时不解码。
2. **片上展开 A**：压缩数据GM→AIV的UB，按位图/局部位置填入稠密16×16；UB→TSCM(L1)，AIC再装载L0A。官方Atlas A2的ND2NZ支持UB→L1，见 [Cube 输入契约](cube-input-contract.md)。该路径需明确共享L1分配和跨核事件。
3. **GM中转展开**：AIV把展开结果写GM，再由AIC读取。可作为最简单的分阶段功能对照，但每tile额外写512 B、读512 B，不能把这部分藏到计时之外。

如果 A 的数值也长期不变，压缩一次、每次解码未必划算；应该同时报告“离线展开后多次使用”和“保留压缩、每次调用展开”的总成本。如果 A 的结构固定而值更新，结构元数据可复用，但 A 值的重编码成本须另计。

片上展开还占用AIV资源。当前Residual分流虽然保持不变，性能验证仍必须检查它与残余计算并行时是否发生竞争。AIC单支变快不足以证明完整调用受益。
