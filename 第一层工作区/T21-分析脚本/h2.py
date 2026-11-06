from load import *
pd.set_option('display.width',250); pd.set_option('display.max_rows',500)
d=load(); ok=d[(d.status=='OK')]
ok=ok[ok.placement.isin(['none','tail'])]
key=['matrix','mv','diag','W','tau','placement']
p=ok.pivot_table(index=key,columns='d_rule',values='sumR',aggfunc='first').reset_index()
p=p[p['own'].notna()&p['D-greedy'].notna()]
p['red']=1-p['D-greedy']/p['own']
p['cap']=(p['own']-p['D-greedy'])/(p['own']-p['D-exact'])
p['red_exact']=1-p['D-exact']/p['own']
w16=p[p.W==16]
print('W16 cases',len(w16),'red>=10%:',(w16.red>=0.10).sum(), ' exact available:',w16['D-exact'].notna().sum(),' cap>=80%:',(w16.cap>=0.8).sum())
print(w16.groupby(['matrix','tau']).agg(n=('red','size'),red_min=('red','min'),red_med=('red','median'),red_max=('red','max'),n10=('red',lambda s:(s>=0.1).sum()),
     cap_n=('cap','count'),cap_min=('cap','min'),cap_med=('cap','median'),n80=('cap',lambda s:(s>=0.8).sum())).round(3).to_string())
# failing red cases by member
f=w16[w16.red<0.10]
print(f.groupby(['matrix','mv']).size().unstack(0).fillna(0).astype(int).to_string())
print(w16[w16.cap<0.8][['matrix','mv','diag','tau','own','D-greedy','D-exact','red','cap']].round(3).to_string())
# W sensitivity
print(p[p.W>16].groupby(['matrix','W','tau']).agg(n=('red','size'),red_min=('red','min'),red_med=('red','median'),red_max=('red','max')).round(3).to_string())
