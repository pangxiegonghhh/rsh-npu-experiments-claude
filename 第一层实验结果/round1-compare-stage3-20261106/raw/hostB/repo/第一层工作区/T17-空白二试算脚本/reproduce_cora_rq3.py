"""Reproduce the Cora numbers in 第一层工作区/T17-空白二调研.md (§8 Tables 1-4; --pls Table 5; --lsfull Table 6).
Usage (run in an empty directory outside the repo; outputs go to ./out_rq3/):
  python3 reproduce_cora_rq3.py            # Tables 1-4 + self-check (about 10-20 s)
  python3 reproduce_cora_rq3.py --pls      # also Table 5: partition-aware P-LS from 8 starts (about 10-15 min, pure Python)
  python3 reproduce_cora_rq3.py --lsfull   # also Table 6: full-row member LS, alignment premium (about 3 min)
Exit code 1 if the self-check fails.
"""
import sys, os, json, csv, time
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rq3lib import (four_numbers, phase_T, resid_set, chunks, win_metrics, layout_D, resid_write_runs, place_inplace,
                    gorder_sub, bp_sub, induced, pilot_sub)
from rq2lib import load_cora, existing_perms
from methods import rcm, slashburn, bp, gorder, MemberLS
from memberls_part import MemberLSPart
from collections import defaultdict
import itertools

OUT = os.path.join(os.getcwd(), 'out_rq3'); os.makedirs(OUT, exist_ok=True)
W = 16
n, adj0 = load_cora(); _, adj1 = load_cora(selfloop=True)
P = existing_perms()
orders = {'original': P['original'], 'rsh': P['rsh'], 'rabbit': P['rabbit'], 'neutron': P['neutron'],
          'rcm': rcm(adj0), 'slashburn': slashburn(adj0), 'bp': bp(adj0),
          'gorder': gorder(adj0), 'gorder-S': gorder(adj0, use_sn=False)}
MS = list(orders)

def rerun(m, K):
    """T(pi'): rerun the same method on the kept rows. Input = A[K, :] (residual points stay as columns);
    RCM / SlashBurn need a square graph and use the induced subgraph A[K, K]. 'original' restricted to K is pi_K."""
    if m == 'original': return [v for v in orders['original'] if v in K]
    if m == 'gorder': return gorder_sub(adj0, K)
    if m == 'gorder-S': return gorder_sub(adj0, K, use_sn=False)
    if m == 'bp': return bp_sub(adj0, K)
    if m in ('rsh', 'rabbit', 'neutron'): return pilot_sub(adj0, K, m)
    Ks, sub = induced(adj0, K)
    o = rcm(sub) if m == 'rcm' else slashburn(sub)
    return [Ks[i] for i in o]

def snap_own(pi, wins, D):
    win_of = {v: gi for gi, w in enumerate(wins) for v in w}
    owner = defaultdict(list); last = wins[0][0]
    for v in pi:
        if v in D: owner[win_of[last]].append(v)
        else: last = v
    return [x for gi, w in enumerate(wins) for x in (w + owner[gi])]

def kendall(a, b):
    c = d = ta = tb = 0
    for i, j in itertools.combinations(range(len(a)), 2):
        x = (a[i] > a[j]) - (a[i] < a[j]); y = (b[i] > b[j]) - (b[i] < b[j])
        if x == 0 and y == 0: continue
        if x == 0: ta += 1; continue
        if y == 0: tb += 1; continue
        c += (x == y); d += (x != y)
    return (c - d) / ((c + d + ta) * (c + d + tb)) ** 0.5

