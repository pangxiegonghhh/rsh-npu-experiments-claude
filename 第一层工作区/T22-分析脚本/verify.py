# Independent recomputation of T22 headline counts: csv module only (no pandas / scipy).
# Usage: python3 verify.py [<rq3-validate-dir>]   (default: 第一层实验结果/rq3-validate-20261106 in the repo)
import csv, sys, collections
from pathlib import Path
B = (sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parents[2] / '第一层实验结果' / 'rq3-validate-20261106')).rstrip('/') + '/'
rows = lambda f: list(csv.DictReader(open(B + f, encoding='utf-8')))
num = lambda s: None if s in ('', '—', None) else float(s)
F = [x for x in rows('four_numbers.csv') if x['W'] == '16']
R = [x for x in rows('results.csv') if x['W'] == '16']
K = rows('kendall.csv'); C = rows('cross_tau.csv')
SMOOTH = ['rsh-α0', 'rabbit-pilot', 'neutron-pilot', 'C9-Gorder', 'C9-S']
GNN = ('cora', 'ogbn-arxiv')
A = {}
for x in F:
    if x['diag'] == 'A0': A[(x['matrix'], x['member'])] = num(x['align_premium']) / num(x['T_full'])
def rank(v):
    o = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0] * len(v); i = 0
    while i < len(o):
        j = i
        while j + 1 < len(o) and v[o[j + 1]] == v[o[i]]: j += 1
        for t in range(i, j + 1): r[o[t]] = (i + j) / 2
        i = j + 1
    return r
def spearman(a, b):
    ra, rb = rank(a), rank(b); n = len(a); ma = sum(ra) / n; mb = sum(rb) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    va = sum((x - ma) ** 2 for x in ra) ** .5; vb = sum((y - mb) ** 2 for y in rb) ** .5
    return cov / (va * vb)
# H1
lo = [x for x in F if A[(x['matrix'], x['member'])] <= 0.02]
uk = [x for x in F if num(x['U_keep']) > num(x['U_inplace'])]
print('H1a lowA keep<inplace', sum(num(x['T_keep']) < num(x['T_inplace']) for x in lo), 'of', len(lo))
print('H1b Ukeep>Uinplace', len(uk), 'with A>=5%', sum(A[(x['matrix'], x['member'])] >= 0.05 for x in uk))
# H2
hi = [(m, v) for (m, v), a in A.items() if m in GNN and v in ('C10-BP', 'LS-full(C9-Gorder)', 'LS-full(rsh-α0)')]
lw = [(m, v) for (m, v), a in A.items() if m in GNN and v in ['B0'] + SMOOTH]
print('H2a hi', sum(A[k] >= 0.05 for k in hi), 'of', len(hi), ' lo', sum(A[k] <= 0.02 for k in lw), 'of', len(lw))
g = collections.defaultdict(list)
for x in F:
    if num(x['T_rerun']) is not None: g[(x['matrix'], x['tau'], x['diag'])].append(x)
print('H2b rho<=-0.5', sum(spearman([A[(x['matrix'], x['member'])] for x in s], [num(x['T_rerun']) / num(x['T_keep']) for x in s]) <= -0.5 for s in g.values()), 'of', len(g))
# H3
kk = [x for x in K if x['W'] == '16' and x['comparison'] == 'full_vs_keep' and x['matrix'] in GNN]
print('H3a kendall>=0.6', sum(float(x['kendall_tau_b']) >= 0.6 for x in kk), 'of', len(kk))
g = collections.defaultdict(list)
for x in F: g[(x['matrix'], x['diag'], x['tau'])].append(x)
ch = [k for k, s in g.items() if min(s, key=lambda x: num(x['T_full']))['member'] != min(s, key=lambda x: num(x['T_keep']))['member']]
print('H3b first changed on', sorted(set(k[0] for k in ch)))
# H4
sm = [x for x in F if x['member'] in SMOOTH]
bp = [x for x in F if x['member'] == 'C10-BP']
print('H4 smooth within 3%', sum(abs(num(x['T_rerun']) / num(x['T_keep']) - 1) <= 0.03 for x in sm), 'of', len(sm),
      ' BP<=-3%', sum(num(x['T_rerun']) / num(x['T_keep']) - 1 <= -0.03 for x in bp), 'of', len(bp))
