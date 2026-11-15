# 新增控制波动复核

【事后补充】同批FP16/N128按行Cora控制均值11.749101 μs/回放、SD=1.514371，逐轮范围9.722787–12.838434，呈约9.72与12.83两档；ND控制仍约9.621。该格比原M11的均值配对比变化约−8.39%，其他三个控制比值变化均小于0.3%。所有轮保留；不按双峰划组重算主门，不把哨兵通过当作所有配置稳定的证明。该现象进一步阻止将异常简单归因为固定blockCount=8惩罚；测量故障/运行状态/流水几何交互仍分不开。以同批与原M11两套参考计算B2，4格偏差都仍超过30%。

| block | case_id | us_per_replay |
|---|---|---|
| 0 | M11b-B2-cora-B1-control-FP16-n128-hot-p1 | 12.828761 |
| 1 | M11b-B2-cora-B1-control-FP16-n128-hot-p1 | 9.728358 |
| 2 | M11b-B2-cora-B1-control-FP16-n128-hot-p1 | 12.829504 |
| 3 | M11b-B2-cora-B1-control-FP16-n128-hot-p1 | 12.824989 |
| 4 | M11b-B2-cora-B1-control-FP16-n128-hot-p1 | 9.722795 |
| 5 | M11b-B2-cora-B1-control-FP16-n128-hot-p1 | 9.726965 |
| 6 | M11b-B2-cora-B1-control-FP16-n128-hot-p1 | 12.832712 |
| 7 | M11b-B2-cora-B1-control-FP16-n128-hot-p1 | 12.828973 |
| 8 | M11b-B2-cora-B1-control-FP16-n128-hot-p1 | 12.838057 |
| 9 | M11b-B2-cora-B1-control-FP16-n128-hot-p1 | 9.722787 |
| 10 | M11b-B2-cora-B1-control-FP16-n128-hot-p1 | 9.790399 |
| 11 | M11b-B2-cora-B1-control-FP16-n128-hot-p1 | 12.834777 |
| 12 | M11b-B2-cora-B1-control-FP16-n128-hot-p1 | 12.831821 |
| 13 | M11b-B2-cora-B1-control-FP16-n128-hot-p1 | 12.831185 |
| 14 | M11b-B2-cora-B1-control-FP16-n128-hot-p1 | 12.826440 |
| 15 | M11b-B2-cora-B1-control-FP16-n128-hot-p1 | 12.838434 |
| 16 | M11b-B2-cora-B1-control-FP16-n128-hot-p1 | 12.835065 |
| 17 | M11b-B2-cora-B1-control-FP16-n128-hot-p1 | 9.735212 |
| 18 | M11b-B2-cora-B1-control-FP16-n128-hot-p1 | 12.837396 |
| 19 | M11b-B2-cora-B1-control-FP16-n128-hot-p1 | 9.737396 |