T1, T2, reruns = [], [], {}
for tau in (2, 3):
    D = resid_set(adj0, tau)
    for m in MS:
        pi = orders[m]; K = [v for v in pi if v not in D]; Dpi = [v for v in pi if v in D]
        r = dict(tau=tau, member=m, resid_frac=round(len(D) / n, 4))
        for tag, adj in (('A0', adj0), ('A1', adj1)):
            f = four_numbers(pi, adj, D)
            for k_, v in f.items(): r[f'{tag}_{k_}'] = v
        ph = phase_T(pi, adj0); r['A0_T_full_phase'] = round(ph[0], 1); r['A0_U_full_phase'] = round(ph[1], 1)
        r['A0_align_premium'] = round(ph[0] - r['A0_T_full'], 1)
        pp = rerun(m, set(K)); assert sorted(pp) == sorted(K); reruns[f'{tau}|{m}'] = pp
        for tag, adj in (('A0', adj0), ('A1', adj1)):
            wm = win_metrics(chunks(pp, W), adj); r[f'{tag}_T_rerun'] = wm['T']; r[f'{tag}_U_rerun'] = wm['sumU']
        T1.append(r)
        # placements (A0): own order and D-greedy, on pi_K windows; and D-greedy on rerun windows
        wins = chunks(K, W)
        q = dict(tau=tau, member=m)
        for nm, sig in (('tail_own', K + Dpi), ('inplace_own', list(pi)), ('snap_own', snap_own(pi, wins, D))):
            e = win_metrics(wins, adj0, sig)
            q[f'R_{nm}'] = round(e['R'], 2); q[f'WRaic_{nm}'] = e['write_runs_aic']; q[f'WRres_{nm}'] = resid_write_runs(sig, D)
        for rule in ('tail', 'tail-co', 'gap', 'snap', 'inplace'):
            sig = layout_D(wins, adj0, n, Dpi, rule=rule, W=W, pi=list(pi)); assert sorted(sig) == list(range(n))
            e = win_metrics(wins, adj0, sig)
            q[f'R_{rule}_D'] = round(e['R'], 2); q[f'p90_{rule}_D'] = e['p90']
            q[f'WRaic_{rule}_D'] = e['write_runs_aic']; q[f'WRres_{rule}_D'] = resid_write_runs(sig, D)
        wr = chunks(pp, W)
        for rule in ('tail', 'tail-co', 'gap'):
            sig = layout_D(wr, adj0, n, Dpi, rule=rule, W=W)
            q[f'rerun_R_{rule}_D'] = round(win_metrics(wr, adj0, sig)['R'], 2)
        # A1 placements (D stage with A1 co)
        for rule in ('tail', 'tail-co'):
            sig = layout_D(wins, adj1, n, Dpi, rule=rule, W=W)
            q[f'A1_R_{rule}_D'] = round(win_metrics(wins, adj1, sig)['R'], 2)
        T2.append(q)
        print(r['tau'], m, 'T full/inplace/keep/rerun', r['A0_T_full'], r['A0_T_inplace'], r['A0_T_keep'], r['A0_T_rerun'],
              '| R tail/tail-co/gap +D', q['R_tail_D'], q['R_tail-co_D'], q['R_gap_D'], flush=True)

# Table 3: Kendall tau between rankings by T
T3 = []
for tag, adj in (('A0', adj0), ('A1', adj1)):
    full = [win_metrics(chunks(orders[m], W), adj)['T'] for m in MS]
    for tau in (2, 3):
        keep = [r[f'{tag}_T_keep'] for r in T1 if r['tau'] == tau]
        rr = [r[f'{tag}_T_rerun'] for r in T1 if r['tau'] == tau]
        T3.append(dict(diag=tag, tau=tau, full_vs_keep=round(kendall(full, keep), 3), keep_vs_rerun=round(kendall(keep, rr), 3),
                       full_vs_keep_no_original=round(kendall(full[1:], keep[1:]), 3)))
# Table 4: cross-tau mismatch (order regrouped for assumed tau_a, evaluated at actual tau_b)
T4 = []
for m in ('gorder', 'rsh', 'bp', 'slashburn'):
    pi = orders[m]
    for ta, tb in ((3, 2), (2, 3)):
        Da = resid_set(adj0, ta); Db = resid_set(adj0, tb)
        sig = reruns[f'{ta}|{m}'] + [v for v in pi if v in Da]
        T4.append(dict(member=m, assumed_tau=ta, actual_tau=tb,
                       T_keep_pi=win_metrics(chunks([v for v in pi if v not in Db], W), adj0)['T'],
                       T_sig_assumed=win_metrics(chunks([v for v in sig if v not in Db], W), adj0)['T'],
                       T_rerun_actual=win_metrics(chunks(reruns[f'{tb}|{m}'], W), adj0)['T']))

