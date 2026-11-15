# M11 重算结论

R1–R12结果与逐项验收见README及同名MD。核心更正为计时单位、审核中h16摊销与h1单行斜率区别、固定路径与冷热完整表。原主判据6/8不变；hot-only事后3/4；异常格判断(c)；原合成实际随机，B1无需补跑。没有PMU，机制问题仍无法归因。

## Claim Candidates

- Claim: 原“μs/矩阵”应为完整回放吞吐单位。
  - Source evidence: R1-example.csv、原host/kernel、20轮时钟。
  - Allowed wording: Cora每回放170窗口，同格相对比值不变。
  - Forbidden stronger wording: 12.5942 μs是单窗或单核延迟。
  - Uncertainty: 归一化是全卡makespan吞吐，不是隔离延迟。
  - Next check: 下游表统一单位。
  - Decision: revise

- Claim: hot-only事后3/4格降低超过25%，cold的更大相对改善主要来自ND变慢。
  - Source evidence: R3、R4全部20轮配对与访问集合重建。
  - Allowed wording: 原8格判据不变，作为敏感性与限定说明。
  - Forbidden stronger wording: 预登记hot-only通过；按行被发射数钉死已证明。
  - Uncertainty: 无PMU及动态地址trace，连续时间区组可能相关。
  - Next check: 机制要专门控制实验，不凭近等时推因果。
  - Decision: keep
