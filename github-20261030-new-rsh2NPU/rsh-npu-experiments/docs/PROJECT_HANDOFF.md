# RSH迁移NPU：完整项目情况与交接

状态时点：2026-10-22，北京时间。当前任务是项目交接与GitHub初始化，不执行设备实验。当前动态状态始终以[续跑指针](e0-e6-experiments/resume.md)为准。

## 1. 项目目标与边界

用户已确定A的行重排和RSH式细粒度行划分。本项目研究在固定窗口和AIC/Residual归属下，怎样组织A、映射当次B，并向910B Cube高效供数。用户将选中Cube分支的准备、装载、计算和写回流程称为“AIC kernel”；解码若使用AIV，也属于这条供给支路的实现成本。

本轮不重新寻找行序、不改变窗口成员或分流来制造收益。旧项目位于旧电脑路径`/Users/Zhuanz/Desktop/研究生规划/rsh-spmm-910b`，只读；2026-10-20复制到此独立目录。当前仓库不依赖旧Git或共享worktree。迁入146文件逐哈希核验，见[迁入清单](../迁入清单.json)与[环境接收记录](../环境接收记录.md)。旧D0—D3结论只作历史背景，不等于本轮E0—E6已完成。

研究借鉴DTC-SpMM、Acc-SpMM、FlashSparse等方法中的组织/供给思路，提出统一接口下的候选编码与可证伪实验；不是照搬三个完整kernel后选赢家，也未宣称已获得一种有性能优势的新格式或论文新颖性。

## 2. 三个尺度和统一接口

- W=16：固定窗口的16行，M维。
- K16：窗口压缩列空间中16个槽，归约维；对应原A列号可能不连续。
- Nt/Np：当前B特征列范围及向16对齐的物理宽度，决定B搬运与缓冲规模。

同一窗口有U个有效原列号，`cols[j]`同时表示原A的列与当次B的行。第t步计算`A_t[16,16] × B_t[16,Np]`并累加，局部列`16*t+k`通过`cols`回到原列号。U=37时有效列为16+16+5，计算域补齐到48；GM是否保存尾部零是格式研究变量。包q=1/2/4/8包含多个K16，存储/搬运包不必等于单次Mmad消费粒度。

统一W16协议v0使用窗口目录、共享原列映射、冻结row_map、16B tile descriptor及32B起点对齐payload。descriptor `<QHBBI`：字节offset u64、nnz u16、kind u8、valid_k u8、payload_bytes u32。nnz可达256，尾映射不落盘；padding A/B必须为零，B尾槽指向额外零行或显式补零，不访问原B界外。

| 编码 | kind | GM payload（未算公共目录/对齐） | 用途 |
|---|---:|---|---|
| Dense16 | 0 | 256 FP16，512B | 无解码对照与分组搬运 |
| DenseTail | 3 | `[16,valid_k]`，32×valid_k B | 尾部零列不存储 |
| Bitmap16 | 1 | 16个u16位图+FP16值，32+2z B | 中等密度候选 |
| LocalIndex16 | 2 | z个u8位置+偶数字节补齐+FP16值，3z+(z mod 2) B | 很稀疏候选 |

压缩减少存储不代表减少Cube稠密计算，更不代表已经更快。B每次调用更新，不能把B打包当作免费离线预处理。字段、布局与成本公式见[研究报告](window-format-research-20261021/report.md)及[输入契约](window-format-research-20261021/cube-input-contract.md)。

## 3. E0—E6当前状态

| 实验 | 目标 | 当前实际状态 |
|---|---|---|
| E0 | FP16 Cube装载、布局、尾部、边界、资源 | 完成；G3独立布局缺口已补证 |
| E1 | 四种编码还原、映射与Cube语义 | 完成；2717案例调用独立回放通过，最大绝对误差0 |
| E2 | AIV展开、供给与跨核交接 | 未通过；U0通过，首个非空小样设备异常；完整失败证据已回收 |
| E3 | A格式同条件完整供给成本 | 未开始 |
| E4 | B逐行gather与连续段搬运 | 未开始 |
| E5 | 包长、消费粒度、缓冲与流水 | 未开始 |
| E6 | 冻结真实窗口完整调用 | 未开始；还缺历史冻结order/routing/rowmap |

