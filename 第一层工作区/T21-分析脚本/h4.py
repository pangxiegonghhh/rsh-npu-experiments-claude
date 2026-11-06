from load import *
pd.set_option('display.width',250); pd.set_option('display.max_rows',500)
d=load(); ok=d[(d.status=='OK')&(d.W==16)]
beta={'C9-S':0,'C9-beta0.5':0.5,'C9-Gorder':1,'C9-beta2':2,'C9-beta4':4}
c=ok[ok.mv.isin(beta)].copy(); c['beta']=c.mv.map(beta)
# T and Gamma independent of d_rule; use own rows. Gamma under tail placement depends on numbering; use full-row own and tail own
rows=[]
for (m,dg,tau,pl),g in c[c.d_rule=='own'].groupby(['matrix','diag','tau','placement']):
    g=g.set_index('beta').sort_index()
    if 0 not in g.index or 1 not in g.index: continue
    gR=c[(c.matrix==m)&(c.diag==dg)&(c.tau==tau)&(c.placement==pl)&(c.d_rule=='D-greedy')].set_index('beta').sort_index()
    rows.append(dict(matrix=m,diag=dg,tau=tau,pl=pl,
        dGamma=g.loc[1,'sumGamma']/g.loc[0,'sumGamma']-1, dT=g.loc[1,'T']/g.loc[0,'T']-1,
        dR_greedy=(gR.loc[1,'sumR']/gR.loc[0,'sumR']-1) if len(gR) else float('nan'),
        Gamma_seq=' '.join(f"{x:.0f}" for x in g.sumGamma), T_seq=' '.join(f"{x:.0f}" for x in g['T']),
        Gamma_monotone=bool((g.sumGamma.diff().dropna()<0).all()), betas=' '.join(f"{b:g}" for b in g.index)))
h=pd.DataFrame(rows)
h['pass_GT']=(h.dGamma<=-0.05)&(h.dT.abs()<=0.02)
print(h.round(4).to_string())
