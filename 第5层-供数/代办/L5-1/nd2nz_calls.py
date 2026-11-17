"""ND2NZ 段合并规则与逐窗口调用计数（L5-1）。L2-3、L1-2 都从这里导入。

合并规则照抄执行方 m11-work/recovered-evidence/prepare.py 的 pieces()/commands()（2026-11-16 核查）。
输入数据在第一版（标签 v1-final）里。先在仓库旁边检出第一版：
    git worktree add ../rsh-npu-v1 v1-final
自检（仓库根目录运行）：
    python3 -I -B 第5层-供数/代办/L5-1/nd2nz_calls.py
期望输出：B0 N128/N256 = 4947/4969，B1 = 2481/2521，B1/N128 单段调用 1729。
只用 Python 标准库。
"""
import json, math, os, sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]          # 仓库根目录
V1_FILES = {
    'cora_mtx': '第一层实验结果/cora-pilot-20261104/neutron-matrices/cora.mtx',
    'cora_B1':  '第一层实验结果/cora-pilot-20261104/results-cora-pilot/cora__rsh__native.json',
    'cora_C9':  '第一层实验结果/round1-compare-stage3-20261106/raw/hostB/reference_inputs/cora-reused/'
                'fbb3cab1de0f31227b065bc28d6e576d0425b50d0001c66af7f8488c1e064b4f__cora__C9-Gorder__W16__tauNone__own__b717b789b237.json',
}

def v1_path(key, v1_root=None):
    root = Path(v1_root or os.environ.get('RSH_V1') or REPO.parent / 'rsh-npu-v1')
    p = root / V1_FILES[key]
    if not p.exists():
        sys.exit(f'找不到第一版输入：{p}\n请先在仓库根目录运行 git worktree add ../rsh-npu-v1 v1-final，'
                 f'或用环境变量 RSH_V1 指向第一版目录。')
    return p

# ---- 执行方的合并规则（逐字照抄）----
def pieces(rows):
    out = []
    for k, row in enumerate(rows):
        if out and row == out[-1][0] + out[-1][1]: out[-1][1] += 1
        else: out.append([row, 1, 1, 0, k, 0, 0, 0])
    return out

def commands(rows, n, zero):
    raw = pieces(rows); out = []; i = 0
    while i < len(raw):
        p = raw[i].copy(); i += 1
        if i < len(raw) and raw[i][1] == p[1] and (raw[i][0] >= zero) == (p[0] >= zero):
            stride = raw[i][0] - p[0]
            if stride * n <= 65535:
                while (i < len(raw) and raw[i][1] == p[1] and (raw[i][0] >= zero) == (p[0] >= zero)
                       and raw[i][0] == p[0] + p[2] * stride and raw[i][4] == p[4] + p[2] * p[1]):
                    p[2] += 1; p[3] = stride; i += 1
        out.append(p)
    return out

# ---- 数据与窗口 ----
def load_mtx_A0(path):
    """读 Matrix Market，对称展开、去对角，得到 A0 的每行列号。"""
    adj = defaultdict(set); n = None
    with open(path) as f:
        for line in f:
            if line.startswith('%'): continue
            parts = line.split()
            if n is None: n = int(parts[0]); continue
            r, c = int(parts[0]) - 1, int(parts[1]) - 1
            if r != c: adj[r].add(c); adj[c].add(r)
    return n, [sorted(adj[i]) for i in range(n)]

def load_cora(v1_root=None):
    n, rows = load_mtx_A0(v1_path('cora_mtx', v1_root))
    b1 = json.load(open(v1_path('cora_B1', v1_root)))['row_perm']
    c9 = json.load(open(v1_path('cora_C9', v1_root)))['row_perm']
    return n, rows, {'B0': list(range(n)), 'B1': b1, 'C9-Gorder': c9}

def symmetric_colmap(order):
    """对称视图：列号随行号同一置换（节点 -> 新编号）。"""
    return {v: i for i, v in enumerate(order)}

def windows(n, rows, order, colmap, W=16):
    """每窗 (排序后的新列号列表, 非零数)。order：新行序（节点列表）。"""
    out = []
    for s in range(0, n, W):
        cols = set(); z = 0
        for r in order[s:s + W]:
            z += len(rows[r]); cols.update(colmap[c] for c in rows[r])
        out.append((sorted(cols), z))
    return out

def window_calls(U, N, zero):
    """按 16 行 tile 切开、尾 tile 补零；返回 (T, 调用数, 单段调用数)。
    zero 必须与真实行编号不相邻（用 n+16），否则末行与补零行会被 pieces() 连成一片。"""
    T = math.ceil(len(U) / 16); calls = single = 0
    for t in range(T):
        tile = U[16 * t:16 * t + 16]
        rows = tile + [zero + j for j in range(16 - len(tile))]
        cmd = commands(rows, N, zero)
        calls += len(cmd); single += sum(1 for p in cmd if p[2] == 1)
    return T, calls, single

if __name__ == '__main__':
    n, rows, orders = load_cora()
    for name in ('B0', 'B1'):
        ws = windows(n, rows, orders[name], symmetric_colmap(orders[name]))
        for N in (128, 256):
            r = [window_calls(U, N, n + 16) for U, _ in ws if U]
            print(f'{name} N{N}: ΣU={sum(len(U) for U, _ in ws)} T={sum(x[0] for x in r)} '
                  f'调用={sum(x[1] for x in r)} 单段调用={sum(x[2] for x in r)}')
