# M11 配对计时分析

独立重复单位为20个随机时间区组；窗口和核不是独立样本。主格8个，严格多数5/8；普通两条路径分别保留配对数据，不将最小均值当无偏选优。
描述性时间下降超过20%的主格：6/8。点置信区间上界仍低于0.8的主格：6/8。

| Cora B1主格 | 普通路径 | 平均耗时比 | 配对bootstrap95%CI | 时间下降 | 主族Holm符号检验p |
|---|---|---|---|---|---|
| cora-B1-FP16-n128-cold-p0 | p1 | 1.304968 | [1.303622, 1.306567] | -30.50% | 3.05176e-05 |
| cora-B1-FP16-n128-cold-p0 | p2 | 10.287195 | [10.274674, 10.301336] | -928.72% | 3.05176e-05 |
| cora-B1-FP16-n128-hot-p0 | p1 | 1.333074 | [1.331781, 1.334539] | -33.31% | 3.05176e-05 |
| cora-B1-FP16-n128-hot-p0 | p2 | 10.510061 | [10.497677, 10.522955] | -951.01% | 3.05176e-05 |
| cora-B1-FP16-n256-cold-p0 | p1 | 0.631226 | [0.629219, 0.633575] | 36.88% | 3.05176e-05 |
| cora-B1-FP16-n256-cold-p0 | p2 | 9.377858 | [9.370840, 9.385497] | -837.79% | 3.05176e-05 |
| cora-B1-FP16-n256-hot-p0 | p1 | 0.738258 | [0.736135, 0.740594] | 26.17% | 3.05176e-05 |
| cora-B1-FP16-n256-hot-p0 | p2 | 11.244341 | [11.224129, 11.265926] | -1024.43% | 3.05176e-05 |
| cora-B1-FP32-n128-cold-p0 | p1 | 0.643494 | [0.642916, 0.644139] | 35.65% | 3.05176e-05 |
| cora-B1-FP32-n128-cold-p0 | p2 | 9.489493 | [9.483689, 9.495095] | -848.95% | 3.05176e-05 |
| cora-B1-FP32-n128-hot-p0 | p1 | 0.746517 | [0.745180, 0.747727] | 25.35% | 3.05176e-05 |
| cora-B1-FP32-n128-hot-p0 | p2 | 11.282063 | [11.260805, 11.303714] | -1028.21% | 3.05176e-05 |
| cora-B1-FP32-n256-cold-p0 | p1 | 0.579338 | [0.578465, 0.580187] | 42.07% | 3.05176e-05 |
| cora-B1-FP32-n256-cold-p0 | p2 | 9.501868 | [9.496800, 9.507090] | -850.19% | 3.05176e-05 |
| cora-B1-FP32-n256-hot-p0 | p1 | 0.740567 | [0.739422, 0.741603] | 25.94% | 3.05176e-05 |
| cora-B1-FP32-n256-hot-p0 | p2 | 12.898441 | [12.861454, 12.936129] | -1189.84% | 3.05176e-05 |

每条路径的全部20轮、主机分配/唯一选中工作集、API次数、原始makespan见JSON和CSV。普通路径B0/B1比另见reordering-ratios.json。

## Claim Candidates

- Claim: 测试范围内三种B供数链与CPU参考相符；FP32原始A普通stride重排链与ND2NZ链相符。
  - Source evidence: GATES-PASSED.json 与实际输出哈希。
  - Allowed wording: 限定有限整数标记、Cora真实窗口与固定稠密A消费。
  - Forbidden stronger wording: 任意浮点位模式正确，或完整稀疏端到端SpMM已验收。
  - Uncertainty: 仅Cora及本合成网格。
  - Next check: 外部矩阵和完整真实稀疏A消费由后续研究决定。
  - Decision: keep


## Additional Claim Candidates

- Claim: 在预登记的Cora B1高N八格中，普通按行路径有六格平均耗时降低超过20%。
  - Source evidence: decision.json、paired-contrasts.json；20共享时间区组，六格点CI上界也小于0.8。
  - Allowed wording: 本M4回放骨架与共同gmax下，六格降低25.35%–42.07%，满足至少5/8的描述性触发条件，优势有条件成立。
  - Forbidden stronger wording: 普通搬运全面优于ND2NZ；全部稀疏SpMM至少快20%；已找到最优实现。
  - Uncertainty: 只有Cora、固定稠密A消费、两选一偏差、时间区组相关性、没有跨芯片重复。
  - Next check: 在独立矩阵和真实稀疏A端到端内核中验证，另做逐路径g调优。
  - Decision: keep

- Claim: 普通按行供数下，Cora重排在六个高N优势格仍带来约1.48倍加速。
  - Source evidence: reordering-ratios.json的p1；U64下R-sensitivity.json与figure-03。
  - Allowed wording: B1降低本回放的总供数工作，U/R/T同时变化；R仍影响ND与按行的相对选择。
  - Forbidden stronger wording: 段数已无价值；重排收益完全由降行数或纯R决定。
  - Uncertainty: 未独立干预U/R/T；synthetic地址与缓存布局随R变化。
  - Next check: 后续需要时分离U、T和R的控制变量。
  - Decision: keep

- Claim: FP32原始列块A的普通两stride搬运链可正确执行，但在本实现中耗时约为ND链的5.5倍。
  - Source evidence: GATES-PASSED.json、STRONG-ADDRESS-GATES.json、A-chain-paired-contrasts.json。
  - Allowed wording: 区分M4 host预打包直装与原始列块；当前FP32普通链正确，性能不支持直接替换ND链。
  - Forbidden stronger wording: FP32一条连续普通拷贝已验收；硬件无法普通搬运；FP16方案无条件推广到FP32。
  - Uncertainty: 只测试一个两stride普通实现，不是所有可行FP32布局。
  - Next check: 若更改第四层FP32路线，再比较替代布局的完整开销。
  - Decision: keep
