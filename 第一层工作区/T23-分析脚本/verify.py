# Independent recomputation of T23 stage 1-2 headline numbers: csv + math only.
# Usage: python3 verify.py [<round1-compare-dir>]  (default: 第一层实验结果/round1-compare-20261106 in the repo)
import csv, sys, math, collections
from pathlib import Path
B = (sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parents[2] / '第一层实验结果' / 'round1-compare-20261106')).rstrip('/') + '/'
R = list(csv.DictReader(open(B + 'results.csv', encoding='utf-8')))
CAT = {'cora': 'GNN', 'ogbn-arxiv': 'GNN', 'wiki-RfA': 'net', 'dawson5': 'FEM', 'olafu': 'FEM', 'pattern1': 'long', 'human_gene1': 'long'}
CANDS = ['C9-Gorder', 'C9-S', 'C10-BP', 'C2-LSH', 'C3-W1', 'C3-W4', 'C4-U', 'C4-T', 'C7-I', 'C1-J', 'C1-H', 'C5', 'C5-U', 'C8-METIS']
own = [x for x in R if x['source'] == 'own' and x['seed'] == '0' and x['W'] == '16']
# D-guard on partitioned rows (tail-co + tail) and post-E
def guard(rows):
    d = collections.defaultdict(dict)
    for x in rows:
        d[(x['matrix'], x['diag'], x['member'], x['tau'], x['placement'])][x['d_rule']] = float(x['sumR'])
    pairs = [v for v in d.values() if 'own' in v and 'D-greedy' in v]
    return sum(v['own'] < v['D-greedy'] for v in pairs), len(pairs)
print('guard main (own chosen, n):', guard([x for x in own if x['tau'] != 'none']))
print('guard post-E (own chosen, n):', guard([x for x in R if x['source'] == 'post-E']))
# RQ4 effectiveness at main setting (tail-co, D-greedy rows; T independent of D rule)
pts = collections.defaultdict(list)
for x in own:
    if x['tau'] != 'none' and x['placement'] == 'tail-co' and x['d_rule'] == 'D-greedy':
        pts[(CAT[x['matrix']], x['diag'], x['member'])].append(float(x['T_ratio_B0']))
eff = collections.defaultdict(list)
for (c, d, m), v in pts.items():
    g = math.exp(sum(map(math.log, v)) / len(v))
    if m in CANDS and g <= 0.95 and max(v) <= 1.05: eff[(c, d)].append(m)
for k in sorted(eff): print('effective', k, len(eff[k]), sorted(eff[k]) if k[0] in ('FEM',) else '')
# overall Pareto (geo over all first-batch points, total order_sec)
sec = collections.defaultdict(float); seen = set()
for x in own:
    if (x['matrix'], x['member']) not in seen:
        seen.add((x['matrix'], x['member'])); sec[x['member']] += float(x['order_sec'] or 0)
for d in ('A0', 'A1'):
    geo = {}
    for m in CANDS:
        v = [t for (c, dd, mm), vv in pts.items() if dd == d and mm == m for t in vv]
        geo[m] = math.exp(sum(map(math.log, v)) / len(v))
    front = [m for m in CANDS if not any(geo[o] <= geo[m] and sec[o] <= sec[m] and (geo[o] < geo[m] or sec[o] < sec[m]) for o in CANDS)]
    print('pareto', d, sorted(front))
