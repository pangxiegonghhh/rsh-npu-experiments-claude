from load import *
pd.set_option('display.width',250); pd.set_option('display.max_rows',500)
d=load(); ok=d[(d.status=='OK')&(d.W==16)&(d.tau=='none')]
rows=[]
for (m,mv,dg),g in ok.groupby(['matrix','mv','diag']):
    g=g.set_index('d_rule')
    rule='D-exact' if 'D-exact' in g.index else 'D-greedy'
    if rule not in g.index: continue
    x=g.loc[rule]; gr=g.loc['D-greedy']
    rows.append(dict(matrix=m,mv=mv,diag=dg,rule=rule,gap=(x.sumR-x.sumGamma)/x.k_windows,gap_greedy=(gr.sumR-gr.sumGamma)/gr.k_windows,meanGamma=x.meanGamma,meanR=x.meanR))
h=pd.DataFrame(rows)
h['pass']=h.gap<=1.5
print('H1 cases',len(h),'pass',h['pass'].sum())
print(h.groupby(['matrix','diag']).agg(n=('gap','size'),gap_min=('gap','min'),gap_med=('gap','median'),gap_max=('gap','max'),npass=('pass','sum'),greedy_max=('gap_greedy','max')).round(2))
print(h[~h['pass']].sort_values('gap',ascending=False)[['matrix','mv','diag','rule','gap','meanGamma','meanR']].round(2).to_string())
# base members only
b=h[h.mv.isin(BASE_MEMBERS)]
print(b.pivot_table(index='mv',columns=['matrix'],values='gap',aggfunc='first').loc[:, :].round(2) if False else '')
print(b[b.diag=='A0'].pivot(index='mv',columns='matrix',values='gap').round(2))
print(b[b.diag=='A1'].pivot(index='mv',columns='matrix',values='gap').round(2))
