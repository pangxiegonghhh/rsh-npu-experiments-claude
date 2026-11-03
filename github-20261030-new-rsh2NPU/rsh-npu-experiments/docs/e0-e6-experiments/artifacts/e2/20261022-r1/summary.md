# E2 首轮中断记录（2026-10-22）

**E2 未通过。新构建成功，U0 调用完成；首个非空 U16/N17/Bitmap16/q1/depth1 小样在 stream 同步时报 acl507015、EZ9999、MPU address access invalid。1344 项正式批次、双缓冲和长循环均未执行，E3 未开始。**

## 已取得的证据

- 本地生成1344项输入，CPU oracle和实际C++ host验证通过；8类非法运行参数被拒绝。2304项随机调度模型通过，漏发空闲AIV ready和过早release的反例检测生效。模型结果不替代设备同步验证。
- 远端 `/data/e2-20261022-r1` 在910B2/CANN9.0.0环境成功完成新CMake构建；源码包SHA-256为 a6c10d409de8bcaad0345cd42bc0e4f1a9be74551e67fc79d6493ffe3d7517c7。
- bootstrap.rc为BOOTSTRAP_RC=1；首个U0有CALL_OK，非空小样报AIV异常，core id47，fixp_err0=0x40d3、fixp_err1=0x60。失败源码、ELF/静态库、环境、输入及原始日志保留。U0尚未独立本地回放，不能仅凭CALL_OK宣称语义门槛通过。
- 恢复会话时控制台实际为已关机、累计2小时18分钟；旧Lab连接404。主机GPU不足，只能无GPU恢复以回收证据，不能继续设备补跑。关机原因未确认，不推测是余额或人工操作。

## 发现的装载契约问题

此前把逻辑接口UB→TSCM视为无GM中转路径，是本轮原型设计中的错误。当前安装包 `aarch64-linux/asc/impl/basic_api/dav_c220/kernel_operator_data_copy_impl.h` 中，普通 `DataCopyUB2L1Impl`（约151行）及ND2NZ重载都调用 `GetKfcClient()->AllocUB`，先 `copy_ubuf_to_gm`，再发送Scm消息让AIC从GM搬入L1；还依赖TPipe/KFC上下文。原型采用静态LocalTensor且未初始化上述上下文，不能按原声明验证“直接片上交接”。

