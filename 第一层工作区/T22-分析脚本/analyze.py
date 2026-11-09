#!/usr/bin/env python3
"""T22 (RQ3 validation) analysis: R3-H1..H9 against the pre-registered criteria
(第一层工作区/RQ3验证实验方案.md §7). Criteria are applied as written; where the text
needs an operational reading, the reading is stated in OPERATIONALISATION below and in
the analysis note. Usage: python3 analyze.py <rq3-validate-dir>  (prints tables + JSON)."""
import sys, json, itertools
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

D = sys.argv[1].rstrip('/') + '/'
r = pd.read_csv(D + 'results.csv')
f = pd.read_csv(D + 'four_numbers.csv')
k = pd.read_csv(D + 'kendall.csv')
c = pd.read_csv(D + 'cross_tau.csv')
for col in ('T_rerun', 'U_rerun'):
    f[col] = pd.to_numeric(f[col].replace('—', np.nan))
f['A_rel'] = f.align_premium / f.T_full

GNN = ['cora', 'ogbn-arxiv']
SMOOTH = ['rsh-α0', 'rabbit-pilot', 'neutron-pilot', 'C9-Gorder', 'C9-S']
P0 = ['B0'] + SMOOTH + ['C10-BP']
OUT = {}

OPERATIONALISATION = {
    'scope': 'W=16 unless stated; A/T_full is computed on A0 (M2 is A0 only) and attached to both A0 and A1 rows of the same order',
    'H1': 'every (matrix, tau) has resid_frac >= 20%, so all rows are in scope',
    'H2b': 'Spearman over members with a rerun (LS-full excluded), per matrix x tau x diag',
    'H5': 'starts = P0 keep orders + C10-BP rerun; spread=(max-min)/min of T; before = T_keep of the same starts; R from A0 tail-co + D-greedy',
    'H7': 'drop = 1 - R(tail-co,D)/R(tail,D) on keep windows; band ~40% = resid_frac in [0.30,0.50), ~60% = [0.50,0.70); monotone = drop(high tau) >= drop(low tau) per matrix x member x diag',
    'H8': 'R(inplace, own) vs R(tail-co, D-greedy), keep windows, all members',
}

A0f = f[(f.diag == 'A0')][['matrix', 'member', 'W', 'tau', 'A_rel']]
ff = f.drop(columns=['A_rel']).merge(A0f, on=['matrix', 'member', 'W', 'tau'], how='left')
f16 = ff[ff.W == 16].copy()

# ---- H1
f16['dKI'] = f16.T_keep - f16.T_inplace
low = f16[f16.A_rel <= 0.02]
h1a_fail = low[low.dKI >= 0]
uk = f16[f16.U_keep > f16.U_inplace]
h1b_fail = uk[uk.A_rel < 0.05]
OUT['H1'] = dict(n_lowA=len(low), lowA_keep_lt_inplace=int((low.dKI < 0).sum()),
                 n_Ukeep_gt_Uinplace=len(uk), of_which_A_ge_5pct=int((uk.A_rel >= 0.05).sum()),
                 fails_a=h1a_fail[['matrix', 'diag', 'member', 'tau', 'T_inplace', 'T_keep', 'A_rel']].to_dict('records'),
                 fails_b=h1b_fail[['matrix', 'diag', 'member', 'tau', 'U_inplace', 'U_keep', 'A_rel']].to_dict('records'))

# ---- H2
a0 = f16[(f16.diag == 'A0')].drop_duplicates(['matrix', 'member'])
piv = a0.pivot(index='member', columns='matrix', values='A_rel')
OUT['H2_A_rel_table'] = piv.round(4).to_dict()
g = a0[a0.matrix.isin(GNN)]
need_hi = g[g.member.isin(['C10-BP', 'LS-full(C9-Gorder)', 'LS-full(rsh-α0)'])]
need_lo = g[g.member.isin([m for m in P0 if m != 'C10-BP'])]
OUT['H2a'] = dict(hi_pass=int((need_hi.A_rel >= 0.05).sum()), hi_n=len(need_hi),
                  lo_pass=int((need_lo.A_rel <= 0.02).sum()), lo_n=len(need_lo),
                  hi_fail=need_hi[need_hi.A_rel < 0.05][['matrix', 'member', 'A_rel']].to_dict('records'),
                  lo_fail=need_lo[need_lo.A_rel > 0.02][['matrix', 'member', 'A_rel']].to_dict('records'))
