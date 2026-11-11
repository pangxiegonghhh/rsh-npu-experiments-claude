from load import *
pd.set_option('display.width',250); pd.set_option('display.max_rows',500)
d=load(); ok=d[(d.tau=='none')]
s=ok[ok.d_rule.isin(['indep-CBM','D-greedy','indep-first'])]
print(s[s.d_rule=='indep-CBM'].groupby(['matrix','status']).size())
p=s[s.status=='OK'].pivot_table(index=['matrix','mv','diag','W'],columns='d_rule',values='sumR',aggfunc='first').reset_index()
p['ratio']=p['indep-CBM']/p['D-greedy']; p['ratio_first']=p['indep-first']/p['D-greedy']
mem=['B0','rsh-α0','C9-Gorder','C10-BP']
q=p[p.mv.isin(mem)&p.matrix.isin(['cora','ogbn-arxiv','dawson5','wiki-RfA'])]
t=q.pivot_table(index=['matrix','mv','diag'],columns='W',values='ratio').round(3)
t['monotone_dec']=[all(np.diff([r[w] for w in [16,32,64,128] if not np.isnan(r[w])])<0) for _,r in t.iterrows()]
print(t.to_string())
print('monotone decreasing:',t.monotone_dec.sum(),'of',len(t))
print(q.pivot_table(index=['matrix','mv','diag'],columns='W',values='ratio_first').round(3).to_string())
# W16 all members
w=p[(p.W==16)]
print(w.groupby('matrix').ratio.describe().round(3))
