#!/usr/bin/env python3
"""T23 stage 1-2 analysis (first-round candidate comparison).
Usage: python3 analyze.py <round1-compare-dir> [<stage3-snapshot-dir>]  -> prints JSON.
Main setting: W=16, symmetric, partitioned (both taus), tail-co, D-guard (min sumR of own / D-greedy), A0 and A1 side by side.
RQ4 thresholds (fixed 2026-11-06): effective = category geo-mean T/T(B0) <= 0.95 and worst <= 1.05.
Unit of the RQ4 distribution = one (matrix, tau) point; worst is taken over all points of the category."""
import sys, json, math
import numpy as np
import pandas as pd
from scipy.stats import kendalltau

D = sys.argv[1].rstrip('/') + '/'
S3 = sys.argv[2].rstrip('/') + '/' if len(sys.argv) > 2 else None
r = pd.read_csv(D + 'results.csv')
dg = pd.read_csv(D + 'diag.csv')
r['tau_s'] = r.tau.astype(str)
CAT = {'cora': 'GNN', 'ogbn-arxiv': 'GNN', 'wiki-RfA': 'net', 'dawson5': 'FEM', 'olafu': 'FEM', 'pattern1': 'long', 'human_gene1': 'long'}
CANDS = ['C9-Gorder', 'C9-S', 'C10-BP', 'C2-LSH', 'C3-W1', 'C3-W4', 'C4-U', 'C4-T', 'C7-I', 'C1-J', 'C1-H', 'C5', 'C5-U', 'C8-METIS']
BASE = ['B0', 'B1']
REFS = ['B-RCM-ref', 'rabbit-pilot', 'neutron-pilot']
OUT = {}
own = r[(r.source == 'own') & (r.seed == 0) & (r.W == 16)]
part = own[own.tau_s != 'none'].copy()
part['tl'] = part.groupby('matrix').tau.transform(lambda s: s.astype(int).rank(method='dense').astype(int))

# ---- D-stage guard on tail-co (main) and tail (reference), plus post-E
def guard(df, label):
    key = ['matrix', 'diag', 'member', 'tau_s', 'placement']
    a = df[df.d_rule == 'own'][key + ['sumR', 'meanR']]
    b = df[df.d_rule == 'D-greedy'][key + ['sumR', 'meanR']]
    j = a.merge(b, on=key, suffixes=('_own', '_D'))
    j['own_wins'] = j.sumR_own < j.sumR_D
    j['gain'] = 1 - j.sumR_own / j.sumR_D
    w = j[j.own_wins]
    return j, dict(n=len(j), own_chosen=int(j.own_wins.sum()), share=float(j.own_wins.mean()),
                   max_gain=float(w.gain.max()) if len(w) else 0.0,
                   by_member=w.groupby('member').size().to_dict(), by_matrix=w.groupby('matrix').size().to_dict(),
                   by_placement=w.groupby('placement').size().to_dict())
gj, OUT['guard_main'] = guard(part[part.placement.isin(['tail-co', 'tail'])], 'main')
post = r[(r.source == 'post-E') & (r.W == 16)].copy()
_, OUT['guard_postE'] = guard(post, 'post')
fullrow = own[own.tau_s == 'none']
_, OUT['guard_fullrow'] = guard(fullrow.assign(placement='none'), 'full')

# ---- RQ4: effectiveness per category (T only; T independent of placement / D rule)
mainT = part[(part.placement == 'tail-co') & (part.d_rule == 'D-greedy')][['matrix', 'diag', 'member', 'tau_s', 'tl', 'T', 'T_ratio_B0']]
def eff_table(T):
    rows = []
    for (cat, d), s in T.groupby([T.matrix.map(CAT), 'diag']):
        for m, x in s.groupby('member'):
            v = x.T_ratio_B0.values
            rows.append(dict(category=cat, diag=d, member=m, n=len(v), geo=float(np.exp(np.log(v).mean())), worst=float(v.max()),
                             median=float(np.median(v)), improved=int((v < 0.99).sum()), flat=int((abs(v - 1) <= 0.01).sum()), worse=int((v > 1.01).sum())))
    e = pd.DataFrame(rows)
    e['effective'] = (e.geo <= 0.95) & (e.worst <= 1.05)
    return e