rows = []
for (m, t, dg), s in f16[f16.T_rerun.notna()].groupby(['matrix', 'tau', 'diag']):
    rho = spearmanr(s.A_rel, s.T_rerun / s.T_keep).correlation
    rows.append(dict(matrix=m, tau=t, diag=dg, n=len(s), rho=rho))
h2b = pd.DataFrame(rows)
OUT['H2b'] = dict(pass_=int((h2b.rho <= -0.5).sum()), n=len(h2b), table=h2b.round(3).to_dict('records'))

# ---- H3
kk = k[(k.W == 16) & (k.comparison == 'full_vs_keep') & (k.matrix.isin(GNN))]
OUT['H3a'] = dict(pass_=int((kk.kendall_tau_b >= 0.6).sum()), n=len(kk),
                  table=kk[['matrix', 'diag', 'tau', 'exclude_B0', 'kendall_tau_b']].round(3).to_dict('records'))
firsts = []
for (m, dg, t), s in f16.groupby(['matrix', 'diag', 'tau']):
    a = s.loc[s.T_full.idxmin(), 'member']; b = s.loc[s.T_keep.idxmin(), 'member']
    firsts.append(dict(matrix=m, diag=dg, tau=t, first_full=a, first_keep=b, changed=a != b))
firsts = pd.DataFrame(firsts)
OUT['H3b'] = firsts.to_dict('records')

# ---- H4
f16['rr'] = f16.T_rerun / f16.T_keep - 1
sm = f16[f16.member.isin(SMOOTH)]
bp = f16[f16.member == 'C10-BP']
OUT['H4'] = dict(smooth_in_band=int((sm.rr.abs() <= 0.03).sum()), smooth_n=len(sm),
                 smooth_out=sm[sm.rr.abs() > 0.03][['matrix', 'diag', 'member', 'tau', 'T_keep', 'T_rerun', 'rr']].round(4).to_dict('records'),
                 bp_pass=int((bp.rr <= -0.03).sum()), bp_n=len(bp),
                 bp_table=bp[['matrix', 'diag', 'tau', 'T_keep', 'T_rerun', 'rr']].round(4).to_dict('records'),
                 other=f16[~f16.member.isin(SMOOTH + ['C10-BP']) & f16.rr.notna()][['matrix', 'diag', 'member', 'tau', 'rr']].round(4).to_dict('records'))

# ---- H5
r16 = r[r.W == 16]
pls_any = r16[r16.source.isin(['pls-0', 'pls-1'])]
def pls_T(src, dg):
    s = pls_any[(pls_any.source == src) & (pls_any.diag == dg)]
    return s.drop_duplicates(['matrix', 'member', 'tau', 'start_source'])[['matrix', 'member', 'tau', 'start_source', 'T', 'sumU']]
rows = []
for dg in ('A0', 'A1'):
    p0 = pls_T('pls-0', dg)
    p0 = p0[p0.member.isin(P0)]
    for (m, t), s in p0.groupby(['matrix', 'tau']):
        before = f16[(f16.matrix == m) & (f16.tau == t) & (f16.diag == dg)]
        bvals = []
        for _, x in s.iterrows():
            b = before[before.member == x.member]
            bvals.append(float(b.T_rerun.iloc[0] if x.start_source == 'rerun' else b.T_keep.iloc[0]))
        rows.append(dict(matrix=m, tau=t, diag=dg, n_starts=len(s), spread_after=(s['T'].max() - s['T'].min()) / s['T'].min(),
                         spread_before=(max(bvals) - min(bvals)) / min(bvals)))