def dump(name, rows):
    with open(os.path.join(OUT, name), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
for name, rows in (('table1_four_numbers.csv', T1), ('table2_placement.csv', T2), ('table3_kendall.csv', T3), ('table4_cross_tau.csv', T4)):
    dump(name, rows)
json.dump(orders, open(os.path.join(OUT, 'orders.json'), 'w'))
json.dump(reruns, open(os.path.join(OUT, 'reruns.json'), 'w'))

# ---- self-check against the research doc (§8) ----
EXPECT_T1 = {  # (tau, member): (T_full, T_inplace, T_keep, T_rerun, U_inplace, U_keep)  A0
    (2, 'original'): (681, 588, 550, 550, 8189, 8076), (2, 'rsh'): (455, 419, 384, 377, 5556, 5373),
    (2, 'rabbit'): (553, 490, 463, 464, 6748, 6590), (2, 'neutron'): (554, 496, 456, 458, 6685, 6559),
    (2, 'rcm'): (562, 511, 471, 463, 6809, 6783), (2, 'slashburn'): (558, 503, 456, 453, 6829, 6641),
    (2, 'bp'): (474, 412, 402, 377, 5337, 5714), (2, 'gorder'): (463, 404, 376, 373, 5381, 5261),
    (2, 'gorder-S'): (460, 407, 377, 375, 5381, 5292),
    (3, 'original'): (681, 503, 446, 446, 6779, 6634), (3, 'rsh'): (455, 380, 317, 317, 4902, 4591),
    (3, 'rabbit'): (553, 434, 381, 379, 5777, 5573), (3, 'neutron'): (554, 437, 376, 376, 5717, 5511),
    (3, 'rcm'): (562, 437, 384, 386, 5823, 5668), (3, 'slashburn'): (558, 439, 395, 374, 5948, 5779),
    (3, 'bp'): (474, 362, 330, 312, 4628, 4720), (3, 'gorder'): (463, 359, 311, 307, 4686, 4480),
    (3, 'gorder-S'): (460, 358, 309, 310, 4687, 4479)}
EXPECT_T2 = {  # (tau, member): (R_tail_D, R_tail-co_D, R_gap_D)
    (2, 'original'): (59.81, 52.60, 52.06), (2, 'rsh'): (23.04, 20.14, 19.46), (2, 'rabbit'): (30.75, 27.01, 26.17),
    (2, 'neutron'): (30.93, 27.09, 26.32), (2, 'rcm'): (26.01, 24.52, 23.82), (2, 'slashburn'): (29.75, 26.96, 26.17),
    (2, 'bp'): (26.02, 21.15, 20.41), (2, 'gorder'): (20.17, 17.39, 16.65), (2, 'gorder-S'): (22.36, 18.83, 18.06),
    (3, 'original'): (73.22, 54.15, 53.19), (3, 'rsh'): (29.66, 23.03, 22.16), (3, 'rabbit'): (38.99, 29.18, 28.10),
    (3, 'neutron'): (38.49, 28.46, 27.44), (3, 'rcm'): (33.12, 27.01, 26.15), (3, 'slashburn'): (42.51, 32.54, 31.62),
    (3, 'bp'): (33.00, 21.49, 20.53), (3, 'gorder'): (25.46, 18.93, 17.65), (3, 'gorder-S'): (27.19, 20.29, 19.19)}
bad = []
for r in T1:
    got = (r['A0_T_full'], r['A0_T_inplace'], r['A0_T_keep'], r['A0_T_rerun'], r['A0_U_inplace'], r['A0_U_keep'])
    if got != EXPECT_T1[(r['tau'], r['member'])]: bad.append(('T1', r['tau'], r['member'], got))
for q in T2:
    got = (q['R_tail_D'], q['R_tail-co_D'], q['R_gap_D'])
    if any(abs(a - b) > 0.011 for a, b in zip(got, EXPECT_T2[(q['tau'], q['member'])])): bad.append(('T2', q['tau'], q['member'], got))
    for rule in ('tail', 'tail-co', 'gap', 'snap'):   # these rules keep every AIC window contiguous in sigma
        if q[f'WRaic_{rule}_D'] != (103 if q['tau'] == 2 else 68): bad.append(('WR', q['tau'], q['member'], rule))
print('RQ3 Table 1/2 self-check:', 'OK' if not bad else bad)
for r in T3: print(r)
for r in T4: print(r)
if bad: sys.exit(1)

if '--pls' in sys.argv:
    T5 = []
    plan = [('gorder', 'keep', (0.0, 1.0)), ('rsh', 'keep', (0.0, 1.0)), ('bp', 'keep', (0.0, 1.0)), ('bp', 'rerun', (0.0, 1.0)),
            ('original', 'keep', (0.0,)), ('rabbit', 'keep', (0.0,)), ('neutron', 'keep', (0.0,)), ('rcm', 'keep', (0.0,))]
    for start, src, lams in plan:
        for tau in (3, 2):
            D = resid_set(adj0, tau); pi = orders[start]; Dpi = [v for v in pi if v in D]
            base = pi if src == 'keep' else reruns[f'{tau}|{start}'] + Dpi
            for lam in lams:
                t = time.time(); ls = MemberLSPart(base, adj0, tau); o = ls.run(lam=lam, sweeps=10)
                wins = chunks([v for v in o if v not in D], W); e = win_metrics(wins, adj0)
                r = dict(start=start, src=src, tau=tau, lam=lam, T=e['T'], U=round(e['U'], 2), T_A1=win_metrics(wins, adj1)['T'])
                for rule in ('tail', 'tail-co', 'gap'):
                    r[f'R_{rule}_D'] = round(win_metrics(wins, adj0, layout_D(wins, adj0, n, Dpi, rule=rule, W=W))['R'], 2)
                r['sec'] = round(time.time() - t); T5.append(r); print(r, flush=True)
    dump('table5_pls.csv', T5)

if '--lsfull' in sys.argv:
    T6 = []
    for start in ('gorder', 'rsh'):
        o = MemberLS(orders[start], adj0).run(lam=0.0, sweeps=10)
        ph = phase_T(o, adj0); r = dict(start=start, T_full=win_metrics(chunks(o, W), adj0)['T'], T_full_phase=round(ph[0], 1))
        for tau in (2, 3):
            f = four_numbers(o, adj0, resid_set(adj0, tau))
            r.update({f'tau{tau}_{k}': f[k] for k in ('T_inplace', 'T_keep', 'U_inplace', 'U_keep')})
        T6.append(r); print(r, flush=True)
    dump('table6_lsfull.csv', T6)
