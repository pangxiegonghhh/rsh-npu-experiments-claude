# 包十五：内容与用法（给用户）

## 内容

| 文件 | 作用 |
|---|---|
| `pkg15-0001.patch` | 规划方提交（作者 planner）：RQ2 方案加 C6 / C6-M 对齐修补，T21 补跑说明、改后的 `c6.py`、回放脚本与预期值，讨论记录，代办 / 流程图 / README 同步 |
| `apply_pkg15.sh` | 一键应用：核对补丁哈希 → 树哈希 → 前置哈希 → `git am` → 应用后树哈希 → 应用后哈希；任何不符即停；不推送；可重复运行 |
| `pkg15-sha256-before.txt` / `-after.txt` | 改动前 4 个文件、改动后 10 个文件的 sha256 |
| `AGENT-README.md` | 给执行方 agent 的说明（应用本包 + T21 补跑） |

## 用法

1. 用「写入文件夹」把本包写到 `第一层工作区/agent下载文件区/`（会生成 `rsh_pkg15/` 子目录）。
2. 让执行方 agent 读 `rsh_pkg15/AGENT-README.md`：先跑 `apply_pkg15.sh`，再按 `第一层工作区/T21补跑-C6对齐修补/说明.md` 做补跑。
3. 推送由你决定（`git push origin HEAD:main`）。推送后提交号会变，核验以树哈希为准：应用后应为 `ca3af5408b13a8ec9a424452649ebe943a902d19`。
4. 补跑交回的 `第一层实验结果/rq2-c6align-YYYYMMDD/` 由你入库，规划方再核验、并入 T21 分析。

## 起点与校验值

| 项 | 值 |
|---|---|
| 起点树哈希（远端 main `c6da5f8`） | `ff969ff7806c3eb5cdf0b1abbf954011b63ff95f` |
| 应用后树哈希 | `ca3af5408b13a8ec9a424452649ebe943a902d19` |
| `pkg15-0001.patch` sha256 | `96f44d14d05c404fc4410e04e68da0fc0c74d18ea853fba54b40f97e6b6e4aae` |