E = eff_table(mainT)
OUT['effective_main'] = E.round(4).to_dict('records')
fullT = fullrow[fullrow.d_rule == 'own'][['matrix', 'diag', 'member', 'T', 'T_ratio_B0']]
OUT['effective_fullrow'] = eff_table(fullT).round(4).to_dict('records')
# per category ranking by geo (candidates + B1), and between-category Kendall of those ranks
rk = {}
for (cat, d), s in E[E.member.isin(CANDS + ['B1'])].groupby(['category', 'diag']):
    rk[(cat, d)] = s.set_index('member').geo
cats = ['GNN', 'net', 'FEM', 'long']
kc = []
for d in ('A0', 'A1'):
    for a, b in [(a, b) for i, a in enumerate(cats) for b in cats[i + 1:]]:
        x, y = rk[(a, d)], rk[(b, d)]
        idx = x.index.intersection(y.index)
        kc.append(dict(diag=d, a=a, b=b, kendall=float(kendalltau(x[idx], y[idx]).statistic)))
OUT['category_kendall'] = kc

# ---- Pareto on (overall geo-mean T/T(B0) over all first-batch points, total order_sec)
osec = own.drop_duplicates(['matrix', 'member']).groupby('member').order_sec.sum()
par = []
for d in ('A0', 'A1'):
    s = mainT[(mainT.diag == d) & mainT.member.isin(CANDS + ['B1'])]
    g = s.groupby('member').T_ratio_B0.apply(lambda v: float(np.exp(np.log(v).mean())))
    t = pd.DataFrame({'geo': g, 'sec': osec.reindex(g.index)})
    t['pareto'] = [not any((t.geo <= t.geo[i]) & (t.sec <= t.sec[i]) & ((t.geo < t.geo[i]) | (t.sec < t.sec[i]))) for i in t.index]
    t['diag'] = d
    par.append(t.reset_index())
P = pd.concat(par)
OUT['pareto'] = P.round(4).to_dict('records')
# Pareto without B1 (baseline) - candidates only
par2 = []
for d in ('A0', 'A1'):
    t = P[(P.diag == d) & (P.member != 'B1')].set_index('member')
    t['pareto'] = [not any((t.geo <= t.geo[i]) & (t.sec <= t.sec[i]) & ((t.geo < t.geo[i]) | (t.sec < t.sec[i]))) for i in t.index]
    par2.append(t.reset_index())
OUT['pareto_candidates_only'] = pd.concat(par2).round(4).to_dict('records')
# per-category best (geo) among candidates
best = []
for (cat, d), s in E[E.member.isin(CANDS)].groupby(['category', 'diag']):
    s = s.sort_values('geo')
    best.append(dict(category=cat, diag=d, top3=s.member.head(3).tolist(), geo=s.geo.head(3).round(3).tolist(), B1_geo=float(E[(E.category == cat) & (E.diag == d) & (E.member == 'B1')].geo.iloc[0])))
OUT['category_top3'] = best

# ---- R at main setting (D-guard) relative to B0, per category
gj['R_guard'] = np.minimum(gj.sumR_own, gj.sumR_D)
gm = gj[gj.placement == 'tail-co']
b0 = gm[gm.member == 'B0'][['matrix', 'diag', 'tau_s', 'R_guard']].rename(columns={'R_guard': 'R_B0'})
gm = gm.merge(b0, on=['matrix', 'diag', 'tau_s'])
gm['R_ratio'] = gm.R_guard / gm.R_B0
Rt = gm.groupby([gm.matrix.map(CAT).rename('category'), 'diag', 'member']).R_ratio.apply(lambda v: float(np.exp(np.log(v).mean()))).reset_index()
OUT['R_ratio_geo'] = Rt.round(4).to_dict('records')

