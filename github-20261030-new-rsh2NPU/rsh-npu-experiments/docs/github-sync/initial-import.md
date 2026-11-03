# 首次完整工作区上传凭证

核验时间：2026-10-22T22:25:59+08:00。

私有仓库：[pangxiegonghhh/rsh-npu-experiments](https://github.com/pangxiegonghhh/rsh-npu-experiments)，默认分支`main`。

首个完整内容提交：`34991f5c1ecd8a4126eb8717c28a80a75b35e488`；tree：`aaea9e1f6cdde8af552422838749837637833381`。Git推送成功后，`git ls-remote origin refs/heads/main`返回同一SHA；GitHub连接器按该commit读取README成功。

## 范围与核验

- 内容快照93584个文件，逻辑大小448194197字节；Git传输包47.52 MiB。保留源码、8个矩阵、计划、状态、完整归档及展开的实际ELF/库、构建与失败日志、输入输出和核验凭证。
- `.private/`、密码/私钥/会话凭据、虚拟环境和缓存不上传；`.private/`跟踪文件数为0。预检见[扫描结果](../github-sync-preflight.json)。
- 9项现有CPU测试通过，20处新交接文档相对链接通过；同步脚本dry-run通过；G3/E1/E2三个主要原始归档哈希未变。
- 首次22端口推送遭远端断开，没有宣称成功；改用GitHub官方SSH 443端口后完成。已固定官方主机密钥并启用连接超时/保活。
- 用户明确授权本仓库读写Deploy key并亲自完成GitHub再次验证；密钥权限仅用于本仓库，私钥留在本机。其他环境需自行正常认证。

本凭证描述上述已核验的完整内容提交，随后随文档更新同步；最终交接版本以GitHub `main`最新commit为准，不在同一commit里递归写自己的SHA。

## 当前研究状态与下一次交接

本轮仅整理项目、提交与上传，没有租卡、开机或执行设备实验。E0/G3、E1已完成；E2首个非空小样失败，完整现场已回收；E3—E6未开始。最近设备观察为OFF，累计2小时41分钟，仍以[当前断点](../e0-e6-experiments/resume.md)为准。

新agent先读[完整项目交接](../PROJECT_HANDOFF.md)、[续跑位置](../e0-e6-experiments/resume.md)、[实验台账](../e0-e6-experiments/experiment-status.md)和[协作同步规则](../AGENT_WORKFLOW.md)。规划方下一项是明确E2修正版通路与分层诊断；执行方不能直接重跑r1失败bootstrap，也不自动进入E3。

以后每轮PASS/FAIL/INCOMPLETE均保存证据、更新状态/断点、确认关机并commit/push，核对远端SHA。提供`scripts/sync_experiment.py`辅助执行；这是每轮收尾要求，不是后台自动调度。