### E0/G3已经证明什么

E0原补测有223项独立、常规/直装各17项集成及逐次重复/guard检查。后续复审发现A/B同时经过候选装载链时，共同K置换可能抵消，乘积对并不能分别证明两侧布局。

G3固定物理A单位基参照，先做144项独立B选择器，再24项正常A与60次重复，含锚定/控制共179进程233调用全部通过；2932成员哈希和6个实际旧ELF复核通过，独立性缺口闭合。没有要求整轮E0重跑。D1是E0内部已完成诊断，不是E1前的新实验。

入口：[E0总结](e0-e6-experiments/artifacts/e0-supplement/20261021-r1/summary.md)、[G3总结](e0-e6-experiments/artifacts/e0-g3/20261022-r1/summary.md)。覆盖证明限于实际测试尺寸/有限FP16，不外推无限尺寸、L0原始字节读回或性能优势。

### E1已经证明什么

四种编码各497主例，共1988；另720次重复和9小样，全部2717案例调用通过，16类非法输入在aclInit前拒绝。独立回放从原始FP16 A/cols/B重算FP64参考，并检查还原A、refs、C、debug及guard。

真实路径是**AIV解码→UB→GM→host stream同步→既定E0 AIC装载/Cube**。这只证明编码语义，不证明共享L1直达、同kernel交接、双缓冲或更快。42953成员哈希和实际源码/ELF/库已校验。

入口：[E1总结](e0-e6-experiments/artifacts/e1/20261022-r1/summary.md)、`npu/e1_probe/`、`scripts/e1_experiment.py`、`scripts/e1_replay_independent.py`。

### E2现在卡在哪里

本地1344输入及CPU参考、实际C++ host验证和2304随机调度模型通过。目标新CMake构建成功，先跑5个单缓冲小样；第一个U0完成，第二个U16/N17/Bitmap16/q1/depth1在stream同步时报`acl507015 / EZ9999 / MPU address access invalid`。bootstrap.rc=1；后面3小样未跑，1344正式批次、480次计划重复、双缓冲、长循环均未开始。

**关键前提纠正：**目标CANN9.0.0 `dav_c220/kernel_operator_data_copy_impl.h`中，UB→TSCM普通拷贝和ND2NZ重载依赖TPipe/KFC，先将UB写GM，再发送Scm消息由AIC搬入L1。逻辑“UB→L1”不等于无GM物理直达。r1原型使用静态LocalTensor，未初始化该上下文，是明确实现缺口；尚未通过设备分层复现证明是MPU异常的唯一原因。

因此，**不能只重新执行原E2 driver，也不能直接启动E3。** 原driver含`GM_A_feed=False`等原假设字段，只有在修正实际路径、元数据和验收后才能复用。`close`原分支只接受PASS；保留失败应走明确的失败检查点封存，不伪造PASS。

完整r1已本地回收：11264文件哈希、6实际源码与2二进制通过，U0精确零/未写快照与trace/3角色done/guard及输入不变独立回放通过；非空失败原始日志保留。上传或备份成功不等于E2通过。

入口：[E2完整记录](e0-e6-experiments/artifacts/e2/20261022-r1/summary.md)、[核验](e0-e6-experiments/artifacts/e2/20261022-r1/local-checkpoint-audit.json)、`npu/e2_probe/`、`scripts/e2_experiment.py`。

## 4. 下次应从哪里开始

本次交接不替代一份批准执行的E2修正版计划。规划方下一项工作：读取本地SDK原始头文件和失败现场，明确实际物理通路、对照、停止条件与分层诊断。

候选可包括同一混合kernel内显式GM工作区生产/消费与ready/release，并将GM流量/同步计入成本；若坚持无GM目标，须先证明910B2当前环境有可用路径。不能把带GM版本记成原无GM目标通过，也不能仅通过加TPipe而宣称硬件直达。

执行方收到指定计划后，在新的run/构建目录先分层验证握手、UB展开、实际搬运、AIC消费/Fixpipe，再做完整单缓冲，最后双缓冲/长循环。复用现有输入和CPU参考，但重验受改动影响的地址、同步模型和host字段。r1封存目录保持字节不变。