# ---- A11 / R1-H4: full-row vs partitioned ranking; alignment premium
ranked = CANDS + ['B1']
k11 = []
for (m, d), s in own[(own.d_rule == 'own') & own.member.isin(ranked)].groupby(['matrix', 'diag']):
    f = s[s.tau_s == 'none'].set_index('member')['T']
    for t in sorted(s[s.tau_s != 'none'].tau_s.unique(), key=int):
        p = s[(s.tau_s == t) & (s.placement == 'tail-co')].set_index('member')['T']
        idx = f.index.intersection(p.index)
        k11.append(dict(matrix=m, diag=d, tau=t, kendall=float(kendalltau(f[idx], p[idx]).statistic),
                        first_full=f[idx].idxmin(), first_part=p[idx].idxmin()))
OUT['A11'] = k11
a = dg[(dg.W == 16) & (dg.diag == 'A0')].drop_duplicates(['matrix', 'member'])[['matrix', 'member', 'T_full', 'align_premium']]
a['A_rel'] = a.align_premium / a.T_full
OUT['A_rel'] = a.pivot(index='member', columns='matrix', values='A_rel').round(4).to_dict()
# rank change full -> partitioned (A0), by A_rel group
ch = []
for (m, d), s in own[(own.d_rule == 'own') & own.member.isin(ranked) & (own.diag == 'A0')].groupby(['matrix', 'diag']):
    f = s[s.tau_s == 'none'].set_index('member')['T'].rank()
    for t in sorted(s[s.tau_s != 'none'].tau_s.unique(), key=int):
        p = s[(s.tau_s == t) & (s.placement == 'tail-co')].set_index('member')['T'].rank()
        for mem in f.index.intersection(p.index):
            ar = a[(a.matrix == m) & (a.member == mem)].A_rel
            ch.append(dict(matrix=m, tau=t, member=mem, A_rel=float(ar.iloc[0]) if len(ar) else None, drop=float(p[mem] - f[mem])))
ch = pd.DataFrame(ch)
hiA = ch[ch.A_rel >= 0.05]; loA = ch[ch.A_rel <= 0.02]
OUT['R1H4'] = dict(hiA_n=len(hiA), hiA_rank_worse=int((hiA['drop'] > 0).sum()), hiA_mean_drop=float(hiA['drop'].mean()),
                   loA_n=len(loA), loA_abs_change_le1=int((loA['drop'].abs() <= 1).sum()), loA_mean_abs=float(loA['drop'].abs().mean()),
                   hiA_list=hiA.round(3).to_dict('records'))

# ---- A12 / R1-H5: post-E spread on GNN graphs; before vs after
pe = post[(post.placement == 'tail-co') & (post.d_rule == 'D-greedy')][['matrix', 'diag', 'member', 'tau_s', 'T', 'meanR']]
pre = mainT[['matrix', 'diag', 'member', 'tau_s', 'T']]
h5 = []
P0 = CANDS + BASE
for (m, d, t), s in pe[pe.member.isin(P0)].groupby(['matrix', 'diag', 'tau_s']):
    b = pre[(pre.matrix == m) & (pre.diag == d) & (pre.tau_s == t) & pre.member.isin(s.member)]
    h5.append(dict(matrix=m, diag=d, tau=t, n=len(s), spread_after=float((s['T'].max() - s['T'].min()) / s['T'].min()),
                   spread_before=float((b['T'].max() - b['T'].min()) / b['T'].min()),
                   kendall_before_after=float(kendalltau(b.set_index('member')['T'][s.member], s.set_index('member')['T']).statistic),
                   best_after=s.loc[s['T'].idxmin(), 'member'], best_before=b.loc[b['T'].idxmin(), 'member']))
OUT['R1H5_A12'] = h5
pst = pd.read_csv(D + 'post-E.csv')
OUT['postE_sweeps'] = pst.groupby('matrix').sweeps_done.agg(['min', 'median', 'max']).to_dict('index')
OUT['postE_seconds_total'] = float(pst.post_seconds.sum())

