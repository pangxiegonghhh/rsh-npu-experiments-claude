from load import *
pd.set_option('display.width',250); pd.set_option('display.max_rows',500)
d=load(); ok=d[(d.status=='OK')&(d.W==16)&(d.d_rule=='own')&(d.placement.isin(['none','tail']))]
p=ok.pivot_table(index=['matrix','mv','tau'],columns='diag',values=['meanU','meanGamma','T'],aggfunc='first').dropna()
h=pd.DataFrame({'dU':p[('meanU','A1')]/p[('meanU','A0')]-1,'dG':p[('meanGamma','A1')]/p[('meanGamma','A0')]-1,'dT':p[('T','A1')]/p[('T','A0')]-1}).reset_index()
h['U_in']=(h.dU>=0.10)&(h.dU<=0.25); h['G_in']=h.dG.abs()<0.03
f=h[h.tau=='none']
print('full-row cases',len(f),'U in [10,25]%:',f.U_in.sum(),' |dGamma|<3%:',f.G_in.sum())
print(f.groupby('matrix').agg(n=('dU','size'),dU_min=('dU','min'),dU_med=('dU','median'),dU_max=('dU','max'),dG_maxabs=('dG',lambda s:s.abs().max()),dT_med=('dT','median'),nU=('U_in','sum')).round(4).to_string())
print(h[h.tau!='none'].groupby(['matrix','tau']).agg(dU_med=('dU','median'),dG_maxabs=('dG',lambda s:s.abs().max()),nU=('U_in','sum'),n=('dU','size')).round(4).to_string())
# T first place: base members and all members
def first(sub,diag):
    s=sub[sub.diag==diag].sort_values('T'); best=s['T'].min(); return sorted(s[s['T']==best].mv.tolist()), s.mv.tolist()[:3]
rows=[]
for mset,name in [(BASE_MEMBERS,'base'),(None,'all')]:
    for (m,tau),g in ok[ok.d_rule=='own'].groupby(['matrix','tau']):
        g=g if mset is None else g[g.mv.isin(mset)]
        a0,top0=first(g,'A0'); a1,top1=first(g,'A1')
        rows.append(dict(set=name,matrix=m,tau=tau,first_A0='/'.join(a0),first_A1='/'.join(a1),changed=a0!=a1,top3_A0=', '.join(top0),top3_A1=', '.join(top1)))
r=pd.DataFrame(rows); print(r.to_string())