h5a = pd.DataFrame(rows)
OUT['H5a'] = dict(pass_=int((h5a.spread_after <= 0.10).sum()), n=len(h5a), before_gt20=int((h5a.spread_before > 0.20).sum()),
                  table=h5a.round(4).to_dict('records'))
tc = r16[(r16.placement == 'tail-co') & (r16.d_rule == 'D-greedy') & (r16.diag == 'A0')]
key = ['matrix', 'member', 'tau', 'start_source']
l0 = tc[tc.source == 'pls-0'][key + ['meanR', 'T']]
l1 = tc[tc.source == 'pls-1'][key + ['meanR', 'T']]
j = l0.merge(l1, on=key, suffixes=('_0', '_1'))
j['Rdrop'] = 1 - j.meanR_1 / j.meanR_0
j['Tchg'] = j.T_1 / j.T_0 - 1
T1 = pls_T('pls-1', 'A1').merge(pls_T('pls-0', 'A1'), on=key, suffixes=('_1', '_0'))
T1['Tchg'] = T1.T_1 / T1.T_0 - 1
OUT['H5b'] = dict(n=len(j), R_drop_5_15=int(((j.Rdrop >= 0.05) & (j.Rdrop <= 0.15)).sum()), R_drop_ge5=int((j.Rdrop >= 0.05).sum()),
                  T_within3=int((j.Tchg.abs() <= 0.03).sum()), both=int(((j.Rdrop >= 0.05) & (j.Rdrop <= 0.15) & (j.Tchg.abs() <= 0.03)).sum()),
                  A1_T_within3=int((T1.Tchg.abs() <= 0.03).sum()), A1_n=len(T1),
                  by_matrix=j.groupby('matrix').agg(Rdrop_med=('Rdrop', 'median'), Rdrop_min=('Rdrop', 'min'), Rdrop_max=('Rdrop', 'max'),
                                                    Tchg_med=('Tchg', 'median'), Tchg_max=('Tchg', 'max')).round(4).to_dict('index'))

# ---- H6
ct = c[(c.W == 16) & (c.assumed_tau > c.actual_tau)].copy()
ct['holds'] = ct.T_sig_assumed >= ct.T_keep_pi
ct['rel'] = ct.T_sig_assumed / ct.T_keep_pi - 1
OUT['H6'] = dict(n=len(ct), holds=int(ct.holds.sum()),
                 by_matrix=ct.groupby('matrix').holds.agg(['sum', 'count']).to_dict('index'),
                 rel_median=float(ct.rel.median()), table=ct[['matrix', 'diag', 'member', 'assumed_tau', 'actual_tau', 'T_keep_pi', 'T_sig_assumed', 'rel']].round(4).to_dict('records'))
ct2 = c[(c.W == 16) & (c.assumed_tau < c.actual_tau)].copy()
ct2['rel'] = ct2.T_sig_assumed / ct2.T_keep_pi - 1
OUT['H6_reverse_direction'] = dict(n=len(ct2), le=int((ct2.T_sig_assumed <= ct2.T_keep_pi).sum()), rel_median=float(ct2.rel.median()))

# ---- H7
kp = r16[(r16.source == 'keep') & (r16.d_rule == 'D-greedy')]
key7 = ['matrix', 'diag', 'member', 'tau']
t_ = kp[kp.placement == 'tail'][key7 + ['meanR', 'resid_frac']]
tco = kp[kp.placement == 'tail-co'][key7 + ['meanR']]
h7 = t_.merge(tco, on=key7, suffixes=('_tail', '_co'))
h7['drop'] = 1 - h7.meanR_co / h7.meanR_tail
b40 = h7[(h7.resid_frac >= 0.30) & (h7.resid_frac < 0.50)]
b60 = h7[(h7.resid_frac >= 0.50) & (h7.resid_frac < 0.70)]
mono = []
for (m, dg, mem), s in h7.groupby(['matrix', 'diag', 'member']):
    s = s.sort_values('resid_frac')
    if len(s) == 2:
        mono.append(s['drop'].iloc[1] >= s['drop'].iloc[0])
