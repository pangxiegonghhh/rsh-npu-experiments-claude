# 环境接收检查笔记

日期：2026-10-20（北京时间）

## 来源
- 用户提供的交接文件：`/Users/Zhuanz/Desktop/研究生规划/rsh-spmm-910b/RSH-910B-完整项目交接材料.md`
- 旧项目的 `续跑说明.md`、`恢复环境.md`、`项目资料总览.md`。
- 当前工作目录与本地工具检查。

## 已确认
- 新工作目录初始只有 `.git`，尚无代码、输入或结果。
- 当前目录及已检查的父目录未发现 AGENTS.md。
- 旧项目目录可读，含代码、输入、结果、恢复脚本与备份入口。
- 交接覆盖六主版本与 D0–D3，未提出本轮需要补跑的任务。
- 资料中的后续候选路线是固定 J 窗口，诊断 Cube 操作数供给；尚未证明 B 供数是主瓶颈。
- 资料记载的实验平台为 Ascend 910B2 / 64 GB、CANN 9.0.0；属于历史设备环境。
- 最近历史关机核实时间是 2026-10-19 15:32:29（北京时间），本轮没有查询实时设备状态。

## 结论边界
- 本轮尚未审计全部原始数据、重新计算统计或核验备份整体哈希。
- 旧文档中的任务建议与历史操作约定不自动构成本轮授权。

## 本地工具与隔离核对
- macOS 15.2，Darwin arm64。
- Python 3.12.10：`/Library/Frameworks/Python.framework/Versions/3.12/bin/python3`。
- 已安装包元数据：NumPy 2.4.4、SciPy 1.17.1、PyTorch 2.12.0；未做运行时兼容性测试。
- `torch_npu` 不可发现；PATH 未发现 uv、cmake、npu-smi、ccec；默认 Ascend 目录不存在。
- Git 根目录是当前新项目；`.git` 是本地目录、非符号链接，无 commondir 标记，无 remote 配置；main 尚无提交。
- 旧项目核心 Python/C++ 源码、D3 protocol/analysis/shutdown 文件及恢复包存在。
- D3 恢复包大小为 311373287 字节，与交接记载一致；本轮未重算 SHA256。
- 额外阅读 D3 的结果解读和机制解读，主要结论与交接一致；其中旧“下次建议”仍只作历史背景。

## 待确认
- 用户已选择复制旧代码到新项目，独立修改。

## 代码迁入结果
- 复制 146 文件 / 17952225 字节：源码、脚本、测试、设计资料、8 个原始 NPZ 输入、requirements 与归档交接文档。
- 每个迁入文件 SHA256 与来源相同；使用普通复制，不共享符号链接或硬链接。
- 没有迁入 results、cases、build、artifacts、旧 Git 或缓存。
- Python 语法检查 98 文件通过；9 个已有 CPU 测试通过。
- 清单为 `迁入清单.json`，核验与测试日志为 `docs/migration-20261020/`。
- 新入口为 README.md；依赖历史结果的脚本尚不具备独立运行材料；不自动从旧目录补读。


## 2026-10-22T22:25:59+08:00 GitHub初始化与交接

已创建私有仓库`pangxiegonghhh/rsh-npu-experiments`，完整内容快照93584文件/448194197逻辑字节，首提交`34991f5c1ecd8a4126eb8717c28a80a75b35e488`与远端main一致。22端口推送断开，GitHub官方SSH443认证及推送成功。用户授权仓库读写Deploy key并完成再次验证，未复制私钥。完整情况、两角色协议、每轮同步辅助和上传凭证分别在`docs/PROJECT_HANDOFF.md`、`docs/AGENT_WORKFLOW.md`、`scripts/sync_experiment.py`、`docs/github-sync/initial-import.md`。未运行设备实验，E2失败状态不变。
