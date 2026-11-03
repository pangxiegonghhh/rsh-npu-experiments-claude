# GPU 窗口格式：原文核验与可迁移部分

核验日期：2026-10-21。定向检索窗口列压缩、位图、局部索引及尾块存储；以下五篇均阅读了原文对应方法段落。评价的是与固定 W16 / 910B 供给问题的适配程度，不按不同论文的跨平台加速比排名。

| 论文与原文位置 | 格式事实 | 对本项目的用途与限制 |
|---|---|---|
| Wang 等，**TC-GNN**，USENIX ATC 2023，§4.1、图4、算法1 | SGT 对行窗口列集合排序、去重，生成紧凑列编号；`winPartition` 描述块数，`edgeToCol` 保存映射 | 窗口内列压缩是共同基础；保留原列号才能找到 B 行。当前项目已具备这一步，不需要重新发明重排 |
| Fan、Wang、Chu，**DTC-SpMM**，ASPLOS 2024，§4.2、图5 | ME-TCF 用 `RowWindowOffset / TCOffset / TCLocalId / SparseAtoB`；16×8 块内位置用 8-bit 索引；数值另存 | 可借鉴“一份列映射＋局部位置”；迁移到16×16时位置0…255仍可用 uint8，但块 nnz 可能为256，计数必须更宽 |
| Zhao 等，**Acc-SpMM**，arXiv:2501.09251v1，2025，§3.3、图3 | BitTCF 使用8×8块，`RowWindowOffset / TCOffset / SparseAToB / TCLocalBit`，每块 uint64 位图替代逐非零局部位置 | 适合研究中等密度 tile 的编码；16×16 位图应为256 bit，不能照搬一个uint64。值流与其起点仍需描述 |
| Shi 等，**FlashSparse**，arXiv:2412.11007v1，2024，§3.5、图10 | ME-BCRS 用 `RowPointers / ColumnIndices / Values`，只保存有效列向量，最后一块不在GM中保存补齐零列；值在块内按行组织 | “存储不补尾、消费时补齐”可用于我们的16行窗口；论文8×1粒度来自GPU swap-and-transpose，不能据此把固定窗口改为8行 |
| **RSH-SpMM**，arXiv:2603.08734v1，2026，§3.2、§3.3.2 | TC部分先压缩窗口列集合，再组织8×8位图块；原文列出Row Window ID/Offset、Bitmap、Col ID，kernel另使用数值流；warp位操作展开到fragment | 借鉴结构映射与数值编码分离；GPU的共享内存、warp prefix-popcount和寄存器fragment方案不能直接当作AIC指令流程 |

原始来源：[TC-GNN 会议论文](https://www.usenix.org/system/files/atc23-wang-yuke.pdf)、[DTC-SpMM 作者论文](https://cse.hkust.edu.hk/~weiwa/papers/dtc-spmm-asplos24.pdf)、[Acc-SpMM 原文](https://arxiv.org/html/2501.09251v1)、[FlashSparse 原文](https://arxiv.org/html/2412.11007v1)、[RSH-SpMM 原文](https://arxiv.org/html/2603.08734v1)。arXiv 条目按所读版本引用，不据页面模板自动确认发表状态。

## 原文措辞中需要辨别的地方

- Acc-SpMM 把 `SparseAToB` 描述为原列索引，同时给定长度 `NumTcBlock×8`。这里应理解为块的列槽映射，不能实现成每一个 nnz 都再存一个32位原列号。
- DTC 的 `NNZ/4 elements` 是按32位存储单位计的开销；实际局部位置每项8 bit，不能误读成只保存四分之一的非零位置。
- RSH 论文正文给出格式思想和kernel伪代码，但不足以唯一确定完整二进制ABI，例如值流所有偏移和字节对齐。我们的字段契约需要自己明确，不能把自行补出的字段称为原文规定。

## 综合判断（设计推论）

没有一种格式脱离展开位置和 B 搬运路径仍能被称为“最好”。固定窗口后，最值得比较的是：稠密分形、尾列紧凑存储、bitmap＋紧凑值、uint8局部位置＋紧凑值。列映射由这些格式共享。先做同窗口、同N分块、同流水条件下的比较，才能把格式收益与其他优化区分开。

论文中的重排、负载均衡和 GPU 汇总加速比不作为本项目格式性能证据；本研究没有复现这些 GPU kernel，也不声称这几类编码构成新的存储格式发明。
