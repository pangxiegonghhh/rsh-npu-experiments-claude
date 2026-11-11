#!/usr/bin/env python3
"""T23 evaluation grid, reference definitions (派发说明 §4). Pure Python on top of rq2lib / rq3lib (the T21 / T22 pilots).

For one row order `pi` (computed on A0) it produces the T23 result rows of one matrix and one W:
  full rows      : placement 'none'    x d_rule {own, D-greedy}                     x diag {A0, A1}
  each tau       : placement 'tail-co' x d_rule {own, D-greedy}  (main protocol)  x diag {A0, A1}
                   placement 'tail'    x d_rule {own, D-greedy}  (reference)      x diag {A0, A1}
Definitions (residual set D = {v : deg_A0(v) <= tau}, the same D for A1; kept rows K in pi order are cut into W-row windows):
  own     + tail    : sigma = pi_K + D in pi order
  own     + tail-co : sigma = pi_K + co_chain(D)            (co counted on the AIC windows only; no D stage on pi_K)
  D-greedy+ tail    : rq3lib.layout_D(windows, adj, n, D_in_pi, 'tail')
  D-greedy+ tail-co : rq3lib.layout_D(windows, adj, n, D_in_pi, 'tail-co')       (T23 main protocol)
  full rows         : own = pi; D-greedy = rq2lib.dstage(pi, adj, intra='greedy')
A1 rows use the A1 adjacency for D-greedy and co (as in T22). The D-stage guard (T23 方案 §4) is applied by the planner
at analysis time from the own / D-greedy pairs; it is not a row here.

usage:  python3 -B conditions_ref.py --cora-selfcheck      (run in an empty directory; compares with expected_conditions_cora.json)
"""
import sys, os, json, math
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.dirname(HERE)
for p in (os.path.join(WS, 'T17-空白一试算脚本'), os.path.join(WS, 'T17-空白二试算脚本'), os.path.join(WS, 'T23参考实现')):
    if p not in sys.path: sys.path.insert(0, p)
from rq2lib import dstage, _gv                    # noqa: E402
from rq3lib import layout_D, co_chain             # noqa: E402

def metrics(windows, adj, sigma, W):
    pos = {v: i for i, v in enumerate(sigma)}
    U = T = G = R = 0; Rs = []
    for w in windows:
        cols = set().union(*(adj[v] for v in w))
        p = sorted(pos[c] for c in cols)
        r = (1 + sum(1 for a, b in zip(p, p[1:]) if b != a + 1)) if p else 0
        U += len(p); T += math.ceil(len(p) / 16); G += len({x // W for x in p}); R += r; Rs.append(r)
    k = len(windows); Rs.sort()
    q = lambda f: Rs[min(k - 1, int(f * k))]
    return dict(k_windows=k, sumU=U, T=T, sumGamma=G, sumR=R, meanR=round(R / k, 6), R_p50=q(0.5), R_p90=q(0.9), R_max=Rs[-1])

def grid(pi, adj0, adj1, W=16, taus=(2, 3)):
    n = len(pi); assert sorted(pi) == list(range(n))
    rows = []
    for diag, adj in (('A0', adj0), ('A1', adj1)):
        windows = [pi[i:i + W] for i in range(0, n, W)]
        g = dstage(pi, adj, W=W, intra='greedy')
        for rule, sigma in (('own', pi), ('D-greedy', g)):
            wins = windows if rule == 'own' else [sigma[i:i + W] for i in range(0, n, W)]
            rows.append(dict(diag=diag, W=W, tau='none', placement='none', d_rule=rule, **metrics(wins, adj, sigma, W)))
        for tau in taus:
            D = {v for v in range(n) if len(adj0[v]) <= tau}
            K = [v for v in pi if v not in D]; D_in_pi = [v for v in pi if v in D]
            windows = [K[i:i + W] for i in range(0, len(K), W)]
            Gv = _gv(windows, adj, n)
            cases = (('tail-co', 'own', K + co_chain(D_in_pi, Gv)),
                     ('tail-co', 'D-greedy', layout_D(windows, adj, n, D_in_pi, 'tail-co', W=W)),
                     ('tail', 'own', K + D_in_pi),
                     ('tail', 'D-greedy', layout_D(windows, adj, n, D_in_pi, 'tail', W=W)))
            for placement, rule, sigma in cases:
                assert sorted(sigma) == list(range(n))
                rows.append(dict(diag=diag, W=W, tau=tau, placement=placement, d_rule=rule,
                                 resid_frac=round(len(D) / n, 6), **metrics(windows, adj, sigma, W)))
    return rows

if __name__ == '__main__' and '--cora-selfcheck' in sys.argv:
    from rq2lib import load_cora
    import t23_candidates as C
    n, a0 = load_cora(); _, a1 = load_cora(selfloop=True)
    got = {'B0': grid(list(range(n)), a0, a1), 'C4-U': grid(C.c4(a0, 'U')[0], a0, a1)}
    path = os.path.join(HERE, 'expected_conditions_cora.json')
    if '--write-expected' in sys.argv:
        json.dump(got, open(path, 'w'), indent=1); print('expected written'); sys.exit(0)
    exp = json.load(open(path))
    ok = got == exp
    print('T23 conditions self-check:', 'OK' if ok else 'FAILED')
    if not ok:
        for m in exp:
            for a, b in zip(got[m], exp[m]):
                if a != b: print(m, a, b); break
    sys.exit(0 if ok else 1)