# H5
P0 = ['B0'] + SMOOTH + ['C10-BP']
pl = collections.defaultdict(dict)
for x in R:
    if x['source'] in ('pls-0', 'pls-1') and x['member'] in P0:
        pl[(x['source'], x['matrix'], x['tau'], x['diag'])][(x['member'], x['start_source'])] = num(x['T'])
sp = [(max(v.values()) - min(v.values())) / min(v.values()) for k, v in pl.items() if k[0] == 'pls-0']
print('H5a spread<=10%', sum(s <= 0.10 for s in sp), 'of', len(sp))
tc = {}
for x in R:
    if x['placement'] == 'tail-co' and x['d_rule'] == 'D-greedy' and x['diag'] == 'A0' and x['source'] in ('pls-0', 'pls-1'):
        tc[(x['source'], x['matrix'], x['member'], x['tau'], x['start_source'])] = (num(x['meanR']), num(x['T']))
n = ok = 0
for k, (r0, t0) in tc.items():
    if k[0] != 'pls-0' or ('pls-1',) + k[1:] not in tc: continue
    r1, t1 = tc[('pls-1',) + k[1:]]; n += 1; d = 1 - r1 / r0
    ok += 0.05 <= d <= 0.15 and abs(t1 / t0 - 1) <= 0.03
print('H5b both parts', ok, 'of', n)
# H6
ct = [x for x in C if x['W'] == '16' and int(x['assumed_tau']) > int(x['actual_tau'])]
print('H6 T_sig>=T_keep', sum(num(x['T_sig_assumed']) >= num(x['T_keep_pi']) for x in ct), 'of', len(ct))
# H7
kp = {}
for x in R:
    if x['source'] == 'keep' and x['d_rule'] == 'D-greedy' and x['placement'] in ('tail', 'tail-co'):
        kp[(x['matrix'], x['diag'], x['member'], x['tau'], x['placement'])] = (num(x['meanR']), float(x['resid_frac']))
b40 = b60 = n40 = n60 = 0
for k, (rt, rf) in kp.items():
    if k[4] != 'tail': continue
    d = 1 - kp[k[:4] + ('tail-co',)][0] / rt
    if .30 <= rf < .50: n40 += 1; b40 += d >= .05
    if .50 <= rf < .70: n60 += 1; b60 += d >= .15
print('H7 band40 >=5%', b40, 'of', n40, ' band60 >=15%', b60, 'of', n60)
# H8
ip = {}; co = {}
for x in R:
    if x['source'] != 'keep': continue
    k = (x['matrix'], x['diag'], x['member'], x['tau'])
    if x['placement'] == 'inplace' and x['d_rule'] == 'own': ip[k] = x
    if x['placement'] == 'tail-co' and x['d_rule'] == 'D-greedy': co[k] = x
print('H8 runs>=3k', sum(num(x['write_runs_aic']) >= 3 * num(x['k_windows']) for x in ip.values()), 'of', len(ip),
      ' R_inplace>=R_co', sum(num(ip[k]['meanR']) >= num(co[k]['meanR']) for k in ip), 'of', len(ip))
# H9
rr = {(x['matrix'], x['tau'], x['diag']): num(x['T_rerun']) for x in F if x['member'] == 'neutron-pilot'}
h9 = [(k, v) for k, v in pl.items() if k[0] == 'pls-0' and k[1] in GNN]
print('H9 ratio<=0.9', sum(v[('neutron-pilot', 'keep')] <= 0.9 * rr[k[1:]] for k, v in h9), 'of', len(h9))
