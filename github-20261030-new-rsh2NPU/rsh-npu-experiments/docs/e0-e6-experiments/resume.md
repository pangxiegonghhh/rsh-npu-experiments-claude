# 实验中断与续跑指针

更新：2026-10-22T22:25:59+08:00（北京时间；本次仅补GitHub交接入口）。

**E2尚未通过；完整远端检查点已回收并本地核验；实例已确认关机。下一步先修正装载通路与分层诊断，不启动E3，不重跑原失败bootstrap。**

## 当前结束到哪里

- E0/G3、E1已完成，原结果与备份不受此次下载问题影响。
- E2本地1344输入/CPU参照、host参数检查和2304调度模型已完成；目标新构建成功。
- E2仅U0设备调用完成，现已本地独立回放通过；首个非空U16/N17/Bitmap16/q1/depth1小样发生acl507015 MPU异常。正式批次、双缓冲、长循环及E3均未执行。
- 目标CANN9.0.0 dav_c220源码显示UB→TSCM普通拷贝/ND2NZ接口实际经GM/KFC，依赖TPipe/KFC上下文。原静态Tensor原型未初始化该上下文；这是明确实现缺口，尚未由设备分层复现证明是此次异常的唯一根因。

## 可信证据和备份

- [E2完整首轮记录](artifacts/e2/20261022-r1/summary.md)。
- [完整原始归档](artifacts/e2/20261022-r1/e2-20261022-r1-checkpoint.tar.gz)：5,849,507 B，11265成员；SHA-256 `db0dca9dd7811f7fae34ba569153bb0b84bfa55afe46eddaf2f13df8aa28e36f`。
- [核验凭证](artifacts/e2/20261022-r1/local-checkpoint-verification.json)：11264成员哈希通过。
- [源码/实际二进制/U0独立回放](artifacts/e2/20261022-r1/local-checkpoint-audit.json)：6源码、2产物通过；U0输出/快照/trace/done/padding/guard/输入通过。
- 解包目录：`docs/e0-e6-experiments/artifacts/e2/20261022-r1/device-checkpoint/`，包含实际构建产物、全部输入、构建与失败日志、SDK原始头文件。保持该封存目录不变，后续改动在新版本源码/构建/输出目录进行。
- 工作区原实现：`npu/e2_probe/`、`scripts/e2_experiment.py`。归档中的同名文件是实际执行版本。
- [E1总结](artifacts/e1/20261022-r1/summary.md)、[G3总结](artifacts/e0-g3/20261022-r1/summary.md)、[实验台账](experiment-status.md)。

## 实例状态

实例BSMUOI9QAL6YDC4U，主机dengjia-ascend910b-node02，已关机、开关off，累计2小时41分钟。[最终关机截图](artifacts/e2/20261022-r1/backup-complete-instance-off.png)。本次备份没有执行设备实验。完整原始证据已在本地，下次恢复不依赖远端残留或固定物理卡号。

用户结束Chrome自动化调试会话后亲自正常下载成功；策略页显示无政策，管理页显示未受组织管理。之前直接归因组织策略已纠正。内部具体原因未受控复现，不修改安全浏览设置。

## 下次从哪里开始

1. 先读E2总结及本地SDK头文件：`device-checkpoint/sdk-headers/kernel_operator_data_copy_impl.h`、`sdk-scm-header.txt`、`sdk-nd2nz.txt`。先把API逻辑位置与实际物理中转区分清楚，不再把TSCM接口视为无GM直达。
2. 明确修正版物理路径和验收口径：可研究同一个混合kernel内显式受控GM工作区的生产/消费与ready/release，计入GM成本；若保留无GM目标，须先独立证明当前设备的可用路径。不能用含GM路径冒充原无GM门槛。
3. 保留r1失败源码/产物，后续新目录先做握手/UB快照、搬运、AIC消费/Fixpipe等分层小样，定位并修复非空异常。只有单缓冲小样通过后，才跑单缓冲正式覆盖，再进入双缓冲、长循环和重复。
4. 原输入和CPU参照可复用；修改涉及的地址/同步模型和host检查需重新验证。A重排、W16窗口、路由及Residual归属继续冻结，不开展E3。
5. 每轮仍保存实际源码/二进制、输出、日志和哈希；本地回收核验后关机并更新本文件。

历史备份尝试记录保留在E2总结和resume-before-full-recovery.md，当前状态以本文件为准。


## GitHub交接与分工

完整工作区已上传私有仓库[pangxiegonghhh/rsh-npu-experiments](https://github.com/pangxiegonghhh/rsh-npu-experiments)。首个完整内容提交`34991f5c1ecd8a4126eb8717c28a80a75b35e488`已核对远端SHA；之后的交接文档更新见main历史。

当前会话负责规划，另一个agent负责用户指定的实验。先读[完整交接](../PROJECT_HANDOFF.md)与[每轮同步规则](../AGENT_WORKFLOW.md)；使用独立checkout和分支，每次实验结束（包括失败/中断）都要更新本文件、台账、run总结并推送，核对远端SHA。上传不改变上述E2失败结论和下一步，也不授权自动执行新实验。
