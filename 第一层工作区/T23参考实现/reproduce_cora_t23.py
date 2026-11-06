#!/usr/bin/env python3
"""T23 step 0: Cora self-check for the pure-Python candidates (C2-LSH, C3-W1/W4/A, C3-W4-noP, C4-U/T, C7-I).

usage (run in an empty directory outside the repo; outputs go to ./out/):
    python3 <repo>/第一层工作区/T23参考实现/reproduce_cora_t23.py
First line printed: 'T23 Cora self-check: OK' (exit 0) or 'T23 Cora self-check: FAILED ...' (exit 1).
Checks (a) the SHA-256 of every row order and (b) the metrics below against EXPECT, exact for integers, 0.005 for means.
Metrics: W = 16, symmetric view. Full rows: A0 and A1, own order and +D-greedy. Partitioned (tau = 2, 3, residual set by A0
degree): main protocol of T23 §4 = D-greedy + tail-co (rq3lib.layout_D), A0 and A1, plus the tail rule for reference.
"""
import sys, os, json, csv, hashlib
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.dirname(HERE)
for p in (HERE, os.path.join(WS, 'T17-空白一试算脚本'), os.path.join(WS, 'T17-空白二试算脚本')):
    if p not in sys.path: sys.path.insert(0, p)
from rq2lib import load_cora, evaluate, dstage            # noqa: E402
from rq3lib import layout_D, win_metrics, resid_set       # noqa: E402
import t23_candidates as C                               # noqa: E402

OUT = os.path.join(os.getcwd(), 'out'); os.makedirs(OUT, exist_ok=True)
n, adj0 = load_cora(); _, adj1 = load_cora(selfloop=True)

def sha(o): return hashlib.sha256(json.dumps(o).encode()).hexdigest()

orders, stats, rows = {}, {}, []
for name, f in C.CANDIDATES.items():
    o, st = f(adj0)
    orders[name] = o; stats[name] = st
    r = dict(member=name, order_sha256=sha(o))
    for tag, adj in (('A0', adj0), ('A1', adj1)):
        e = evaluate(o, adj); g = evaluate(dstage(o, adj, intra='greedy'), adj)
        assert e['sumU'] == g['sumU'] and e['sumG'] == g['sumG'], name     # D stage keeps membership
        r.update({f'{tag}_U': round(e['U'], 4), f'{tag}_T': e['T'], f'{tag}_Gamma': round(e['G'], 4),
                  f'{tag}_R_own': round(e['R'], 4), f'{tag}_R_Dgreedy': round(g['R'], 4)})
    for tau in (2, 3):
        D = resid_set(adj0, tau)                      # residual set from A0 degrees, also used for A1
        Dset = set(D)
        kept = [v for v in o if v not in Dset]; D_in_pi = [v for v in o if v in Dset]
        windows = [kept[i:i + 16] for i in range(0, len(kept), 16)]
        for tag, adj in (('A0', adj0), ('A1', adj1)):
            s_co = layout_D(windows, adj, n, D_in_pi, rule='tail-co')
            s_tl = layout_D(windows, adj, n, D_in_pi, rule='tail')
            m_co = win_metrics(windows, adj, s_co); m_tl = win_metrics(windows, adj, s_tl)
            assert m_co['sumU'] == m_tl['sumU'] and sorted(s_co) == list(range(n))
            r.update({f'tau{tau}_{tag}_k': m_co['k'], f'tau{tau}_{tag}_U': round(m_co['U'], 4), f'tau{tau}_{tag}_T': m_co['T'],
                      f'tau{tau}_{tag}_R_tailco_Dgreedy': round(m_co['R'], 4), f'tau{tau}_{tag}_R_tail_Dgreedy': round(m_tl['R'], 4)})
    rows.append(r)

json.dump(orders, open(os.path.join(OUT, 'orders_t23.json'), 'w'))
json.dump(stats, open(os.path.join(OUT, 'stats_t23.json'), 'w'), indent=1)
with open(os.path.join(OUT, 'table_t23.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

EXPECT_PATH = os.path.join(HERE, 'expected_cora_t23.json')
if '--write-expected' in sys.argv:          # planner only: (re)generate the expected table
    json.dump({r['member']: r for r in rows}, open(EXPECT_PATH, 'w'), indent=1, ensure_ascii=False)
    print('expected table written'); sys.exit(0)
EXPECT = json.load(open(EXPECT_PATH))
bad = []
for r in rows:
    e = EXPECT[r['member']]
    for k, v in e.items():
        got = r[k]
        if isinstance(v, float) or isinstance(got, float):
            if abs(got - v) > 0.005: bad.append((r['member'], k, got, v))
        elif got != v: bad.append((r['member'], k, got, v))
print('T23 Cora self-check:', 'OK' if not bad else f'FAILED {bad[:10]}')
for r in rows:
    print(r['member'], r['order_sha256'][:16], 'A0 U', r['A0_U'], 'T', r['A0_T'], 'Gamma', r['A0_Gamma'], 'R_own', r['A0_R_own'],
          'R_Dg', r['A0_R_Dgreedy'], '| tau3 A0 T', r['tau3_A0_T'], 'R_tailco', r['tau3_A0_R_tailco_Dgreedy'])
sys.exit(1 if bad else 0)
