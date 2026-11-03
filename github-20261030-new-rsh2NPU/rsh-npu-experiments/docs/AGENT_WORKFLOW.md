# 规划/执行分工与每轮GitHub同步协议

用户要求：当前agent负责生成计划，另一个agent负责跑实验；整个工作区上传GitHub，每次实验结束后同步。此文件把要求落实为仓库流程，不创建定时任务，也不自动启动下一实验。

## 开始工作

1. 读`AGENTS.md`、`PROJECT_HANDOFF.md`、`e0-e6-experiments/resume.md`与当前计划。
2. 每个agent用自己的clone或worktree。先`git fetch origin`，记录起始SHA，选择明确基线；新分支用`codex/plan-...`或`codex/run-...`。
3. 同一轮只指定一个实验。规划方不默认开卡；执行方在用户指定的实验/计划范围内运行。没有新的E2修正版执行计划前，不运行r1失败driver。
4. 工作前确认没有对方未提交改动；不清理、不重置、不强推覆盖未知工作。

## 规划方写什么

计划放`docs/e0-e6-experiments/plans/<experiment>-<revision>.md`（新建下一轮计划时再建），开头写状态和适用基线SHA。至少包括：

- 要验证的问题、现有证据、尚未验证假设。
- 固定的行序/窗口/路由/数值协议、允许改变的路径或参数。
- 案例矩阵、先后顺序、最小分层小样和负例。
- 实际物理搬运路线、SDK限制与资源预算；不要把逻辑位置等同硬件直达。
- 独立oracle、每次捕获项、数量/编号完整性、guard和错误门槛。
- 正确性/资源/性能各自的判据，失败停止条件，不放宽指标掩盖问题。
- 新远端目录、构建与运行步骤、封存/本地回收/关机/同步步骤。

改动核心目标或验收口径必须在计划和交接中明说。通道恢复、备份或编译成功不等于实验通过。

## 执行方每轮保存什么

建议新run路径`docs/e0-e6-experiments/artifacts/<experiment>/<run-id>/`，已有r1封存不动。至少保存：

| 内容 | 要求 |
|---|---|
| `summary.md` | PASS/FAIL/INCOMPLETE，测了什么/未测什么，数据表、失败事实、结论边界、下一操作 |
| 实际源码及哈希 | 不能只记录工作区最新版；有源码改变应开新版本目录 |
| 实际ELF/库及哈希 | 不以二进制hash清单替代回收实际产物 |
| 环境与命令 | SoC/SDK/编译器/驱动/设备映射、命令/PID/时间/返回码、构建及运行原日志 |
| 输入/输出/中间量 | 逐次保存、数量和连续编号检查，独立参考、guard/padding/输入不变检查 |
| 检查与原始样本 | 原始数据与汇总分离；模型/CPU预检与设备结果分开记录 |
| 完整归档与成员hash | 回收到本地后核验整包、成员、源码/产物和独立重放 |
| 实例状态 | 控制台OFF确认与截图；不能仅凭shutdown请求或closed.json推定 |

执行中的进度更新写入台账/断点。中断前能做本地回收/同步就先做；如果结果、回收或关机未完成，明确标为未完成，不填默认零或虚构PASS。

## 固定收尾顺序

1. 停止本轮设备任务；保留成功与失败原始证据。
2. 封存→本地回收→完整性与独立结果核验。
3. 关闭实例，确认OFF并保存观察凭证；若有阻碍，写明最后可确认状态和下一操作。
4. 更新run总结、`experiment-status.md`、`resume.md`、相关计划。当前续跑指针保持简明，历史过程留在run总结/台账。
5. Git提交并push本轮源码、文档与证据；失败/中断同样执行。认证或网络失败不丢本地提交，记录尚未push。
6. 比较远程分支SHA与本地HEAD，交接准确分支/commit、结果路径和下一步。

GitHub同步不是NPU验收；核验本轮PASS不能替代下一轮授权。规划方读取执行方分支/commit复审后，决定下一份计划；执行方不自动跑E3或更后阶段。

## 同步命令

在仓库根目录且已配置`origin`、Git身份和认证后：

```sh
python3 scripts/sync_experiment.py --experiment E2 --run-id 20261022-r2 \
  --run-dir docs/e0-e6-experiments/artifacts/e2/20261022-r2 \
  --outcome incomplete --dry-run
```

确认待上传内容与run记录后，去掉`--dry-run`：脚本检查run总结和全局断点/台账存在，扫描明显凭据/超限文件，fetch当前远程分支并拒绝非快进冲突，stage整个未忽略工作区，commit、push、核对远端SHA。不会启动设备、修改验收数据、自动merge/rebase或force push。所有内容都会进入提交，不能混入另一个agent未完成的工作。

提交格式：`chore(experiments): archive E2 20261022-r2 (incomplete)`。脚本的上传意向记录包含outcome和源HEAD；结果SHA以Git和最终回复为准，不在同一commit中递归写入它自己的SHA。上传确认写`.private/last-push.json`供本机查看，不上传认证信息。

初次项目导入可使用等价的直接Git命令。以后认证凭据不得放仓库；新的agent在自己的环境使用正常GitHub认证，不从实验日志抄token/密码。

## 上传范围与大文件

本次保留代码、计划、8个矩阵、完整封存包、展开证据、已有本地备份与迁入来源记录。`docs/e0-e6-experiments/artifacts/`下的build/results不能被泛化忽略。只排除凭据、环境和缓存、根目录临时生成物；封存包即使含历史构建缓存也保持原始字节不变。

初始化时没有单文件超过10MiB，可用普通Git。GitHub普通Git拒绝超过100MiB的单文件；将来出现时应先采用LFS或Release产物，并将hash/下载与恢复说明一同提交，不能悄悄忽略结果目录。规范来源：[GitHub大文件说明](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)。

仓库为私有研究资料库。不要擅自改公开、删除历史失败、重写已发布历史或向无关服务传输材料。