这一发现有安装包原始头文件和[实现截图](sdk-ub-to-l1-gm-relay.png)支持；官方[9.0.0 DataCopyPad说明](https://www.hiascend.com/doc_center/source/zh/canncommercial/900/API/ascendcopapi/atlasascendc_api_07_0265.html)亦明确VECIN/VECOUT→GM→TSCM的实际路径和通信开销。[9.0.0 ND2NZ接口表](https://www.hiascend.com/doc_center/source/en/CANNCommunityEdition/900/API/ascendcopapi/atlasascendc_api_07_00127.html)列的是逻辑位置，不能单凭该表推断物理直达。

**未初始化KFC/TPipe是明确代码缺口和强排查线索，尚未通过分层设备复现证明它是此次MPU异常的唯一根因。** 不把API逻辑支持、成功编译、CPU模型或U0调用当成无GM路径已成立。

## 证据封存与当前回收状态

远端检查点 `/data/e2-20261022-r1-checkpoint.tar.gz`：5,849,507字节，11265文件成员（包括成员哈希清单）；SHA-256 `db0dca9dd7811f7fae34ba569153bb0b84bfa55afe46eddaf2f13df8aa28e36f`。包括实际源码/二进制、完整输入、构建与失败日志、U0输出、SDK搬运头文件。

**Chrome下载被组织策略阻止，当前没有“保留”按钮，已请用户亲自处理。归档尚未完成本地回收/哈希验证；远端封存不等于本地备份完成。** [浏览器证据](download-blocked.png)、[远端清单抄录](checkpoint-transfer-observed.json)。不得改名、更换通道或改安全设置规避同一归档的下载拦截。

## 下次续跑

1. 先完成归档正常下载，验证整包SHA和11264成员哈希、安全解包，独立回放已有U0原始结果及实际源码/产物对应关系。
2. 核对GPU资源与实际实例状态。保留首轮失败目录；后续代码、构建、输出采用新版本目录。
3. 先修正E2物理通路前提：在910B2当前SDK上，按已发现的实现不能继续声称TSCM接口无GM中转。可研究显式受控GM环形工作区，在同一个混合kernel内做AIV生产/AIC消费和ready/release，明确计入GM传输成本；或为硬性无GM目标另核验可用路径。不能暗中用GM路径冒充原验收目标。
4. 设备分层先测握手与UB快照、显式搬运、静态AIC消费/Fixpipe，再测完整单缓冲；修复后重跑单缓冲全部，再进入双缓冲/长循环/重复，保留原覆盖，不跳到E3。
5. 每次结束回收完整证据并确认关机。当前尚无性能数据，不能给编码优劣结论。

## 本次收尾

2026-10-22 20:24:01北京时间核对：原实例BSMUOI9QAL6YDC4U已关机、开关off，累计运行2小时24分钟；[关机截图](instance-off.png)。无GPU恢复仅用于读取SDK和封存证据，没有运行新设备测试。归档下载仍被阻止且未在本地找到；不宣称完成回收。平台页面显示关机后磁盘约36小时保留期，应优先完成备份，不能依赖其长期存在。

## 用户下载反馈

用户确认“无法下载”。浏览器拦截未解决，检查点归档仍仅在远端，未完成本地整包/成员哈希验证；先前下载请求不再视为等待用户操作。实例保持OFF，不为重复尝试同一被拦截下载而开机。后续先确认平台允许的安全备份途径及远端保留状态，再恢复设备工作；不得绕过浏览器/组织安全拦截。

## 本地备份追加任务：2026-10-22T20:47:40+08:00

用户要求本地备份。核对平台官方SCP说明后无GPU恢复实例，用户亲自设置SSH密码；但实例SSH图标未显示连接指令，用户亦确认“没有登录命令”。操作菜单没有导出选项，申请公网端口提示仅包周期实例可用。本轮未更改付费方式、未修改浏览器安全设置、未执行设备实验。无GPU实例最终已关机，累计2小时34分钟；[本次关机截图](backup-instance-off.png)。

当前先对本地已有E2源码、1344输入、CPU记录、研究文档、断点与截图进行独立归档和成员哈希校验。该备份不包含尚未传回的远端实际ELF/静态库、SDK原始头文件和完整失败日志，不能替代5,849,507字节的远端检查点。远端保留状态和平台可用安全导出/SSH入口仍须优先解决。

本地现有材料备份完成：[归档](../../../../../backups/e2-local-existing-20261022.tar.gz)，5,288,446字节、10849成员，10848份文件SHA校验通过；整包SHA-256为 `926894ea9872172dd119a5156b2b27dfee871170fc2b15973f0246ddbf8775b8`。范围与核验见[本地备份凭证](local-existing-backup-verification.json)。远端检查点未接收的状态保持不变。

## GPU恢复可用后的备份重试：2026-10-22 21:22收尾

按用户授权以GPU模式启动原实例，仅做备份。远端完整归档重新计算得到5,849,507字节与原SHA-256一致，见[重算截图](remote-checkpoint-retry-sha.png)。重试原文件正常Download，Chrome仍显示“已被您的组织屏蔽”，见[拦截截图](download-retry-gpu-blocked.png)；本地Downloads中未找到归档。GPU恢复可用没有解除该下载拦截，完整远端检查点仍未接收，既有本地材料备份不变。未修改安全设置、未换名规避拦截、未运行实验。

21:22北京时间观察到原实例已关机、开关off，累计2小时36分钟；[本轮关机截图](backup-retry-gpu-instance-off.png)。下一步先解决下载政策阻拦或取得平台可用安全传输入口，再回收核验。

## 下载原因判定纠正

用户确认无DownloadRestrictions后，只读核查chrome://policy（清空过滤）显示未设置任何政策，chrome://management显示浏览器未由公司或组织管理。因此此前将提示直接归因为实际组织策略证据不足，予以纠正。自动化调试会话或扩展导致下载取消是待验证假设。未修改策略、未关闭安全浏览、未禁用扩展。

手动下载诊断交接：原实例再次无GPU运行，已在Jupyter选中原始tar.gz。准备让用户结束“ChatGPT已开始调试此浏览器”的会话后亲自正常Download，以检验自动化会话是否影响下载；尚未验证该假设。期间不继续浏览器工具调用，避免重新接管。安全提示仍交用户处理，未修改安全设置。

## 完整远端检查点回收完成：2026-10-22T21:41:44+08:00

**当前结论：备份已完整回收、E2仍未通过、实例已关机。** 用户结束浏览器自动化调试后，亲自正常下载成功。此前从“组织屏蔽”文案推断实际组织策略的说法已纠正；Chrome策略页与管理页均不支持该归因，下载恢复与结束调试会话相伴，但未做受控复现，不能进一步断定具体内部机制。

- [项目内完整归档](e2-20261022-r1-checkpoint.tar.gz)：5,849,507 B，11265成员，SHA-256 `db0dca9dd7811f7fae34ba569153bb0b84bfa55afe46eddaf2f13df8aa28e36f`。
- [整包/成员核验](local-checkpoint-verification.json)：11264份文件哈希全部通过，路径/重复/文件类型检查通过；安全解包到device-checkpoint/，原始封存文件未修改。
- [来源及U0独立回放](local-checkpoint-audit.json)：6份实际源码与预期哈希及当前工作区一致；runner为ELF、kernel静态库为ar，两份产物哈希通过。U0完整输出精确零、snapshot/trace未写、3角色done与padding、10个输入/输出缓冲guard及输入不变均通过。
- 非空U16/N17/Bitmap/q1/depth1仍为acl507015 MPU异常；bootstrap.rc=1、唯一CALL_OK及全部原始失败日志保留。没有正式批次结果，E2不记PASS，E3未开始。
- [本次关机截图](backup-complete-instance-off.png)：观察原实例BSMUOI9QAL6YDC4U已关机、开关off，累计2小时41分钟。本次仅备份和本地核验，未运行设备实验。

现在下次续跑可以完全依赖本地封存证据，不再依赖远端36小时磁盘保留。此前本文件“未回收/等待下载/实例运行”等均为带时间的历史断点，以本节和resume.md为准。下一步仍是纠正供给路径和分层设备诊断，不能重新启动原失败bootstrap。
