# E1编码语义实验：2026-10-22

## Material Passport

- Origin：用户授权“执行E1”；experiment run，内联执行与验证。
- Version：e1-20261022-r1；协议沿用W16窗口存储协议v0。
- Verification Status：PASS，设备结果、本地独立回放、归档及最终关机均已完成。
- Scope：四种A payload编码还原、原列映射、零尾部及Cube结果语义；有限FP16 A/B，FP32累加。

**E1已完成，无未解决失败或本轮必补项；下一阶段为E2，尚未开始。** Dense16、DenseTail、Bitmap16、LocalIndex16均在所列输入上正确解码并供给Cube。该结果确认编码语义可行，尚不决定哪种格式更快或应当启用。

## 结果与覆盖

| 检查 | 数量 | 结果 |
|---|---:|---|
| 正常合成窗口：10个U×6个N×4值/密度模式×4编码 | 960案例 | 全部PASS |
| 固定结构单tile，z=0…256×4编码 | 1028案例 | 全部PASS |
| 主批次合计，每编码497案例 | 1988案例 | 全部PASS |
| U17/37/63、N17/64、4编码；每配置3新进程×10次 | 720次调用 | 每次PASS |
| 构建后设备小样 | 9次调用 | 每次PASS |
| 非法输入：host验证分支，aclInit之前 | 16类别 | 全部拒绝 |
| 正式案例调用（主批次+重复） | 2708次 | 最大绝对误差0 |
| 含小样的全部案例调用 | 2717次 | 本地独立回放全部通过 |

正常窗口覆盖U=0/1/15/16/17/31/32/37/48/63，N=1/16/17/32/33/64；Kp补齐到16/32/48/64，Np为16/32/48/64。每组四种编码共享同一原始A、当次B和列映射，497组逻辑输入共1988种编码案例。单tile占用率诊断固定结构列域，允许值更新后出现零列，不将其解释为真实矩阵的列并集统计。

主批次32个进程，每进程最多64个不同案例共享ACL上下文，以暴露相邻案例残留；重复阶段3个新进程，每进程24配置×10次，A/B符号独立轮换，guard使用0x5a/0x36。正式命令开始15:36:44.304799、结束15:38:24.215703（北京时间）。该时间范围是执行日志，不能当作kernel性能。

正式2708次包含2708次decoder launch、2612次Cube kernel launch；96个U0主例由设备显式写零C，不启动Cube。另9次小样包含9次decoder和8次Cube；案例调用数、kernel launch数和内部Mmad次数分别记录，不混为同一计数。

证据：[设备汇总](device/summary.json)、[主批次检查](device/checks.json)、[重复检查](device/repeat-checks.json)、[小样检查](device/smoke-checks.json)、[非法输入检查](device/negative-checks.json)、[完整命令](device/commands.json)。

## 实际供给路径与字段处理

设备AIV读取16字节descriptor和原始payload，用UB零底板还原成16×Kp的A，同时将有效col_idx展开为Kp个B行号；无效槽填原K，指向额外的全零B行。完成后写GM，host同步，再由冻结E0 Probe的普通装载路径逐K16消费并累加。

四种payload分别按512B稠密值、16×valid_k紧凑尾块、16个行位图后接值流、局部uint8索引后接偶数字节对齐值流解析。offset使用字节单位和32B起点对齐，nnz可表示256；尾部映射不落盘。空窗口无tile descriptor，设备显式产生零输出。

每次保存完整expanded A、refs、C、decoder debug和Cube debug及其前后guard，逐个坐标与独立参考比较；不依赖最终乘积推断A和列映射正确。host每次检查descriptor/payload/col_idx/config/B及Cube配置的字节和输入guard，最终输入副本也回收。输出数量和连续编号必须等于iterations，缺档不作为通过。

该版本包含AIV→GM→AIC中转和串行stream同步，没有使用跨核共享L1或ready/release协议；不能作为E2的片上交接或性能证据。原A重排、行窗口、路由和Residual归属没有修改，原行序恢复不在本轮新增实现范围。

## 本地独立验证与来源

独立脚本从原始16×U FP16 A、原列号和B，按原列逐项累加FP64参考，不调用设备解码器或编码打包函数。2717次全部输出、还原A、refs和debug均通过，最大绝对误差0；共检查13585份逐次捕获数组、12414份最终输入副本及其guard。重复组的最终输入副本与每次输出分开计数；不声称保存了每次调用后的全部输入副本。