E0/E1不因E2失败或下载异常而重跑；如相关装载/工具链改变，再按影响范围设计必要回归。E6须先恢复历史冻结计划；8个原始NPZ不是冻结计划的替代品。

## 5. 环境与设备操作

| 项目 | 已记录环境 |
|---|---|
| 本地 | macOS15.2/arm64，Python3.12.10，NumPy2.4.4，SciPy1.17.1 |
| 设备 | Ascend910B2 64GB，Linux/aarch64，CANN9.0.0 |
| 工具 | npu-smi/driver26.1.1，GCC12.3.1，Python3.11.15，NumPy2.4.4 |
| 编译器 | CANN9.0.0的bisheng（clang15.0.5），精确版本在各轮归档 |
| API查询容量 | L1=524032、L0A=65536、L0B=65536、L0C=131072、UB=196352 B |

查询容量不是可分配容量保证；每次恢复核对SDK、SoC、设备映射，不能沿用物理6等旧卡号。当前实例`BSMUOI9QAL6YDC4U`/`dengjia-ascend910b-node02`最后确认OFF，累计2小时41分钟，[截图](e0-e6-experiments/artifacts/e2/20261022-r1/backup-complete-instance-off.png)。它是可过期的临时环境，重新租用/恢复前以控制台为准，不硬编码服务地址或凭据。

新订单付款、充值及安全提示由用户按需亲自完成；正常恢复已有实例和任务内操作按既有授权执行。每项实验结束必须回收核验、关机和GitHub同步。不能为了阅读计划擅自开卡。

Chrome下载曾显示“组织屏蔽”，但核查全部策略为空且浏览器未受组织管理；用户结束ChatGPT调试会话后亲自正常下载成功。此前组织策略归因已纠正，内部具体原因没有受控复现。遇到相似情形保留事实，不改名/改安全设置规避，不把带会话参数的URL写入公共说明。

## 6. 可恢复证据

以下封存包及展开目录随仓库保留，原始字节不改写。Git clone后可从归档重新安全解包，依据成员哈希核对。

| 证据 | 位置（相对仓库） | SHA-256 |
|---|---|---|
| G3闭合归档 | `docs/e0-e6-experiments/artifacts/e0-g3/20261022-r1/e0-g3-20261022-r1-closed.tar.gz` | `6b9fd44349c4988fe63e2b8d124519533a35932a0c379b638cbacbbdf7693eff` |
| E1完整归档 | `docs/e0-e6-experiments/artifacts/e1/20261022-r1/e1-20261022-r1-closed.tar.gz` | `d0b6ccffac78f66deca5e721b4d32a18f622e86c2cfe9c07fe0e657de8cec3ac` |
| E2失败检查点 | `docs/e0-e6-experiments/artifacts/e2/20261022-r1/e2-20261022-r1-checkpoint.tar.gz` | `db0dca9dd7811f7fae34ba569153bb0b84bfa55afe46eddaf2f13df8aa28e36f` |

E0原补测与逐次补充另在`artifacts/e0-supplement/20261021-r1/`。实际SDK头、ELF/库、构建缓存和日志在封存目录中用于来源追溯，不是可移植的现成运行环境；不要复用旧CMake绝对路径构建。

仓库中的旧文档/哈希清单含Mac绝对路径和旧远端目录，作为来源信息保留；当前入口与协作文档均使用相对链接。历史文档里指向未迁入旧项目结果的链接不代表数据已存在此仓库。

## 7. 规划与执行agent的交接

用户指定当前会话主要负责生成计划，另一个agent跑实验。双方以仓库中的计划、状态、run目录和明确commit交接，不依赖聊天上下文。

- 规划方交付：问题/假设、固定项、变量/案例矩阵、命令与新目录、oracle独立性、正确性/资源/性能门槛、停止条件、收尾产物。
- 执行方交付：起始commit、实际源码/产物哈希、完整命令/PID/返回码、设备信息、逐次数据/检查、原始失败、结论边界、本地备份、OFF凭证、下一操作、GitHub分支与commit。
- 每轮结束必须更新并push，失败也同步。独立checkout和`codex/`分支避免相互覆盖；不force push，不自动推进下一实验。

详细规则及同步命令见[协作与同步协议](AGENT_WORKFLOW.md)和[AGENTS.md](../AGENTS.md)。