a0d = h7[h7.diag == 'A0'][['matrix', 'member', 'tau', 'drop']]
a1d = h7[h7.diag == 'A1'][['matrix', 'member', 'tau', 'drop']]
dd = a0d.merge(a1d, on=['matrix', 'member', 'tau'], suffixes=('_A0', '_A1'))
dd['gap_pp'] = (dd.drop_A1 - dd.drop_A0) * 100
mt = h7.groupby(['matrix', 'tau', 'diag']).agg(resid=('resid_frac', 'first'), drop_med=('drop', 'median'),
                                             drop_min=('drop', 'min'), drop_max=('drop', 'max')).reset_index()
OUT['H7'] = dict(band40_n=len(b40), band40_ge5=int((b40['drop'] >= 0.05).sum()),
                 band60_n=len(b60), band60_ge15=int((b60['drop'] >= 0.15).sum()),
                 monotone=int(sum(mono)), monotone_n=len(mono),
                 A0A1_within3pp=int((dd.gap_pp.abs() <= 3).sum()), A0A1_n=len(dd),
                 spearman_resid_vs_drop_A0=float(spearmanr(h7[h7.diag == 'A0'].resid_frac, h7[h7.diag == 'A0']['drop']).correlation),
                 by_matrix=mt.round(4).to_dict('records'))

# ---- H8
ip = kp_all = r16[(r16.source == 'keep')]
ip_own = ip[(ip.placement == 'inplace') & (ip.d_rule == 'own')][key7 + ['meanR', 'write_runs_aic', 'k_windows']]
co = ip[(ip.placement == 'tail-co') & (ip.d_rule == 'D-greedy')][key7 + ['meanR']]
h8 = ip_own.merge(co, on=key7, suffixes=('_inplace', '_co'))
h8['ratio_runs'] = h8.write_runs_aic / h8.k_windows
OUT['H8'] = dict(n=len(h8), runs_ge3=int((h8.ratio_runs >= 3).sum()), runs_ratio_median=float(h8.ratio_runs.median()),
                 runs_by_matrix=h8.groupby('matrix').ratio_runs.median().round(3).to_dict(),
                 R_inplace_ge_co=int((h8.meanR_inplace >= h8.meanR_co).sum()),
                 R_fail=h8[h8.meanR_inplace < h8.meanR_co][key7 + ['meanR_inplace', 'meanR_co']].round(3).to_dict('records'))

# ---- H9
rows = []
for dg in ('A0', 'A1'):
    p0 = pls_T('pls-0', dg)
    for m in GNN:
        for t in sorted(p0[p0.matrix == m].tau.unique()):
            x = p0[(p0.matrix == m) & (p0.tau == t) & (p0.member == 'neutron-pilot') & (p0.start_source == 'keep')]
            y = f16[(f16.matrix == m) & (f16.tau == t) & (f16.diag == dg) & (f16.member == 'neutron-pilot')]
            if len(x) and len(y):
                rows.append(dict(matrix=m, tau=t, diag=dg, T_pls0=int(x['T'].iloc[0]), T_rerun=float(y.T_rerun.iloc[0]),
                                 ratio=float(x['T'].iloc[0] / y.T_rerun.iloc[0])))
h9 = pd.DataFrame(rows)
OUT['H9'] = dict(n=len(h9), pass_=int((h9.ratio <= 0.9).sum()), table=h9.round(4).to_dict('records'))
OUT['operationalisation'] = OPERATIONALISATION

def conv(o):
    if isinstance(o, (np.integer,)): return int(o)
    if isinstance(o, (np.floating,)): return None if np.isnan(o) else float(o)
    if isinstance(o, (np.bool_,)): return bool(o)
    return str(o)
print(json.dumps(OUT, ensure_ascii=False, indent=1, default=conv))
