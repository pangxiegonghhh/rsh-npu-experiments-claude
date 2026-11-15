# 重算图目录

## R3-cache-sensitivity
目的：分清cold相对收益来自哪条路径变化。源R3-primary-cold-hot.csv；20区组平均耗时比，成对bootstrap点95%CI。ND在三格cold明显更慢，按行接近等时，按条在部分cold反而略快；不能推断缓存或发射的单一瓶颈。对策略的影响：给原cold相对降幅加“来自ND变慢”的限定。

## R4-hot-only
目的：展示不依赖cold条件的敏感性。源R4-hot-only-posthoc.csv，同样误差条；明确标事后，三格低于0.8、FP16N128反向。不能冒充原8格预登记门，也不据此删反向格。
