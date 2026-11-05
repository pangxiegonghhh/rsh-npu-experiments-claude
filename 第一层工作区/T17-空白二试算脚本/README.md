# T17 空白二试算脚本（参考实现）

复现 `第一层工作区/T17-空白二调研.md` 中的 Cora 数字，并作为 `第一层工作区/RQ3验证实验方案.md`（T22）的参考实现。
**试算质量，不是 T1 评价器。** 纯 Python，适合 Cora 规模；大图需移植（可复用 T21 的移植代码）。
依赖同级目录 `T17-空白一试算脚本/`（`rq2lib`、`methods`、`memberls_part`、`hk.c`）与 `第一层实验结果/cora-pilot-20261104/`（矩阵、先导行序、rsh / rabbit / neutron 先导实现）。

| 文件 | 内容 |
|---|---|
| `rq3lib.py` | 显式布局评价（窗口 + 最终编号 σ）：四个数（T_full / T_inplace / T_keep）、对齐红利（切口平移 1–15 行的平均 T）、写回段数；残余点放置规则（末尾 / 末尾-co / 间隙 / 就近 / 原位，均可接 D-greedy）；在剩余行上重跑（Gorder、C9-S、C10-BP 用 A[K, :]，RCM、SlashBurn 用诱导子图，rsh / rabbit / neutron 调先导实现） |
| `reproduce_cora_rq3.py` | 复现调研 §8 表 1–4（带自检，退出码 0/1）；`--pls` 另跑表 5（划分感知 P-LS，8 个起点）；`--lsfull` 另跑表 6（全行成员局部搜索的对齐红利） |
| `verify/indep_check_rq3.py` | 独立复核（numpy / scipy，不依赖 rq2lib、rq3lib）：`python3 -I verify/indep_check_rq3.py <mtx> <layouts.json>` |

用法：在仓库外的空目录里运行 `python3 <仓库>/第一层工作区/T17-空白二试算脚本/reproduce_cora_rq3.py`，输出写到该目录的 `out_rq3/`，不写仓库
（`rq2lib` 导入时会在当前目录编译 `rq2_hk_bin`）。依赖：Python 3、numpy、scipy、gcc。
