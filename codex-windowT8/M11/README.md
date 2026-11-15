# M11：普通拷贝与ND2NZ供数对照

1. [接管提示词](START-M11.md)：远程阅读清单、参数初查、设备与实验边界。
2. [用户原始方案](M11-用户原稿.md)：本次待执行内容。
3. [上游源码读取脚本](fetch_upstream_sources.py)：按固定提交下载并校验源码，不编译或执行。

提示词里的资料路径均以`codex-windowT8/`根目录为基准。M11在这次归档时仍未开始设备实验；M4/M5/M8资料分别见相邻任务目录，共享背景和Cora准备见`../shared/`。

从资料根目录可运行：`python3 M11/fetch_upstream_sources.py --out ../m11-upstream`。