主批次1988个ID与精确覆盖集合相等，四种编码各497项；每个重复进程的24个ID也完整。35个正式设备进程退出码为0，日志CALL_OK合计2708，16个负例均为预期的host验证错误；每个拒绝理由与本地实际C++验证器一致。

[独立重放结果](local-replay-independent.json)、[收尾审计](completion-audit.json)、[本地覆盖审计](local/coverage-audit.json)均PASS。源码、实际ELF和两个静态库执行前后哈希一致；本地源码与实际执行源码一致，冻结E0 probe.h未改变。正式设备脚本与独立重放脚本分别保存，不在封存证据内改写数据。

本地还完成1988编码还原及原列空间oracle、实际C++ Input验证器1988有效例/16负例、实际decoder标量函数体的host内存API stub验证。这些本地检查单独记录，不替代目标CANN编译和设备执行。确定性案例数量不用于p值、置信区间或性能显著性。

## 环境、资源和产物

实例BSMUOI9QAL6YDC4U，主机dengjia-ascend910b-node02；新目录/data/e1-20261022-r1。实际Ascend910B2 / CANN9.0.0，driver/npu-smi26.1.1、GCC12.3.1、Python3.11.15，bisheng精确版本及45份SDK版本信息已归档。用户设备0→逻辑0→物理6，查询返回均0；5份SDK头哈希与E0一致。

五种SDK查询容量仍为L1=524032、L0A=65536、L0B=65536、L0C=131072、UB=196352字节。当前显式最大decoder UB为6400B；Cube显式A1+B1为10240B、A2为2048B、B2为8192B、CO1为4096B。未知框架预留不按0处理，不把查询值当最大可分配容量。

实际产物在device/build/：
- e1_runner：c25bc3094f530074a57b9db371ae35336f452ef7c70e4cbe271b244cc4e42511
- lib/libe1_decode_lib.a：c6134a26636f414e0714653ff87b6216c69ad2c6a7b49b8244669ff5eda19082
- lib/libe1_cube_lib.a：5b1bc5e57232fade82cba565f846577a7fe5c49e52773434457e00e4aae2b021

[环境](device/environment.json)、[设备映射](device/device-map.json)、[产物哈希](device/binary-sha256.json)、[执行后核对](device/source-binary-after.json)；完整新目录CMake配置/构建日志保留。host包装编译阶段有cce_global属性忽略警告，构建返回0、设备小样及全量结果通过；不称构建零警告。

## 过程异常与处置

第一次恢复实例因余额不足被平台拒绝，实例保持OFF；用户亲自充值并授权继续后恢复。初始化输入检查因JSON字段顺序不同触发字面SHA失败，发生在设备运行前；规范化全部字段及逐bin哈希确认一致后继续，原bootstrap失败日志保留。规范化manifest SHA为5ceb25e03d74ba7372482bd64a9a7ac063669feede000b200c1b38efb1afc171。

Chrome阻止HTTP下载，用户亲自保留文件后完成正常下载。没有绕过浏览器安全提示，也没有放宽数值或guard验收条件。除此以外，本轮没有未解决的构建/设备失败。

## 归档、关机与下一步

[完整封存归档](e1-20261022-r1-closed.tar.gz)：9,051,185字节、42954个成员（含哈希清单），SHA-256：

d0b6ccffac78f66deca5e721b4d32a18f622e86c2cfe9c07fe0e657de8cec3ac

[远端传输记录](transfer-info.json)通过Jupyter可见JSON读取；本地归档SHA、大小和成员数一致，42953文件哈希全部通过。原始device解包副本保持只读语义，没有修改封存文件；本轮E0旧归档原样保留。

完成本地重放后提交关机；控制台于2026-10-22 15:46:26北京时间确认“已关机”、开关off、GPU资源释放，累计运行2小时7分钟（E1前1小时51分钟）。本轮增加约16分钟；非精确计费金额。[关机截图](instance-off.png)、[关机观察记录](shutdown-observation.json)。观察时间不是精确关机时刻。

下一阶段E2：Bitmap/LocalIndex设备展开和UB→共享L1交接，先单缓冲串行ready/release，再双缓冲，q=1/2/4/8，验证长循环、奇数/末包、首尾、资源与每次输出；不得将本轮GM中转当作已验证的片上路径。E2尚未开始，待用户另行授权；仍一次只执行一个实验，结束回收并关机。
