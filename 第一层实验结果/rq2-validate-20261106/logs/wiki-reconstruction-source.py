#!/usr/bin/env python3
"""把 SNAP 的 wiki-RfA 投票网络转成 Matrix Market (.mtx) 格式。

背景：SuiteSparse 官方文件服务器 sparse-files.engr.tamu.edu 目前全站返回
403 AccessDenied（S3 桶权限问题），官方 tar.gz 下不了。这里用同一份数据的
上游来源 SNAP（snap.stanford.edu/data/wiki-RfA.html）重建 Matrix Market 文件。

规则（与 SuiteSparse 版本对齐）：
  - 节点 = 维基百科用户，编号 1..n（n = 11380）
  - 边 (src -> tgt) 有向，权重 = RfA 投票结果 +1 / -1 / 0
  - 同一对用户的多次投票只保留最后一次
  - 跳过投票人/被投票人为空的记录（账号被隐藏或注销），约 1600+ 条；
    但这些用户名本身仍计入节点表，因此会出现少量全零行/列

用法:
  gzcat wiki-RfA.txt.gz | python3 snap_to_mtx.py > wiki-RfA.mtx
"""
import sys

src = None
tgt = None
vot = 1
edges = {}
names = set()


def flush():
    global src, tgt, vot
    if src and tgt:
        edges[(src, tgt)] = vot  # 同一对用户多次投票只保留最后一次的值
    src = tgt = None
    vot = 1


for raw in sys.stdin:
    line = raw.rstrip("\n")
    if line.startswith("SRC:"):
        flush()
        src = line[4:].strip()
        if src:
            names.add(src)
    elif line.startswith("TGT:"):
        tgt = line[4:].strip()
        if tgt:
            names.add(tgt)
    elif line.startswith("VOT:"):
        try:
            vot = int(line[4:].strip())
        except ValueError:
            vot = 1
flush()

nodes = sorted(names)
index = {n: i + 1 for i, n in enumerate(nodes)}

out = sys.stdout
out.write("%%MatrixMarket matrix coordinate integer general\n")
out.write("% wiki-RfA: Wikipedia Requests for Adminship voting network (signed)\n")
out.write("% rebuilt from SNAP wiki-RfA.txt (snap.stanford.edu), SuiteSparse-compatible\n")
out.write("%% rows=%d cols=%d nnz=%d asymmetric\n" % (len(nodes), len(nodes), len(edges)))
out.write("%d %d %d\n" % (len(nodes), len(nodes), len(edges)))
for (a, b), v in sorted(edges.items(), key=lambda kv: (index[kv[0][0]], index[kv[0][1]])):
    out.write("%d %d %d\n" % (index[a], index[b], v))
