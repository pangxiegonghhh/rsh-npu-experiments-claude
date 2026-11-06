"""Reproduce the Cora numbers in 第一层工作区/T17-空白一调研.md (§8 Tables A/B, §4.5).
Usage:
  python3 reproduce_cora.py            # Tables A and B + self-check (about 1-2 min)
  python3 reproduce_cora.py --ls       # also §4.5 member local search (about 20-30 min, pure Python)
Outputs go to ./out/ (orders.json, table_a.csv, table_b.csv, ls_*.csv). Do not write into the repo.
"""
import sys, os, json, csv, time
sys.dont_write_bytecode = True   # keep the repo clean
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rq2lib import load_cora, existing_perms, evaluate, dstage
from methods import rcm, slashburn, bp, gorder, MemberLS
from memberls_part import MemberLSPart

OUT = os.path.join(os.getcwd(), 'out'); os.makedirs(OUT, exist_ok=True)
n, adj = load_cora()
P = existing_perms()
orders = {'original': P['original'], 'rsh': P['rsh'], 'rabbit': P['rabbit'], 'neutron': P['neutron'],
          'rcm': rcm(adj), 'slashburn': slashburn(adj), 'bp': bp(adj),
          'gorder': gorder(adj), 'gorder-S': gorder(adj, use_sn=False)}
json.dump(orders, open(os.path.join(OUT, 'orders.json'), 'w'))

# Table A (full rows, W=16)
rowsA = []
for m, o in orders.items():
    e = evaluate(o, adj); d = evaluate(dstage(o, adj), adj); g = evaluate(dstage(o, adj, intra='greedy'), adj)
    assert d['sumU'] == e['sumU'] and d['sumG'] == e['sumG'], m   # D stage must not change membership
    rowsA.append(dict(member=m, U=round(e['U'], 2), T=e['T'], Gamma=round(e['G'], 2), R_own=round(e['R'], 2),
                      R_Dgreedy=round(g['R'], 2), R_Dexact=round(d['R'], 2), p50=d['p50'], p90=d['p90'], max=d['max']))
# Table B (partitioned, tail placement + D)
rowsB = []
for tau in (2, 3):
    for m, o in orders.items():
        ei = evaluate(o, adj, tau=tau, placement='inplace'); et = evaluate(o, adj, tau=tau, placement='tail')
        dt = evaluate(dstage(o, adj, tau=tau), adj, tau=tau, placement='tail')
        gt = evaluate(dstage(o, adj, tau=tau, intra='greedy'), adj, tau=tau, placement='tail')
        rowsB.append(dict(tau=tau, member=m, k=et['k'], U=round(et['U'], 2), T=et['T'], R_inplace=round(ei['R'], 2),
                          R_tail=round(et['R'], 2), Gamma_tail=round(et['G'], 2), R_tail_Dgreedy=round(gt['R'], 2),
                          R_tail_Dexact=round(dt['R'], 2)))
for name, rows in (('table_a.csv', rowsA), ('table_b.csv', rowsB)):
    with open(os.path.join(OUT, name), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

# Self-check against the numbers printed in the research doc (§8)
EXPECT_A = {'original': (56.37, 681, 43.26, 50.38, 43.83), 'rsh': (35.50, 455, 14.15, 17.22, 14.80),
            'rabbit': (45.16, 553, 19.79, 26.32, 20.67), 'neutron': (44.68, 554, 19.56, 26.46, 20.58),
            'rcm': (45.71, 562, 16.20, 22.23, 17.08), 'slashburn': (44.86, 558, 15.94, 24.76, 18.44),
            'bp': (36.08, 474, 14.91, 24.25, 15.28), 'gorder': (36.15, 463, 13.12, 17.11, 13.18),
            'gorder-S': (36.31, 460, 15.58, 19.50, 15.76)}
bad = []
for r in rowsA:
    got = (r['U'], r['T'], r['Gamma'], r['R_own'], r['R_Dexact'])
    exp = EXPECT_A[r['member']]
    if any(abs(a - b) > 0.011 for a, b in zip(got, exp)): bad.append((r['member'], got, exp))
print('Table A self-check:', 'OK' if not bad else bad)
for r in rowsA: print(r)
for r in rowsB: print(r)
if bad:
    sys.exit(1)   # non-zero exit on a failed self-check

if '--ls' in sys.argv:
    rows = []
    for start in ('rsh', 'gorder', 'rabbit'):
        for lam in (0.0, 0.5, 1.0, 2.0):
            ls = MemberLS(orders[start], adj); t = time.time(); o = ls.run(lam=lam, sweeps=10)
            e = evaluate(o, adj); d = evaluate(dstage(o, adj), adj)
            e3 = evaluate(dstage(o, adj, tau=3), adj, tau=3, placement='tail')
            rows.append(dict(mode='fullrow', start=start, lam=lam, U=round(e['U'], 2), T=e['T'], Gamma=round(e['G'], 2),
                             R_D=round(d['R'], 2), tau3_R_tail_D=round(e3['R'], 2), sec=round(time.time() - t)))
            print(rows[-1], flush=True)
    for start in ('gorder', 'rsh'):
        for tau in (3, 2):
            for lam in (0.0, 1.0, 2.0):
                ls = MemberLSPart(orders[start], adj, tau); t = time.time(); o = ls.run(lam=lam, sweeps=10)
                e = evaluate(o, adj, tau=tau, placement='tail')
                d = evaluate(dstage(o, adj, tau=tau), adj, tau=tau, placement='tail')
                rows.append(dict(mode='partition-aware', start=start, tau=tau, lam=lam, U=round(e['U'], 2), T=e['T'],
                                 Gamma=round(e['G'], 2), R_tail_D=round(d['R'], 2), sec=round(time.time() - t)))
                print(rows[-1], flush=True)
    with open(os.path.join(OUT, 'ls.json'), 'w') as f: json.dump(rows, f, indent=1)
