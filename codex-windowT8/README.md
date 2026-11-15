# codex-windowT8：Mac agent 的 M11 交接资料

本目录让Mac上的另一个agent可以独立接管M11，无需读取Windows电脑的本地路径。**先读 [START-M11.md](START-M11.md)，再按其顺序读背景、源码和数据。**

分支：`codex-window`，从原 `codex/work` 的 `c5826d3a6e09143b0c9a5c333e8cfc29b4ca56f6` 分出。原分支不修改，本分支只增加本目录。

`codex-window`是Windows agent维护的资料分支。Mac agent接手M11后，在自己的独立工作目录/分支中写新代码和结果，不覆盖本资料包，也不擅自推回本资料分支。

## Mac 获取和验证

```bash
git clone --filter=blob:none --sparse --single-branch --branch codex-window \
  https://github.com/pangxiegonghhh/rsh-npu-experiments-claude.git
cd rsh-npu-experiments-claude
git sparse-checkout set codex-windowT8
cd codex-windowT8
python3 verify_bundle.py
```

也可以下载本分支ZIP，解压后进入`codex-windowT8`。不要全量拉取仓库中的历史`第一层实验结果/`。Python建议3.10以上，CPU统计复核只额外需要NumPy，macOS可直接执行，不需要CANN或NPU：

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements-audit.txt
python3 run_cpu_checks.py --out audit-output
```

复核会使用临时副本，不修改封存证据；`audit-output/verification.json`记录结果。CANN内核编译和设备测试需要你另开的ARM64 910B2实例，不能在Mac本机完成。

## 资料地图

|路径|内容与先读部分|
|---|---|
|`START-M11.md`|可直接交给新agent的完整提示词，含远程仓库的具体文件/函数/固定提交|
|`t8-m11-20261115/M11-用户原稿.md`|用户原始M11方案的逐字节副本，尚未执行|
|`background/`|8份项目背景/工作单/流程/第四层/第五层文档快照，出处见其`SOURCE-FILES.json`|
|`t8-ai-review-20261115/`|优先读M4/M5数据汇总及完整重复值MD；另有M5设计与数值解释|
|`t8-m4-20261114/`|已验收的M4源码、主manifest、全部原始输入命令表和控制脚本|
|`t8-m4-replay-20261115/`|Cora回放源码、B0/B1行列表、manifest、尾块及stride处理和输入表|
|`t8-m4-recovered-statistics-20261115/`|2592主配置+40回放配置×20轮，共52640条有效观测；300张系数表、恢复与复算核验记录|
|`t8-m5-evidence-20261115/t8-m5/`|M5所需源码、正式/质量补测CSV、块登记与作废记录、正确性gate、分析CSV/JSON；保留原相对目录|
|`t8-m5-statistical-delivery-20261115/`|M5统计包说明、原包清单、972份所选原证据的哈希核验与独立复算结论|
|`t8-cpu-prep-20261114/`|Cora B0/B1行序、窗口、原始段表与CPU输入元数据|
|`cora-offline-audit/evidence/neutron-matrices/cora.mtx`|本批CPU准备使用的原始小矩阵，用于独立参考，不需重下载数据集|
|`tools/t8_cpu_prep.py`|用户给的CPU准备脚本副本；已有CPU参考不依赖重跑|
|`audit_m4_recovered_statistics.py`、`audit_m5_statistics_offline.py`、`audit_t8_command_tables.py`|独立统计与地址表复核；建议用上面的runner运行|
|`T8-M8-进展-20261115.md`|M8状态和实例隔离说明的时间点快照，不是实时状态|
|`PACKAGE-INFO.json`、`SHA256SUMS.json`|打包范围、来源、每个文件的SHA256|

历史报告中保留的Windows绝对路径、远端`/data`路径和旧图像引用属于原始记录；执行入口和必须读取的文件均已整理在本目录中。以文字表格和CSV/JSON分析即可，无需图片。背景快照主要更新于11月13日，其“没有设备实测”等旧状态以本包11月14–15日证据为准。

## 两篇工作的命名和源码

- **AscendSPMM**：`IDMG-Lab/Ascend-SpMM`，固定提交`ca0abfeccf957d938ac8946a987f05aa6e9ec36c`；M11核对普通B拷贝、FP32 A、转置加载。
- **AscSPMM**：`LfLab-AI/Ascend-NPU-SpMM`，固定提交`875515ab73c71bc1c72574ca97811d44eac33efb`；主要参考AIV打包与READY/ACK。

第三方完整源码不在本包重复发布。`START-M11.md`列出了具体路径和函数；若想在本地阅读固定版本：

```bash
python3 fetch_upstream_sources.py --out ../m11-upstream
```

脚本只下载5份公开源文件，逐份校验Git blob SHA与SHA256，不安装、编译或运行下载的代码。附加的host/extension文件可按提示词中的固定提交URL直接读取。

## 必须保留的结论边界

- M4没有得到可直接套用的通用固定指令开销`t`；主R模型的真实回放迁移验收未通过。
- M5是单核热数据搬运微基准，合法等间距ND合并的收益不能外推成完整SpMM或任意不等间距收益。
- M4的FP32 A是host预打包后GM→L0A直接`LoadData`，不证明原始列块格式的普通GM→L1+转置链已经验收。M11必须独立检查。
- Cora回放保留真实窗口结构，但既有M4使用固定稠密A消费；它不是完整真实稀疏A的端到端SpMM。复用时写清所测范围。
- M5补测替换原来90个用例，不能把原批与补测叠加扩大样本量；有效块以登记为准，失败和作废记录不能删。
- 本包提供全部有效M4/M5统计数据，并非完整设备取证镜像。大型L1/GM回读二进制、逐指令模拟追踪、CANN安装文件、Python本机依赖与旧完整tar归档未包含。M4完整远端归档曾未整包回传，不把统计恢复说成全部二进制备份。

## M8与M11的责任隔离

M8已由Windows原agent完成20/20轮、封存并关闭原实例。禁止操作其实例 **OP08JZ85MYKCJKH3**（node02物理NPU5，PCI `0000:41:00.0`），也不要在其目录或终端执行M11。

接管agent负责先做M11的CPU准备，再开自己的910B2/CANN9实例做正确性和计时。不得在同一物理NPU上与M8混跑性能测量；任务完成或不用卡时封存、回传并关机。**M11尚未写内核、尚未跑设备实验、尚未开第二张卡。**

## M8最终结果补充（2026-11-15）

先读`t8-m8-results-20261115/M8-summary-20261115.md`，完整表格见同目录`M8-results-20261115.md`，所有16,800条有效CSV和主/分项JSON均在该目录；M8源码与登记在`t8-m8-20261115/`。

两个计时口径结论不同：含交接的实际总时间中合并直接读胜过串行打包；但Cora的两段活跃阶段相加由打包胜出。不可只取一个口径，也不声称已测M1重叠或M11普通拷贝。

`run_cpu_checks.py`会在原三项CPU复核后增加M8只读复核，检查原CSV/主分析哈希、840点×20值、1,200次NumPy拟合。源码中的`analyze.py`会写结果文件；如要完整重算，请先把结果目录复制到独立临时目录再运行，别覆盖封存证据。

M8原实例已关机，仍由原agent保管其远端证据；完整346MB二进制归档未本地回传，不在本包。详见M8目录的`remote-archive.json`。本包包含有效统计、门槛及环境，不是设备取证镜像。
