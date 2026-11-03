# 910B / Atlas A2：本项目的 Cube 输入契约

核验日期：2026-10-21；G3补证与审核更新：2026-10-22。范围：固定W=16窗口，FP16 A/B，FP32累加。官方CANN 900文档集合与目标9.0.0安装包的实测证据分别记录。E0约定范围及G3独立布局参照已通过；后续E1四种编码设备语义也通过并关机，实际覆盖与限制见§6—§7。

## 1. 输入、物理形状和地址

| 项目 | 已核实的要求 | 本项目采用的约束 |
|---|---|---|
| 数据类型 | Atlas A2 支持 half×half→float | A/B FP16；C 保持 FP32 |
| Mmad 操作数位置 | A2、B2、CO1，分别对应 L0A、L0B、L0C | 稀疏文件不能直接作为 Mmad 操作数 |
| 逻辑 m/n/k | API 范围各为 0…4095；官方 half 示例为 M=30、K=70、N=40 | 第一版 m=16、k=16，n 为当前特征分块；后续独立测试 k=16q |
| 物理分形 | FP16 A/B 单个分形 16×16、512 B；输出分形 16×16 个元素 | 补齐空间必须存在；不能把“16×16 分形”解释成“API 只能计算 16×16” |
| Mmad 首地址 | A/B 512 B 对齐；C 256 个元素对齐 | FP32 C 按 1024 B 对齐，覆盖一般 L0C 对齐要求 |
| 累加 | `cmatrixInitVal=true` 清零；后续 false 且来源 CO1 | 一个窗口、一个 N 分块的全部 K 消费结束前保持同一 C 累加区 |

