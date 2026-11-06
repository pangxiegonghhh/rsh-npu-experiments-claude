from load import *
from scipy.stats import spearmanr
pd.set_option('display.width',250); pd.set_option('display.max_rows',500)
d=load(); ok=d[(d.status=='OK')&(d.W==16)&(d.tau=='none')&(d.d_rule=='own')]
out=[]
for (m,dg),g in ok.groupby(['matrix','diag']):
    b=g[g.mv.isin(BASE_MEMBERS)]
    a=g
    nb=b[~b.mv.isin(['B-RCM-ref','SlashBurn'])]
    out.append(dict(matrix=m,diag=dg,n_base=len(b),rho_base=spearmanr(b.meanU,b.meanGamma)[0],
                    n_noRS=len(nb),rho_noRCM_SB=spearmanr(nb.meanU,nb.meanGamma)[0],
                    n_all=len(a),rho_all=spearmanr(a.meanU,a.meanGamma)[0]))
h=pd.DataFrame(out); print(h.round(3).to_string())
# rank table, A0
for m in ['cora','ogbn-arxiv','wiki-RfA','dawson5','olafu','pattern1','human_gene1']:
    b=ok[(ok.matrix==m)&(ok.diag=='A0')&ok.mv.isin(BASE_MEMBERS)][['mv','meanU','meanGamma','T']].copy()
    b['rU']=b.meanU.rank().astype(int); b['rG']=b.meanGamma.rank().astype(int)
    print('\n',m); print(b.sort_values('meanU').round(2).to_string(index=False))
