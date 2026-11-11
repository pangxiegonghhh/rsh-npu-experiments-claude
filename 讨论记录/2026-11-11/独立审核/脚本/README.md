# 独立审核会话的复算与先导脚本（2026-11-10/11）

全部脚本**只读数据、不写仓库**，只用 Python 标准库。建议一律用 `python3 -I` 运行，并在仓库目录**之外**的工作目录里运行（避免解释器从当前目录加载同名模块）。
入库前（2026-11-11）已在审核环境把每个脚本按下面的用法实跑一遍，输出与审核记录中的数字逐项一致。

| 脚本 | 对应文档 | 用法 | 应得到的关键数 |
|---|---|---|---|
| `ascend_model.py` | 02 号 §3 | `python3 -I ascend_model.py <仓库>/第一层实验结果/cora-pilot-20261104/results-cora-pilot/window_metrics.csv` | rsh 的 makespan 相对 original 为 0.775；全上 AIC 时 0.630；ρ\* = 1.712 |
| `ascend_sensitivity.py` | 02 号 §3.1 | 同上（同一个 window_metrics.csv） | 倍数 1.71 时省 22.5%；0.86–5.14 倍范围内省 13.0%–27.0% |
| `t23_merge.py` | 04 号 §3 | `python3 -I t23_merge.py <阶段1-2 results.csv> <阶段3 results.csv>` | GNN 四张 B1 0.496、C9-Gorder 0.509；C9-Gorder 有限元 0.868 且四类全有效；九张帕累托前沿 |
| `t23_time_axis.py` | 04 号 §6.1、T4 方案 §4.2 | 同上（两个 results.csv） | ogbn-products 全在 hostB；同主机八张耗时 B1 449.1、C10-BP 237.8、C9-Gorder 144.5；两种时间轴下候选内前沿集合相同 |
| `probe_rsh.py` | T4 方案 §5、§3.5 | `python3 -I probe_rsh.py <仓库根目录>` | cora 全行 α=0、k=8：ΣU = 6035（与 T23 的 B1 一致）、T = 455；孤立行在全部 α 下恒为 117 |
| `probe_part.py` | T4 方案 §5.1 | `python3 -I probe_part.py <仓库根目录>` | cora 主口径（划分后）B1 几何均值 0.7044；最好组合 α=0.25、k=8 为 0.7004（相对 0.9942） |
| `probe_pl.py` | T4 方案 §5.2 | `python3 -I probe_pl.py <仓库根目录>` | 合成幂律图（n=8000，种子 7）上 α 无益，k=16 相对 0.996 |

**数据来源：**

- `window_metrics.csv` 与 `cora.mtx`、`rsh_reorder_experiment.py` 都在仓库 `第一层实验结果/cora-pilot-20261104/` 下。
- 阶段 1–2 的 `results.csv`：在传输分支 `transfer/t22-t23-20261109` 的 `round1-compare-20261106.tar.gz` 内（包二十三推送后入库于 `第一层实验结果/round1-compare-20261106/`）。
- 阶段 3 的 `results.csv`：在传输分支 `transfer/t23-stage3-20261106` 的分片包内（尚未入库）。

**注意事项：**

- 复算 T23 数据时必须按 `tau not in ('', 'none')` 取划分后行（`'none'` 表示全行），并按 `source != 'post-E'` 取后处理之前的行。审核会话曾因漏掉前一条而得到错误的 C4-U 有限元值 0.908（正确为 0.958），记录在 04 号 §1。
- `probe_*.py` 调用的是 Cora 先导的 **Python** 实现，不是 T23 实际使用的 C++ 移植版；两者在 cora 的 α=0、k=8 上一致，但不保证全参数范围一致（T4 方案 §5.3）。
- `probe_part.py` 的评价器是审核者自写的简化版：同一评价器下各参数档位的**相对**比较自洽，但绝对值与 T23 记录有约 1.8% 偏差，不得用来替代 T23 的数值。
