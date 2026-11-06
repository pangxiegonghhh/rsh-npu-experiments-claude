# T17 空白一试算脚本（参考实现）

复现 `第一层工作区/T17-空白一调研.md` 中的 Cora 数字，并作为 `第一层工作区/RQ2验证实验方案.md` 的参考实现。
**试算质量，不是 T1 评价器。** 纯 Python，适合 Cora 规模；大图需移植。

| 文件 | 内容 |
|---|---|
| `rq2lib.py` | 读矩阵（A0 / A1）、对称视图评价（U、T、Γ、R，全行 / 划分后、原位 / 末尾）、D 阶段（D-greedy、D-exact） |
| `methods.py` | 行序方法：RCM、SlashBurn、C10-BP、C9-Gorder / C9-S；全行成员局部搜索 `MemberLS` |
| `memberls_part.py` | 划分感知成员局部搜索 `MemberLSPart`（P-LS） |
| `hk.c` | 组内 Held–Karp（W ≤ 16），运行时自动编译到当前目录 `rq2_hk_bin` |
| `reproduce_cora.py` | 复现调研 §8 表 A、B（带自检）；`--ls` 另跑 §4.5 |
| `verify/indep_check.py` | 独立复核（numpy / scipy，不依赖 rq2lib）：`python3 -I verify/indep_check.py <mtx> <orders.json>` |

用法：在仓库外的空目录里运行 `python3 <仓库>/第一层工作区/T17-空白一试算脚本/reproduce_cora.py`，输出写到该目录的 `out/`，不写仓库。
依赖：Python 3、numpy、scipy、gcc。
