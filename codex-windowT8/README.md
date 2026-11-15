# codex-windowT8：T8实验资料

按M任务分别归档。进入任务目录即可找到报告、源码、数据与复核入口；跨任务背景、联合报告和Cora准备数据集中在`shared/`。

```text
codex-windowT8/
├── M4/       段数、精度与流水耗时；主实验、Cora回放及统计
├── M5/       ND/ND2NZ跨段搬运；合法合并与单段对照
├── M8/       直接读B与AIV打包；20轮设备测量及结果
├── M11/      普通拷贝替代ND2NZ；用户方案与接管提示词
├── shared/   项目背景、共同CPU输入、联合报告、历史复核记录
├── run_cpu_checks.py
├── verify_bundle.py
├── PACKAGE-INFO.json
└── SHA256SUMS.json
```

|任务|阅读入口|归档时的状态|
|---|---|---|
|M4|[M4/README.md](M4/README.md)|设备数据已完成；模型迁移验收未通过，不能把拟合系数当通用固定指令开销|
|M5|[M5/README.md](M5/README.md)|设备数据及补测已完成；收益范围为单核热数据搬运微基准|
|M8|[M8/README.md](M8/README.md)|20/20轮完成，16,800条有效记录；原实例已关机|
|M11|[M11/START-M11.md](M11/START-M11.md)|待接管；本包没有已完成的M11内核或设备结果|
|共享资料|[shared/README.md](shared/README.md)|背景、B0/B1独立CPU参考、M4/M5联合报告|

M11接管agent先读[完整提示词](M11/START-M11.md)，再按其中顺序读用户原稿、背景、既有证据和上游源码。提示词内资料路径均以本目录为基准。

## 获取与验证

本资料位于`codex-window`分支；原`codex/work`分支不修改。建议Mac agent稀疏克隆，避免下载仓库庞大的历史结果：

```bash
git clone --filter=blob:none --sparse --single-branch --branch codex-window \
  https://github.com/pangxiegonghhh/rsh-npu-experiments-claude.git
cd rsh-npu-experiments-claude
git sparse-checkout set codex-windowT8
cd codex-windowT8
python3 verify_bundle.py
```

Python 3.10以上可做文件校验；统计复算另需NumPy，可在macOS CPU执行，无需CANN或NPU：

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements-audit.txt
python3 run_cpu_checks.py --out audit-output
```

四项复核覆盖M4模型、独立命令表、M5统计及M8统计。M4在临时副本中复算，其余复核只读原证据；结果写入`audit-output/verification.json`。不要直接运行会覆盖封存结果的旧分析脚本，完整重算时先复制到独立工作目录。

## 目录与证据说明

各任务内部保留原日期目录和证据相对结构；原始命令表、CSV/JSON和C++内核保持原字节。路径变更及前后哈希见[整理核验记录](shared/verification/reorganization.json)，当前完整清单见`SHA256SUMS.json`。历史报告保留当时的Windows路径、远端路径及图片引用，当前入口以各任务README为准。其他AI分析可直接使用MD表格与原始CSV/JSON。

本包提供有效统计、源码和所选正确性/环境证据，不是完整设备取证镜像；大型回读二进制、旧完整tar及CANN安装文件未纳入。M8完整远端归档范围见[M8归档登记](M8/t8-m8-results-20261115/remote-archive.json)。

背景快照主要更新于2026-11-13；旧文档中的设备进度以11月14–15日实测记录为准。M4没有已验证通用`t`；M4回放使用真实窗口结构和固定稠密A消费，不能称完整真实SpMM。M5补测替换原来对应用例，不能叠加扩大样本量。M8实际含交接总时间与活跃阶段时间之和的结论不同，先读[M8摘要](M8/t8-m8-results-20261115/M8-summary-20261115.md)。

## M11交接与隔离

工作名称统一为**AscendSPMM**（`IDMG-Lab/Ascend-SpMM`）与**AscSPMM**（`LfLab-AI/Ascend-NPU-SpMM`）。固定提交、具体文件与函数均在[M11提示词](M11/START-M11.md)。可从本目录下载5份指定公开源文件，只校验和保存，不编译或执行：

```bash
python3 M11/fetch_upstream_sources.py --out ../m11-upstream
```

`codex-window`由Windows agent维护。Mac agent在独立工作目录/分支中写M11代码和结果，避免覆盖本资料包或与原agent相互覆盖。

M8原实例`OP08JZ85MYKCJKH3`（node02物理NPU5，PCI `0000:41:00.0`）已关机，不操作其实例。M11接管agent先做CPU准备，再使用自己的910B2/CANN9实例；不用卡时封存、回传并关机。M11在本次整理时仍未开始设备实验，未由本agent租第二张卡。
