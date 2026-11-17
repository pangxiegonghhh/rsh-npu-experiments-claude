"""L2-3：逐窗口「补齐行 ÷ ND 调用」分布与按窗口选路的收益（Cora）。

仓库根目录运行（需先 git worktree add ../rsh-npu-v1 v1-final）：
    python3 -I -B 第2层-分流/代办/L2-3/run_l23.py
输出：终端打印各表；完整数写到同目录 outputs/L2-3-cora.json。只用标准库，约 10 秒。
"""
import json, statistics as st, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / '第5层-供数' / '代办' / 'L5-1'))
from nd2nz_calls import load_cora, symmetric_colmap, windows, window_calls

BASE = (23.5, 67.5, 140.0)                      # a ns/补齐行，b ns/ND调用，c ns/块（M11c 第三轮审核，热档一阶值）
COEF = {'base': BASE, 'nd_cheap': (23.9, 67.0, 112.0), 'nd_dear': (23.1, 75.3, 142.0)}
MERGED_MULT = (1.0, 1.5, 2.0)                   # 敏感性：合并调用（ndNum>1）单价 = 倍数 × b
# 实测（M11 R6 表，FP32/N128/hot，μs/完整回放），×24 换成 μs·核
MEASURED = {('B0', 'row'): 10.723917808, ('B1', 'row'): 7.242862787,
            ('B0', 'nd'): 18.016885274, ('B1', 'nd'): 9.702202227}

def per_window(n, rows, order, colmap, N):
    out = []
    for U, z in windows(n, rows, order, colmap):
        if not U: continue
        T, calls, single = window_calls(U, N, n + 16)
        out.append({'U': len(U), 'T': T, 'calls': calls, 'single': single, 'nnz': z})
    return out

def costs(per, coef=BASE, mm=1.0):
    a, b, c = coef
    row = [a * 16 * p['T'] for p in per]
    nd = [b * (p['single'] + mm * (p['calls'] - p['single'])) + c * p['T'] for p in per]
    best = [min(x, y) for x, y in zip(row, nd)]
    R, D, B = sum(row), sum(nd), sum(best)
    return {'all_row_us': R / 1e3, 'all_nd_us': D / 1e3, 'best_us': B / 1e3,
            'gain_vs_best_uniform_pct': 100 * (1 - B / min(R, D)),
            'nd_windows': sum(1 for x, y in zip(row, nd) if y < x)}

def ideal(per, coef=BASE):
    a, b, c = coef     # 每块一次调用 + 有补齐的块再一次；U 不变
    return sum(b * (p['T'] + (1 if p['U'] % 16 else 0)) + c * p['T'] for p in per) / 1e3

def rank_switch(per, coef=BASE):
    a, b, c = coef     # AIV 代价暂按 Ascend-SpMM（∝ 非零数）；比较「非零数/AIC 代价」与密度「非零数/U」
    aic = [min(a * 16 * p['T'], b * p['calls'] + c * p['T']) for p in per]
    dens = [p['nnz'] / p['U'] for p in per]; ours = [p['nnz'] / x for p, x in zip(per, aic)]
    idx = range(len(per)); res = {}
    for f in (0.25, 0.5, 0.75):
        k = round(f * len(per))
        A = set(sorted(idx, key=lambda i: -dens[i])[:k]); B = set(sorted(idx, key=lambda i: -ours[i])[:k])
        res[str(f)] = len(A - B)
    return res

def main():
    n, rows, orders = load_cora()
    out = {'coef': COEF, 'measured_FP32_N128_hot_us_core': {f'{k[0]}/{k[1]}': v * 24 for k, v in MEASURED.items()}, 'cases': {}}
    print('## 1. 模型复现实测（FP32/N128 热档，μs·核）')
    for name in ('B0', 'B1'):
        per = per_window(n, rows, orders[name], symmetric_colmap(orders[name]), 128)
        cst = costs(per)
        for path, key in (('row', 'all_row_us'), ('nd', 'all_nd_us')):
            m = MEASURED[(name, path)] * 24
            print(f'{name} {path}: 模型 {cst[key]:.1f}  实测 {m:.1f}  偏差 {100 * (cst[key] / m - 1):+.1f}%')
    print('\n## 2. 列号是否随行号一起换（B1，N128）')
    for label, cm in (('对称（列号随行号）', symmetric_colmap(orders['B1'])), ('列号保持原编号', {i: i for i in range(n)})):
        per = per_window(n, rows, orders['B1'], cm, 128)
        T = sum(p['T'] for p in per); K = sum(p['calls'] for p in per)
        print(f'{label}: 调用 {K}，补齐行/调用 {16 * T / K:.2f}'); out[f'colmap/{label}'] = {'T': T, 'calls': K}
    print('\n## 3. 各行序、各 N 的收益与敏感性')
    for name, order in orders.items():
        for N in (128, 256):
            per = per_window(n, rows, order, symmetric_colmap(order), N)
            T = sum(p['T'] for p in per); K = sum(p['calls'] for p in per)
            rpc = [16 * p['T'] / p['calls'] for p in per]
            case = {'windows': len(per), 'sumU': sum(p['U'] for p in per), 'T': T, 'calls': K,
                    'single': sum(p['single'] for p in per), 'rows_per_call': 16 * T / K,
                    'rpc_deciles': [round(q, 2) for q in st.quantiles(rpc, n=10)],
                    'windows_rpc_ge_4.6': sum(r >= 4.6 for r in rpc),
                    'ideal_nd_us': ideal(per), 'rank_switch_by_prefix': rank_switch(per),
                    'models': {f'{cn}|merged×{mm}': costs(per, cv, mm) for cn, cv in COEF.items() for mm in MERGED_MULT}}
            base = case['models']['base|merged×1.0']
            case['ideal_vs_all_row_pct'] = 100 * (1 - case['ideal_nd_us'] / base['all_row_us'])
            gains = [m['gain_vs_best_uniform_pct'] for m in case['models'].values()]
            print(f"{name:9s} N{N}: 补齐行/调用 {case['rows_per_call']:.2f}，≥4.6 的窗口 {case['windows_rpc_ge_4.6']}/{len(per)}，"
                  f"全按行 {base['all_row_us']:.1f}，全ND {base['all_nd_us']:.1f}，逐窗取优 {base['best_us']:.1f}，"
                  f"收益 {base['gain_vs_best_uniform_pct']:.2f}%（敏感性 {min(gains):.2f}–{max(gains):.2f}%），"
                  f"理想ND {case['ideal_nd_us']:.1f}（比全按行快 {case['ideal_vs_all_row_pct']:.1f}%），"
                  f"排序换边 {case['rank_switch_by_prefix']}")
            out['cases'][f'{name}/N{N}'] = case
    print('\nB1/N128 逐窗「补齐行/调用」十分位：', out['cases']['B1/N128']['rpc_deciles'])
    (HERE / 'outputs').mkdir(exist_ok=True)
    json.dump(out, open(HERE / 'outputs' / 'L2-3-cora.json', 'w'), ensure_ascii=False, indent=1)

if __name__ == '__main__':
    main()