# ---- attribution A1, A2, A3, A6, A9 (T geo ratio, main setting, per category)
def pair(a_, b_):
    x = mainT[mainT.member == a_].set_index(['matrix', 'diag', 'tau_s'])['T']
    y = mainT[mainT.member == b_].set_index(['matrix', 'diag', 'tau_s'])['T']
    q = (y / x).dropna()
    by = q.groupby(q.index.get_level_values(0).map(CAT)).apply(lambda v: float(np.exp(np.log(v).mean())))
    return dict(pair=f'{b_}/{a_}', geo_by_cat=by.round(4).to_dict(), n_b_better=int((q < 1).sum()), n=len(q))
OUT['attrib'] = [pair('C1-J', 'C1-H'), pair('C3-W1', 'C3-W4'), pair('C4-U', 'C4-T'), pair('C4-U', 'C7-I'),
                 pair('C5', 'C5-U'), pair('C9-Gorder', 'C9-S')]
# time per member and matrix
OUT['order_sec'] = own.drop_duplicates(['matrix', 'member']).pivot(index='member', columns='matrix', values='order_sec').round(2).to_dict()
# seed spread (cora, ogbn-arxiv)
sd = r[(r.source == 'own') & (r.W == 16) & (r.placement == 'tail-co') & (r.d_rule == 'D-greedy') & r.matrix.isin(['cora', 'ogbn-arxiv'])]
sp = sd.groupby(['matrix', 'diag', 'member', 'tau_s'])['T'].agg(lambda v: (v.max() - v.min()) / v.min() if len(v) > 1 else np.nan).dropna()
OUT['seed_spread_max_by_member'] = sp.groupby('member').max().round(4).to_dict()

# ---- stage-3 snapshot (W sensitivity, R1-H7) - provisional
if S3:
    s3 = pd.read_csv(S3 + 'results.csv')
    s3 = s3[(s3.status == 'OK') & (s3.source == 'own') & (s3.seed == 0)]
    s3['tau_s'] = s3.tau.astype(str)
    allr = pd.concat([own[own.status == 'OK'], s3[s3.W != 16]], ignore_index=True)
    ws = []
    ORDER_ONLY = ['C1-J', 'C1-H', 'C9-Gorder', 'C9-S']
    for m in ['cora', 'ogbn-arxiv', 'wiki-RfA', 'dawson5']:
        for d in ('A0', 'A1'):
            for view in ('none', 'main'):
                def T_at(W):
                    x = allr[(allr.matrix == m) & (allr.diag == d) & (allr.W == W) & (allr.d_rule == 'own')]
                    if view == 'none':
                        x = x[x.tau_s == 'none']
                    else:
                        tmax = str(max(int(t) for t in x.tau_s.unique() if t != 'none'))
                        x = x[(x.tau_s == tmax) & (x.placement == 'tail-co')]
                    return x[x.member.isin(CANDS + ['B1'])].drop_duplicates('member').set_index('member')['T']
                t16 = T_at(16)
                for W in (32, 64, 128):
                    tw = T_at(W)
                    idx = t16.index.intersection(tw.index)
                    if len(idx) >= 4:
                        ws.append(dict(matrix=m, diag=d, view=view, W=W, n=len(idx), kendall=float(kendalltau(t16[idx], tw[idx]).statistic), members=sorted(idx)))
    ws = pd.DataFrame(ws)
    OUT['W_stability'] = ws.drop(columns=['members']).round(4).to_dict('records')
    OUT['W_stability_members'] = sorted(set(sum(ws.members.tolist(), [])))
    stab = []
    for (d, view, W), s in ws.groupby(['diag', 'view', 'W']):
        stab.append(dict(diag=d, view=view, W=W, pass_=int((s.kendall >= 0.6).sum()), n=len(s), stable=bool((s.kendall >= 0.6).mean() >= 0.75)))
    OUT['W_stable'] = stab

def conv(o):
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (np.floating,)): return None if np.isnan(o) else float(o)
    if isinstance(o, (np.bool_,)): return bool(o)
    if isinstance(o, tuple): return list(o)
    return str(o)
print(json.dumps(OUT, ensure_ascii=False, indent=1, default=conv))