依据：[Mmad：参数表、Atlas A2 类型表、非 16 倍数示例](https://www.hiascend.com/doc_center/source/en/CANNCommunityEdition/900/API/ascendcopapi/atlasascendc_api_07_0249.html)。这里选择 K16 作为软件基本单位，不宣称它是唯一合法的逻辑 K。

一般 UB/L1 首地址按 32 B、L0A/L0B 按 512 B 对齐；具体 API 的更强约束优先。GM 没有统一的首地址对齐要求，仍需遵守具体搬运参数和长度要求。[General Address Alignment Restrictions](https://www.hiascend.com/doc_center/source/en/CANNCommunityEdition/900/API/ascendcopapi/atlasascendc_api_07_0004.html)

## 2. 布局必须写成地址公式

官方布局指南给出：L0A 为 ZZ，L0B 为 ZN，L0C 为 NZ；L1 通常使用 NZ。对 FP16，将轴拆为 `m=m1*16+m0`、`k=k1*16+k0`、`n=n1*16+n0`，按以下轴序连续存放：

| 位置 | 逻辑矩阵 | 内存轴序（最右侧连续） |
|---|---|---|
| A_L1，整块 NZ | [M,K] | [k1,m1,m0,k0] |
| A_L0，ZZ | [M,K] | [m1,k1,m0,k0] |
| B_L1，整块 NZ | [K,N] | [n1,k1,k0,n0] |
| B_L0，ZN | [K,N] | [k1,n1,n0,k0] |
| C_L0，NZ | [M,N] | [n1,m1,m0,n0] |

依据：[Data Layout Formats，Special Formats for Cube Multiplication](https://www.hiascend.com/document/detail/en/CANNCommunityEdition/900/programug/Ascendcopdevg/atlas_ascendc_10_0099.html)。Mmad 英文页部分说明段落将 NZ/ZN 名称写反，与该页概要和布局指南不一致；本设计以轴序、地址公式及设备单元测试消除名称歧义。

**由上述布局推导，本项目 W=16 时 m1 只有一个取值，A 的 NZ 和 ZZ 字节顺序相同。** 当前 `[Ktile,16,16]` 的稠密 A 已有这一顺序；给它改名并不会产生一种新压缩格式。多 K16 的 B 则需要区分：

- 整块 NZ：`B1[n1,k1,k0,n0]`。
- 本设计可选的逐 K16 暂存区：`Bstage[k1,n1,k0,n0]`。它不是整块 NZ，但 L1 本身不要求只有一种布局；按各 K16 子视图装载，或按分形序转置后构造 ZN，仍可作为合法设计。

两者不能混用同一套偏移公式。相关布局代数已由本地脚本验证，具体 LoadData 调用仍需设备验证。

## 3. 已有接口支持哪些路径

| 路径／操作 | 官方依据与边界 |
|---|---|
| GM→L1 时 ND→NZ | Atlas A2、half 支持；`nValue/dValue` 为源行列数，`srcDValue` 为行跨度；目标 NZ 步长单位为 32 B。D 方向不足 32 B 的部分可补零 |
| UB→TSCM(L1) 时 ND→NZ | Atlas A2、half 支持，适合研究 AIV 展开后供给 AIC |
| L1→L0A/B，Load2D | 逐分形搬运；一次 repeat 为 512 B，`repeatTimes` 为 1…255，起点和 stride 以分形为单位 |
| L1→L0 分形内转置 | Load2D 对 b16 支持 `ifTranspose=true`，可用于 B |
| GM→L0A/B | Load2D 页面包含这些路径；不能声称 910B 一律必须经过 L1。直接装载要求 GM 已有相应布局，应单独微测 |

来源：[ND2NZ：Supported Paths and Data Types、参数表](https://www.hiascend.com/doc_center/source/en/CANNCommunityEdition/900/API/ascendcopapi/atlasascendc_api_07_00127.html)，[Load2D：适用型号、路径、参数](https://www.hiascend.com/document/detail/en/CANNCommunityEdition/900/API/ascendcopapi/atlasascendc_api_07_00169.html)。L1 暂存方案是本项目为重用、分组和流水选择的路径。

## 4. 同步和资源

AIV→AIC 不能只用核内队列代替跨核同步。Atlas A2 的 `CrossCoreSetFlag/WaitFlag` mode 2 涉及同组一个 AIC 与两个 AIV；不能让一个 AIV 提前返回而另一个仍在给 AIC 供数。flagId 范围、循环计数及配对必须遵守 API，不能使用仅 Atlas 350 支持的 mode 4。[CrossCoreSetFlag](https://www.hiascend.com/doc_center/source/en/CANNCommunityEdition/900/API/ascendcopapi/atlasascendc_api_07_0273.html)、[CrossCoreWaitFlag](https://www.hiascend.com/doc_center/source/en/CANNCommunityEdition/900/API/ascendcopapi/atlasascendc_api_07_0274.html)

本设计不从论文或其他型号抄入 L1/L0 容量常数。host tiling 用 `PlatformAscendC::GetCoreMemSize` 查询 L1、L0_A、L0_B、L0_C、UB，减去框架预留后再决定 q、N_t 和缓冲级数。[GetCoreMemSize](https://www.hiascend.com/doc_center/source/en/CANNCommunityEdition/900/API/ascendcopapi/atlasascendc_api_07_1034.html)

设 Np=ceil(N_t/16)*16、每个 L1 包含 q 个 K16、L1 缓冲 d1 份、L0 输入缓冲 d0 份：

```text
L1 数据预算 = d1*q*(512 + 32*Np) bytes
保持 K16 消费：L0A = d0*512，L0B = d0*32*Np
改为 K=16q： L0A = d0*q*512，L0B = d0*q*32*Np
L0C = 64*Np bytes（单个输出累加区）
```

以上是本设计的数组大小计算；还须加上对齐空隙、描述符/中间区、API 工作区和事件资源。AIV 解码另计 UB，不包含在 L1 公式内。

## 5. 版本与验证边界

- 不能把 [351x Basic API Porting Guide](https://www.hiascend.com/doc_center/source/en/CANNCommunityEdition/900/programug/Ascendcopdevg/atlas_ascendc_compatibility_10_00005.html) 的迁移限制套到 910B；该页面明确讨论 351x，已从本项目的 A2 约束依据中排除。
- 本文未核实或承诺 910B 原生支持任意 bitmap 稀疏 Mmad；候选压缩格式均先软件展开为稠密操作数。
- 研究设计阶段为本地布局/语义检查；后续E0已完成当前尺寸下的搬运、布局独立参照、资源与边界检查。跨核共享分配及同步留给E2，性能留给后续实验；核内GM直装同步不替代AIV→AIC跨核同步。

## 6. 当前验证覆盖与补测入口

E0当前约定范围已完成；2026-10-22定向补证闭合G3的共同K置换盲区，179进程、233次调用及本地独立回放全部通过，最大绝对误差0。E0关机确认时间为15:08北京时间；随后E1也已完成，最新关机和覆盖见§7。见[G3总结](../e0-e6-experiments/artifacts/e0-g3/20261022-r1/summary.md)。既有223项独立、两路径各17项集成、27组重复/扰动及另补120次逐次集成证据保留；真实单次Mmad(30,70,40)的debug为[1,30,70,40]。

| 项目 | 当前设备证据／约束 |
|---|---|
| A/B布局 | 固定原始物理单位基A、逐分形GM→L0A后，144项B独立选择器通过，再以已确认B验证24项正常A；K16/32/48、Np16/32/64、两种B布局、逐/多分形及标签/选择段完整覆盖。证据为selector_observed及物理槽/搬运范围核对，未做L0原始字节读回 |
| A直装 | GM预排布A→L0A可用；本原型增加M→MTE2复用及MTE2→M就绪事件后通过，不能只依赖原A2队列的常规搬运同步 |
| 入口构建 | 本工具链下同源双入口产物曾有入口未执行；拆分编译单元后两个入口通过。源码/二进制必须核哈希，每轮使用全新构建目录避免时间戳导致旧host残留 |
| 尾部 | N17/33、K尾、M30尾行、相邻窗口和FP16紧凑A的valid_k=1/5/15装载原语通过；E0原语不独自证明紧凑编码kernel；E1四种编码语义另见§7，其路径含展开及GM中转 |
| 逻辑尺寸 | K32/K48单次与逐K16累加均通过；30/70/40采用完整物理空间与零填充，有效区通过，未承诺非零无效槽屏蔽或未定义输出值 |
| 资源查询 | L1=524032、L0A=65536、L0B=65536、L0C=131072、UB=196352 B；为目标SDK查询值，不把理论规格或未知框架预留当成实际可分配上限 |
| 边界 | 完整packed/输出、规定零padding、GM guard、host非法参数拒绝、读范围枚举与实际有限哨兵扰动通过；guard不变不能单独证明无越界读 |

全部原始结果、完整构建日志、失败版本和哈希见[实验状态](../e0-e6-experiments/experiment-status.md)、[补测总结](../e0-e6-experiments/artifacts/e0-supplement/20261021-r1/summary.md)。结论限于所列有限FP16合成输入和尺寸；AIV跨核供给、Residual竞争、真实冻结行序/路由、N128/256及性能尚未验证。


## 7. E1编码语义设备覆盖（2026-10-22已完成）

Dense16、DenseTail、Bitmap16、LocalIndex16各497主例，共1988主例通过；U=0/1/15/16/17/31/32/37/48/63，N=1/16/17/32/33/64，含z=0…256全占用率单tile诊断。另24核心配置×3新进程×10次=720重复调用和9设备小样全部通过，最大绝对误差0。

设备分别回收并验证还原A、补齐列映射、Cube输出及debug/guard；本地从原A/原列/B独立重放全部2717案例调用通过。16类非法descriptor、位图/index、列映射、边界及非有限值在host拒绝。U0不生成descriptor，设备显式写零C。

实际路径为AIV解析→UB还原→GM→stream同步→既定AIC装载/Cube。它证明所列编码语义，并未验证共享L1、跨核ready/release、双缓冲或性能；E2仍须单独完成。满块/尾块的优化直装策略不能从本轮通用GM展开路径推断已获性能收益。

源/产物与SDK头对应一致，42953成员哈希和归档校验通过。实例于15:46:26北京时间观察确认已关机，累计2小时7分钟，下一项E2尚未开始。见[E1总结](../e0-e6-experiments/artifacts/e1/20261022-r1/summary.md)、[实验台账](../e0-e6-experiments/experiment-status.md)及[续跑入口](../e0-e6-experiments/resume.md)。


## 2026-10-22 E2首轮：物理通路前提纠正

E2目标新构建成功，但首个非空单缓冲小样在设备同步时发生MPU异常；尚未进入正式批次。核对目标CANN9.0.0的dav_c220安装头文件发现：UB→TSCM的普通DataCopy与ND2NZ重载实际先UB→GM，再通过KFC让AIC搬入L1，并依赖TPipe/KFC上下文。逻辑位置UB→TSCM不等于物理无GM直达。上文“官方证明通路存在”仅能理解为API逻辑支持，不能作为无GM片上交接的证据。

原型未配置该上下文，是明确实现缺口；是否为此次MPU异常的唯一原因尚待分层设备复现。后续须明确采用带GM成本的同kernel生产消费路径，或重新证明目标设备的其他可用通路；不得将含GM版本作为原无GM门槛通过。E2尚未完成，E3未开始。详见[E2首轮记录](../e0-e6-experiments/artifacts/e2/20261022-r1/summary.md)。
